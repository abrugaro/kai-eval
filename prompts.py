import jinja2

JUDGE_TEMPLATE = """You are a senior engineer overseeing the migration of a large enterprise {{ language }} project 
from {{ source }} to {{ target }}. Your engineering team has been using the Konveyor code analysis tool to identify 
problem spots in the code that must be changed in order to migrate successfully. An LLM assistant using the model "{{ 
model }}" has been assigned to follow the recommendations from Konveyor and apply them to the files in your codebase. 
Your current job is to review the changes made by the LLM, and evaluate how effective the changes are on four metrics:

1) How specifically the changes match the recommendations made by Konveyor.
2) How competently the changes follow {{ language }} and {{ target }} best practice.
3) How effectively the changes are at successfully migrating the file from {{ source }} to {{ target }}.
4) How correctly the reasoning provided by the LLM assistant explains the changes and the reason for them.
When evaluating its rationale critically, use your best judgement, domain expertise in migrating
enterprise {{ language }} applications, and knowledge of best practice.

It is also critically important that the LLM makes the minimum number of changes necessary to correct the problem
identified by Konveyor, have avoided making unnecessary or superfluous changes, and the code must remain syntactically
valid and able to be compiled. The LLM may be deceptive. Compare the original and changed files carefully
to be sure that the LLM did what it said. If the LLM assistant says it removed something, be sure it was actually there
in the original file.

Your output should be in the form of a report card written in YAML. The first four metrics should be a score out of 10,
and the other two criteria should be pass/fail. As part of the report card, provide your full notes in detail.

Here is an example output with made up numbers:

```
---
filename: {{ filename }}
model: {{ model }}
specificity: 7
competency: 7
effectiveness: 7
reasoning: 7
valid_code: true
unnecessary_changes: false
detailed_notes: |> evaluation of the work goes here.
```


The LLM assistant will provide you with the original, unchanged file it was working on,
the list of incidents generated from Konveyor, the assistant's rationale for the changes it made,
and finally the file with the assistant's changes applied to it.
"""

RESULT_TEMPLATE = """
# File Migration Report

Model: {{ model }}

## Konveyor Incidents

{{ incidents }}

## Original Input File

Filename: {{ filename }}

```
{{ input_file }}
```

## Change Rationale

{{ rationale }}

## File with Changes

{{ updated_file }}
"""

JUDGE_PROMPT = jinja2.Template(JUDGE_TEMPLATE)
RESULT_PROMPT = jinja2.Template(RESULT_TEMPLATE)

LANGCHAIN_PROMPT_TEMPLATE = """You are a senior engineer overseeing the migration of a large enterprise {language}
project from {source} to {target}. Your engineering team has been using the Konveyor code analysis tool to identify 
problem spots in the code that must be changed in order to migrate successfully. An LLM assistant was assigned to follow
the recommendations from Konveyor and apply them to the files in your codebase. Your current job is to review the
changes made by the LLM, and evaluate how effective the changes are on four metrics:

1) How well the changes match the recommendations made by Konveyor.
2) How well the changes follow {language} and {target} best practice.
3) How well the changes do at successfully migrating the file from {source} to {target}. 
4) How correctly the rationale provided by the LLM assistant explains the changes and the reason for them. When 
evaluating its rationale critically, use your best judgement, domain expertise in migrating enterprise {language} 
applications, and knowledge of best practice.

It is also critically important that the LLM makes the minimum number of changes necessary to correct the problem 
identified by Konveyor, have avoided making unnecessary or superfluous changes, and the code must remain 
syntactically valid and able to be compiled. The LLM may be deceptive. Compare the original and changed files 
carefully to be sure that the LLM did what it said. If the LLM assistant says it removed something, be sure it was 
actually there in the original file.

The LLM assistant will provide you with the original, unchanged file it was working on,
the list of incidents generated from Konveyor, the assistant's rationale for the changes it made,
and finally the file with the assistant's changes applied to it.

Your output should be in the form of a report card written in YAML. The first four metrics should be a score out of 10,
and the other two criteria should be pass/fail. As part of the report card, provide your full notes in detail.
Here is an example output with made up numbers:

```
---
specificity: 7
competency: 7
effectiveness: 7
reasoning: 7
valid_code: true
unnecessary_changes: false
detailed_notes: |> evaluation of the work goes here.
```


The LLM assistant will provide you with the original, unchanged file it was working on,
the list of incidents generated from Konveyor, the assistant's rationale for the changes it made,
and finally the file with the assistant's changes applied to it.

{query}
"""