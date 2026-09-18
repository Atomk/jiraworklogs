# jiraworklogs

A CLI tool script to view time spent each day on Jira tasks.

```
$ jiraworklogs
29 Jun 2026
- 1h 35m   JJ-1814   Meetings
- 1h       JJ-496    Task scheduler: active tasks still available after delete
- 2h 30m   JJ-1150   Debian migration
TOTAL: 5h 5m

30 Jun 2026
- 8h       JJ-783    Task scheduler: simplify backend->frontend model conversion
TOTAL: 8h

01 Jul 2026
- 5h       JJ-783    Task scheduler: simplify backend->frontend model conversion
- 2h 30m   JJ-1150   Debian migration
TOTAL: 7h 30m
```


## Why

I need to track worked time in Jira, but sometimes I forget to record something and there's no easy way to find where there's missing hours, or in other words to ensure that I correctly recorded everything for the day. And it's also a pain in the ass to see _actual_ worked time during a sprint when a task covers multiple sprints, since as of this writing only its total worked time can be shown via Jira's filters.

This tool provides a day-by-day overview of worked time, so that I can easily see if I forgot to add hours somewhere.


## Install
You first need to install [pipx](https://pipx.pypa.io/stable/how-to/install-pipx.html), then:

```sh
# Install the `jiraworklogs` command globally in an isolated environment
pipx install git+https://github.com/Atomk/jiraworklogs.git

# If you change your mind
pipx uninstall jiraworklogs
```


## Usage
```sh
# View times of tasks in current sprint, only current week
jiraworklogs

# View times of tasks in current sprint, starting from a given day
# This is useful when sprints last a few weeks
jiraworklogs --start 2026-09-06

# Show all available options
jiraworklogs --help
```


## Setup for development
Requires Python >= `3.9`.
```sh
# Download repository
git clone https://github.com/Atomk/jiraworklogs.git
cd jiraworklogs

# Install the "jiraworklogs" tool from the current directory
pipx install .
# Use this to update the tool after you make a change
pipx reinstall jiraworklogs
```

If you want to run tests, you also need to setup a virtual environment and dependencies:
```sh
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.lock
pip install --group test
pytest
```


## Configure
1. Run `jiraworklogs` and let it open the config file
2. Replace the auth values with you own


### How to get a Jira API token
Go to https://id.atlassian.com/manage-profile/security to create an API token. Use "Create API token", not the scoped one - while that is more secure, it does not work with two-factor authentication and it's more annoying to setup since you have to create an app in Atlassian's Developer Console.

You can name the token whatever you want, I use "jiraworklogs_cli".

You can set the token's expiration date to at most one year from now.


## Reference
- https://developer.atlassian.com/cloud/confluence/security-overview/
- [Manage API tokens](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)
- [Basic auth for REST APIs](https://developer.atlassian.com/cloud/confluence/basic-auth-for-rest-apis/)
- [REST API docs](https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/) (see menu on the left for endpoint groups)
