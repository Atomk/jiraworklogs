# Actitime-Jira time sync

A CLI script to synchronize reported time for tasks from Actitime to Jira, so you don't have to report time manually on both.

This assumes that the name of your Actitime tasks starts with the related Jira tasks's key (e.g. "IT-456").


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

`actitime_ignore_tasks` is a list of names of Actitime tasks that should be ignored and not synced to Jira. This is useful to enable tracking time for chores that are not supposed to also be tracked in Jira. Leave the list empty if you don't need this.

### Actitime
After logging in the Actitime website, the URL should look like `https://<YOUR_ACTITIME_URL>/timetrack/enter.do`. The part of the URL before `/timetrack` should be pasted into the `actitime_domain` config field.

You'll have to create the basic auth string yourself with your username and password.

### Jira
Go to https://id.atlassian.com/manage-profile/security to create an API token. Use "Create API token", not the scoped one - while that is more secure, it does not work with two-factor authentication and it's more annoying to setup since you have to create an app in Atlassian's Developer Console.

You can name the token whatever you want, I use "actitime_jira_sync".

You can set the token's expiration date to at most one year from now.


## Run
```sh
python main.py
```


## Test
```sh
pytest
```


## Resources
Actitime API docs:
- https://www.actitime.com/api-documentation
- Swagger UI
    - after logging into you account, in the top-right corner there should be a puzzle piece icon, which is the Add-on menu. Click on it, then click on "Access actiTIME API". It should open a page at `https://<YOUR_ACTITIME_URL>/api/v1/swagger`.

Jira docs:
- https://developer.atlassian.com/cloud/confluence/security-overview/
- [Manage API tokens](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)
- [Basic auth for REST APIs](https://developer.atlassian.com/cloud/confluence/basic-auth-for-rest-apis/)
- [REST API docs](https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/) (see menu on the left for endpoint groups)


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
