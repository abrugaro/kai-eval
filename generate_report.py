#!/bin/env python
#
# generate_report.py
# Consume an evaluation yaml produced by evaluate.py
# and output a CSV or JSON file containing all the scores.
#
#
import csv
import argparse
import json
import yaml


def generate_csv_report(evaluations, output):
    with open(output, 'w') as output_file:
        writer = csv.writer(output_file)
        writer.writerow([
            "File",
            "Effectiveness",
            "Specificity",
            "Reasoning",
            "Competency",
            "Valid Code",
            "Unnecessary Changes",
            "Average Score"])
        for evaluation in evaluations:
            row = [
                evaluation["filename"],
                evaluation["effectiveness"],
                evaluation["specificity"],
                evaluation["reasoning"],
                evaluation["competency"],
                evaluation["valid_code"],
                evaluation["unnecessary_changes"]
            ]
            avg = sum(row[1:5]) / 4.0
            row.append(avg)
            writer.writerow(row)

    print(f"CSV file generated at {output}")


def generate_json_report(evaluations, output):
    data = []
    total_effectiveness = 0
    total_specificity = 0
    total_reasoning = 0
    total_competency = 0
    total_average_score = 0

    for evaluation in evaluations:
        row = {
            "file": evaluation["filename"],
            "effectiveness": evaluation["effectiveness"],
            "specificity": evaluation["specificity"],
            "reasoning": evaluation["reasoning"],
            "competency": evaluation["competency"],
            "validCode": evaluation["valid_code"],
            "unnecessaryChanges": evaluation["unnecessary_changes"],
        }
        row["averageScore"] = round(sum([
            row["effectiveness"],
            row["specificity"],
            row["reasoning"],
            row["competency"]
        ]) / 4.0, 1)

        total_effectiveness += row["effectiveness"]
        total_specificity += row["specificity"]
        total_reasoning += row["reasoning"]
        total_competency += row["competency"]
        total_average_score += row["averageScore"]

        data.append(row)

    total_incidents = len(data)
    averages = {
        "averageEffectiveness": round(total_effectiveness / total_incidents, 1),
        "averageSpecificity": round(total_specificity / total_incidents, 1),
        "averageReasoning": round(total_reasoning / total_incidents, 1),
        "averageCompetency": round(total_competency / total_incidents, 1),
        "averageScore": round(total_average_score / total_incidents, 1),
    }

    result = {
        **averages,
        "data": data
    }

    with open(output, 'w') as output_file:
        json.dump(result, output_file, indent=4)

    print(f"JSON file generated at {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", help="path to evaluation yaml")
    parser.add_argument("output_file", help="path to write output file")
    parser.add_argument("output_format", help="output format [csv | json]")
    args = parser.parse_args()
    with open(args.input_file) as input_file:
        evaluations = yaml.safe_load(input_file)

    if args.output_format.lower() == "csv":
        generate_csv_report(evaluations, args.output_file)
        exit(0)

    if args.output_format.lower() == "json":
        generate_json_report(evaluations, args.output_file)
        exit(0)

    print(f"ERROR output format '{args.output_format}' not recognized")
