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

View only Jira worklogs:
```sh
python main.py --view=jira
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

This was initially meant to be a quick n' dirty automation script, I had no interest in investing much time into it so I used Copilot to generate the first version of this tool, which you can see in the first commit along with the prompt. No AI was used after that commit, and I deleted all of that code anyway in the following commits because:
1) it did [not work](db472bacacc1470f39a1b99cb3e5083878bc26fe) and was crap enough that it made me not bother trying to refine the prompt
2) while trying to fix the code I changed my mind about what I wanted the script to do - the initial idea was to sync times from Jira to Actitime, but then I found that Actitime makes it much easier for me to track hours, so I needed to sync in the opposite direction. I could not reuse most code anyway so in the end I deleted basically [everything](11a874d0fac8b7896505bdcd64dda00799fb9c38) except for the function `get_start_end_of_current_week`, which is the only AI-written code in the repository (to which I added the docstring and type hints though).
