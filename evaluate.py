#!/bin/env python
import os
import re
import sys
import yaml
import pydantic
import argparse
import traceback
from typing import List
from dataclasses import dataclass, field
from langchain.output_parsers import YamlOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser, BaseTransformOutputParser

sys.path.append("../kai")
from kai.kai_config import KaiConfig
from kai.llm_interfacing.model_provider import ModelProvider
from prompts import JUDGE_PROMPT, RESULT_PROMPT, LANGCHAIN_PROMPT_TEMPLATE


@dataclass
class LLMResult:
    rationale: str = ""
    updated_file: str = ""


@dataclass
class PromptVars:
    model: str = ""
    language: str = ""
    source: str = ""
    target: str = ""
    filename: str = ""
    unchanged_file: str = ""
    incidents: list = field(default_factory=list)


class EvaluationResult(pydantic.BaseModel):
    filename: str
    effectiveness: int = pydantic.Field(
        description="A grade from 0 to 10 of how effectively the changes migrate the file from the source technology "
                    "to the target technology."
    )
    specificity: int = pydantic.Field(
        description="A grade from 0 to 10 of how targeted the changes are at specifically addressing the incidents "
                    "identified by Konveyor."
    )
    reasoning: int = pydantic.Field(
        description="A grade from 0 to 10 of how well the model under evaluation was able to explain why and how it "
                    "made the changes."
    )
    competency: int = pydantic.Field(
        description="A grade from 0 to 10 of how competently the changes reflect industry best practice for the "
                    "language and target technology."
    )
    valid_code: bool = pydantic.Field(
        description="A pass/fail grade of whether or not the changed file is valid, syntactically correct code that "
                    "can be successfully compiled or interpreted."
    )
    unnecessary_changes: bool = pydantic.Field(
        description="A pass/fail grade of whether or not the model under evaluation made unnecessary changes to the "
                    "file that do not advance the goal of successfully migrating it."
    )
    detailed_notes: str = pydantic.Field(
        description="Freeform explanation of the grades given to the model under evaluation."
    )

    def score_summary(self) -> float:
        score = self.effectiveness
        score += self.specificity
        score += self.reasoning
        score += self.competency
        score /= 4.0
        return score

    def __str__(self):
        return yaml.dump(self.__dict__)


class EvaluationOutputParser(BaseTransformOutputParser[str]):

    @classmethod
    def is_lc_serializable(cls) -> bool:
        return True

    @classmethod
    def get_lc_namespace(cls) -> List[str]:
        return ["langchain", "schema", "output_parser"]

    @property
    def _type(self) -> str:
        return "default"

    def parse(self, text: str) -> EvaluationResult:
        """
        Returns an EvaluationResult derived from the llm text output.

        """

        extracted = extract_yaml_from_text(text)
        result = EvaluationResult()
        result.effectiveness = extracted["effectiveness"]
        result.specificity = extracted["specificity"]
        result.reasoning = extracted["reasoning"]
        result.competency = extracted["competency"]
        result.valid_code = extracted["valid_code"]
        result.unnecessary_changes = extracted["unnecessary_changes"]
        result.detailed_notes = extracted["detailed_notes"]

        return result


class Evaluator:

    def __init__(self, config: KaiConfig):
        self.config = config
        self.model_provider = ModelProvider(config.models)

    def evaluate(self, prompt_vars: PromptVars, llm_result: LLMResult) -> EvaluationResult:
        """
        Evaluates the work done by Kai and returns an EvaluationResult report card.

        """

        chain = self.model_provider.llm | StrOutputParser()
        response = chain.invoke(render_messages(prompt_vars, llm_result))
        extracted = extract_yaml_from_text(response)
        return EvaluationResult(
            filename=prompt_vars.filename,
            effectiveness=extracted["effectiveness"],
            specificity=extracted["specificity"],
            reasoning=extracted["reasoning"],
            competency=extracted["competency"],
            valid_code=extracted["valid_code"],
            unnecessary_changes=extracted["unnecessary_changes"],
            detailed_notes=extracted["detailed_notes"]
        )

    # for some reason this doesn't work as well as `evaluate`. the `detailed_notes` field gets cut off.
    # leaving this in so that the reason it fails to return the complete output can be explored later.
    def evaluate_with_langchain_yaml_parser(self, prompt_vars: PromptVars, llm_result: LLMResult) -> EvaluationResult:
        query = RESULT_PROMPT.render(
            model=prompt_vars.model,
            filename=prompt_vars.filename,
            incidents=prompt_vars.incidents,
            input_file=prompt_vars.unchanged_file,
            rationale=llm_result.rationale,
            updated_file=llm_result.updated_file
        )
        parser = YamlOutputParser(pydantic_object=EvaluationResult)
        prompt = PromptTemplate(
            template=LANGCHAIN_PROMPT_TEMPLATE,
            input_variables=["query", "source", "target", "language"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        chain = prompt | self.model_provider.llm | parser
        result = chain.invoke(
            {"query": query,
             "source": prompt_vars.source,
             "target": prompt_vars.target,
             "language": prompt_vars.language
             })
        return result


def extract_yaml_from_text(text: str) -> dict:
    """
    Extracts a YAML chunk wrapped in triple backticks from a larger text
    and parses it into a Python dictionary.

    Args:
        text (str): The larger unformatted text containing the YAML block.

    Returns:
        dict: The parsed YAML content as a dictionary, or None if not found.
    """
    # Regular expression to find triple backtick-enclosed YAML blocks
    pattern = r'```(yaml)?\n(.*?)\n```'

    # Search for the YAML block
    match = re.search(pattern, text, re.DOTALL)

    if match:
        yaml_content = match.group(2)
        try:
            print(yaml_content)
            # Parse the YAML content
            data = yaml.safe_load(yaml_content)
            return data
        except yaml.YAMLError as e:
            print("Error parsing YAML:", e)
            raise e
    else:
        print("No YAML block found.")
        print(text)
        raise ValueError("No YAML block found.")


def render_messages(prompt_vars: PromptVars, llm_results: LLMResult) -> list:
    """
    Takes the Kai input and output to be evaluated and converts it into
    a prompt for the evaluator.

    """

    judge = JUDGE_PROMPT.render(
        model=prompt_vars.model,
        source=prompt_vars.source,
        target=prompt_vars.target,
        language=prompt_vars.language,
    )
    result = RESULT_PROMPT.render(
        model=prompt_vars.model,
        filename=prompt_vars.filename,
        incidents=prompt_vars.incidents,
        input_file=prompt_vars.unchanged_file,
        rationale=llm_results.rationale,
        updated_file=llm_results.updated_file
    )
    messages = [
        SystemMessage(content=judge),
        HumanMessage(content=result)
    ]
    return messages


def get_config(config_path: str) -> KaiConfig:
    if not os.path.exists(config_path):
        raise FileNotFoundError("Config file not found.")
    return KaiConfig.model_validate_filepath(config_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--language", dest="language", default="Java")
    parser.add_argument("-s", "--source", dest="source_technology", default="JavaEE")
    parser.add_argument("-t", "--target", dest="target_technology", default="Quarkus")
    parser.add_argument("-c", "--config", default="config.toml")
    parser.add_argument("input_file", help="path to unified request/result file produced by parse_kai_logs.py")
    parser.add_argument("output_file")
    args = parser.parse_args()
    config = get_config(args.config)
    evaluator = Evaluator(config)

    results = []
    k = None
    with open(args.input_file) as f:
        ks = yaml.safe_load(f)
    for k in ks:
        prompt_vars = PromptVars()
        prompt_vars.source = args.source_technology
        prompt_vars.target = args.target_technology
        prompt_vars.language = k["prompt_vars"]["src_file_language"]
        prompt_vars.incidents = k["prompt_vars"]["incidents"]
        prompt_vars.unchanged_file = k["prompt_vars"]["src_file_contents"]
        prompt_vars.filename = k["prompt_vars"]["src_file_name"]
        llm_result = LLMResult()
        llm_result.rationale = k["llm_results"].get("reasoning", "")
        llm_result.updated_file = k["llm_results"].get("updated_file", "")
        if llm_result.rationale == "" or llm_result.updated_file == "":
            print("no fix for file: ", prompt_vars.filename)
            continue
        try:
            result = evaluator.evaluate(prompt_vars, llm_result)
            results.append(result.__dict__)
        except BaseException:
            print("Couldn't evaluate response for file: ", prompt_vars.filename)
            print(traceback.format_exc())
    with open(args.output_file, "w") as f:
        yaml.dump(results, f)
