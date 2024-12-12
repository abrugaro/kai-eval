#!/bin/env python

import os
import yaml
import re
import argparse
from collections import defaultdict

from git import Repo


def parse_llm_result(content):
    """
    Parses the content of an llm_result file and returns a YAML document containing
    the reasoning, updated file, and additional information as separate fields.

    Args:
        content (str): The string contents of the llm_result file.

    Returns:
        str: A YAML document as a string.
    """
    # Initialize a dictionary to store the sections
    data = {}

    # Split the content into sections based on headings like '## Reasoning'
    sections = re.split(r'^##\s+', content, flags=re.MULTILINE)

    for section in sections:
        # Skip empty sections
        if not section.strip():
            continue

        # Extract the title and body of each section
        lines = section.strip().split('\n', 1)
        title = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ''

        # Normalize the title to use as a key
        key = title.lower().replace(' ', '_')

        if key == 'updated_file':
            # Extract code from code block
            code_match = re.search(r'```[\w]*\n(.*?)\n```', body, re.DOTALL)
            if code_match:
                code = code_match.group(1)
                data[key] = code.strip()
            else:
                data[key] = body.strip()
        else:
            data[key] = body.strip()
    return data


def find_llm_results_with_prompt_vars(root_dir):
    """
    Search for 'llm_result' files and their corresponding 'prompt_vars.json' files,
    and output the source file they correspond to.

    Args:
        root_dir (str): The root directory to start the search from.
    """
    output_yaml = []

    for root, dirs, files in os.walk(root_dir):
        if 'llm_result' in files:
            llm_result_path = os.path.join(root, 'llm_result')

            # The 'prompt_vars.json' is located two levels up from 'llm_result'
            retry_attempt_dir = root
            incident_batch_number_dir = os.path.dirname(retry_attempt_dir)
            prompt_vars_path = os.path.join(incident_batch_number_dir, 'prompt_vars.json')

            # Check if 'prompt_vars.json' exists
            if not os.path.exists(prompt_vars_path):
                continue  # Skip if 'prompt_vars.json' is missing

            # Split the path into components
            path_components = llm_result_path.split(os.sep)

            try:
                # Find the index of 'logs' in the path to identify positions
                logs_index = path_components.index('logs')
            except ValueError:
                continue  # 'logs' not in path, skip to next

            # Extract components according to the directory structure
            try:
                model = path_components[logs_index + 1]
                app_name = path_components[logs_index + 2]

                # Initialize indices for batch_mode and timestamp
                batch_mode_index = None
                timestamp_index = None

                # Search for the timestamp index (assumed to be a float or int)
                for i in range(logs_index + 3, len(path_components)):
                    component = path_components[i]
                    try:
                        float(component)
                        timestamp_index = i
                        break  # Found the timestamp index
                    except ValueError:
                        pass  # Continue searching

                if timestamp_index is None:
                    continue  # Timestamp not found, skip to next

                batch_mode_index = timestamp_index - 1
                batch_mode = path_components[batch_mode_index]

                # Extract the source file path components
                src_file_path_components = path_components[logs_index + 3:batch_mode_index]
                src_file_path = os.path.join(*src_file_path_components)
                src_file_name = os.path.basename(src_file_path)

                # Output the information
                print(f"LLM Result File     : {llm_result_path}")
                print(f"Prompt Vars File    : {prompt_vars_path}")
                print(f"Corresponding Source: {src_file_path}")
                print('-' * 60)

                with open(prompt_vars_path) as prompt_vars_f:
                    prompt_vars_dict = yaml.safe_load(prompt_vars_f)
                with open(llm_result_path) as llm_results_f:
                    llm_results_raw = llm_results_f.read()
                    llm_results = parse_llm_result(llm_results_raw)

                unified = dict()
                unified["src_file_path"] = src_file_path
                unified["prompt_vars"] = prompt_vars_dict
                unified["llm_results"] = llm_results
                output_yaml.append(unified)
            except IndexError:
                continue  # Path structure not as expected, skip to next
    return output_yaml


def parse_analysis_output_and_changes(analysis_file_path: str, repo_path: str):
    file_incidents_map = map_analysis_output_by_file(analysis_file_path)
    repo = Repo(repo_path)

    for modified_file in repo.index.diff(None):
        print(modified_file.a_path)
        file_path = repo.working_dir + "/" + modified_file.a_path
        for uri in file_incidents_map:
            if uri.endswith(modified_file.a_path):
                diff = repo.git.diff(modified_file.a_path)
                file_incidents_map[uri]["diff"] = diff

    return file_incidents_map



def map_analysis_output_by_file(analysis_file_path: str):
    with open(analysis_file_path) as analysis_output_f:
        output_yaml = yaml.safe_load(analysis_output_f)

    file_incidents_map = defaultdict(lambda: {"incidents": []})
    for top_level_value in output_yaml:
        if not isinstance(top_level_value, dict) or "violations" not in top_level_value:
            continue
        violations = top_level_value["violations"]

        for violation_key, violation_value in violations.items():
            if not isinstance(violation_value, dict) or "incidents" not in violation_value:
                continue

            for incident in violation_value["incidents"]:
                uri = incident.get("uri")
                # Ignore non-project files, TODO (abrugaro) check if this works in Windows
                if not uri or uri.startswith("file:///root/.m2"):
                    continue

                if uri not in file_incidents_map:
                    file_incidents_map[uri] = {"incidents": []}
                file_incidents_map[uri]["incidents"].append(incident)

    file_incidents_map = dict(file_incidents_map)

    return file_incidents_map


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("analysis_output_file", help="path to analysis output yaml file")
    parser.add_argument("repository_path", help="path to repository with updated changes")
    parser.add_argument("output_file", help="path to write unified result yaml")
    args = parser.parse_args()
    output = parse_analysis_output_and_changes(args.analysis_output_file, args.repository_path)
    with open(args.output_file, "w") as outfile:
        yaml.dump(output, outfile)
