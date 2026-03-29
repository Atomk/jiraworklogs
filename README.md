## Setup
Requires Python >= `3.9`.
```sh
python3.9 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```


## Configure
1. Rename `config.sample.json` to `config.json`
2. Replace the auth values with you own


## Run
```sh
python main.py
```


## Test
```sh
pytest
```


## LLM Disclaimer

Initial version generated with Copilot, see first commit.

Prompt:
> You are a Python developer, and your company requires you to report worked hours both on Jira and on Actitime, but to save time you want to only report times on one service and use a script to take that data and report it on the other service.
>
> Produce a well-documented Python script that is responsible for gathering worked hours for the current week from Jira: you want to know, for each day, how many hours you worked on a specific work item and what category that ticket belongs to.
>
> Then, get existing Actitime open tasks, and determine which Jira tasks (with reported time for this week) have no corresponding task on Actitime.
>
> Then, via the Actitime API, take the gathered times and report them also on Actitime, assuming a task exists with the same code as the Jira ticket (i.e. Jira ticket "ET-432" should report time on Actitime for task "ET-432").
