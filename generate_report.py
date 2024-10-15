#!/bin/env python
#
# generate_report.py
# Consume an evaluation yaml produced by evaluate.py
# and output a CSV file containing all the scores.
#
#
import csv
import argparse
import yaml

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", help="path to evaluation yaml")
    parser.add_argument("output_file", help="path to write output csv")
    args = parser.parse_args()

    with open(args.input_file) as input_file:
        evaluations = yaml.safe_load(input_file)
    with open(args.output_file, 'w') as output_file:
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