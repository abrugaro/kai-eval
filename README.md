# Kai Evaluator

---------------

## Overview

This repository contains scripts that can be used to grade Kai's
attempts to fix problems identified by the Konveyor analyzer by running
them through the same LLM with a specialized prompt to put it into
an evaluator persona.

The core of this is the `Evaluator` class in `evaluate.py`. The `Evaluator`
is constructed with a `KaiConfig` and it has an `evaluate` method which
accepts a `PromptVars` object and an `LLMResult` object representing the initial
fix request to Kai and its corresponding response. `evaluate` uses the prompts
defined in `prompts.py` to construct its request and returns an `EvaluationResult`
object with scores for six categories of evaluation:

1. `effectiveness`: A grade from 0 to 10 of how effectively the changes migrate the file from the source technology "
   to the target technology.
2. `specificity`: A grade from 0 to 10 of how targeted the changes are at specifically addressing the incidents "
   identified by Konveyor.
3. `reasoning`: A grade from 0 to 10 of how well the model under evaluation was able to explain why and how it "
   made the changes.
4. `competency`: A grade from 0 to 10 of how competently the changes reflect industry best practice for the "
   language and target technology.
5. `valid_code`: A boolean indicating whether the changed file is valid, syntactically correct code that "
   can be successfully compiled or interpreted.
6. `unnecessary_changes`: A boolean indicating whether the model under evaluation made unnecessary changes to the "
   file that do not advance the goal of successfully migrating it.

The `Evaluator` and supporting objects can be imported and used as a component, or used as part of this
collection of scripts to evaluate the Kai server logs.

## evaluate.py

When run as a script rather than imported as a module, `evaluate.py` will evaluate the contents of the Kai logs and
generate a score document. `evaluate.py` takes the following keyword arguments:

* `--config` Path to the KaiConfig.
* `--source` The source technology being migrated. Defaults to `JavaEE`. Ideally this and `--target` would be derived from the original prompt but for now it needs to be provided.
* `--target` The target technology being migrated to. Defaults to `Quarkus`. 
* `<input yaml>` Path to the parsed log yaml produced by `parse_kai_logs.py`
* `<output yaml>` Path to write the evaluation yaml.

The output yaml is a list of `EvaluationResult` objects, including the judge's detailed reasoning about its decisions.

```yaml
- competency: 10
  detailed_notes: 'The LLM assistant has done an excellent job in addressing the Konveyor
    incidents and migrating the file from JavaEE to Quarkus. Here''s a detailed evaluation:


    1. Specificity (10/10): The changes made perfectly match the recommendations from
    Konveyor. All six import statements were correctly updated from ''javax'' to ''jakarta''
    as specified in the incidents.


    2. Competency (10/10): The changes follow Java and Quarkus best practices. The
    assistant correctly identified that Quarkus is built on Jakarta EE 8 but recommends
    using ''jakarta'' namespace for future compatibility. This shows a good understanding
    of the Java ecosystem and migration paths.


    3. Effectiveness (10/10): The changes are highly effective in migrating the file
    from JavaEE to Quarkus. By updating the import statements, the code is now compatible
    with Jakarta EE, which Quarkus uses. No other changes were necessary for this
    particular file.


    4. Reasoning (9/10): The reasoning provided is mostly correct and thorough. The
    assistant explained the split between Java EE and Jakarta EE, the reason for changing
    ''javax'' to ''jakarta'', and listed all the changes made. The only minor inaccuracy
    is stating that Quarkus is built on Jakarta EE 8 (which uses ''javax''), when
    in fact, Quarkus supports both ''javax'' and ''jakarta'' namespaces depending
    on the version and configuration.


    5. Valid Code (Pass): The changes made do not affect the syntax or structure of
    the code. The file remains valid Java code that should compile without issues.


    6. Unnecessary Changes (Pass): The LLM assistant made only the necessary changes
    as identified by Konveyor. No superfluous modifications were made to the code.


    Overall, the LLM assistant has done an excellent job in migrating this file. The
    changes are precise, effective, and well-reasoned, with only a very minor inaccuracy
    in the explanation that doesn''t affect the quality of the migration itself.'
  effectiveness: 10
  reasoning: 9
  specificity: 10
  unnecessary_changes: false
  valid_code: false
```

## Evaluating Kai Logs

`evaluate.py` can be run in sequence with the rest of the scripts in this repository to collect the contents of
a Kai server's `logs/trace` directory and evaluate each of the request/result pairs, ultimately resulting in a CSV
file containing the raw scores and an average per file.

1. Analyze the target application to generate an `output.yaml`.
2. Start Kai server, ensuring that tracing is turned on.
3. Use `run_kai.py` to generate fixes, thereby populating the `logs/trace` directory with request/result pairs.
```bash
$ ./run_kai.py --name appname --analysis path/to/output.yaml  --src path/to/source/repository
```
4. Run `parse_kai_logs.py`, passing it the path to the Kai server's `logs/trace`
   directory and a location to write out a yaml document containing the parsed logs.
```bash
$ ./parse_kai_logs.py path/to/logs/trace logs.yaml
```
5. Run the evaluator to produce the detailed evaluation output described above.
```bash
$ ./evaluate.py --config kai/config.toml --source JavaEE --target Quarkus logs.yaml evaluation.yaml
```
6. If desired, run `generate_report.py` to generate a CSV file containing a score summary.
```bash
$ ./generate_report.py evaluation.yaml summary.csv
```

# Notes

* The `meta.llama3-70b-instruct-v1:0` model seems to have a hard time constructing the `detailed_notes` field on the 
  report card correctly. In some cases it outputs syntactically invalid yaml for that field which prevents the evaluation
  from being parsed. Claude 3.5 Sonnet doesn't appear to have this problem. Further experimentation with the prompt should
  be done to attempt to get a consistent result.
