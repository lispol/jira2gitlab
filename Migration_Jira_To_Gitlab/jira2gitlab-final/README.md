# Overview
Jira to Gitlab project.

## Table of contents
1. [Requirements](#Requirements)
2. [Migration](#Migration)
    1. [Fill variables](##Fill variables)
    1. [Run the script](##Run the script)
3. [Additional](#Additional)

# Requirements
1. Your system must have python>=3.6
1. It's recommended to use pip package manager.  
[How to install it](https://pip.pypa.io/en/stable/installing/#installing-with-get-pip-py)
1. It's recommended to use virtual environment.   
[How to use it](https://docs.python.org/3/tutorial/venv.html)
1. Migration script requires some python libraries.  
You can find them in the [requirements.txt](requirements.txt)  
To satisfy these requirements you need to install listed packages by yourself or with 
[requirements.txt](requirements.txt) file.  
For example, `pip3 install -U -r <path_to_requirements.txt>`
1. Users must have same email addresses in Jira and Gitlab.  
Also they must have admin or project owner rights at the time of migration.
1. You must have accounts in Jira and Gitlab that:  
    - Have administrator role in Gitlab
    - Have project administrator in Jira 

# Migration
## Fill variables
- jira_auth_username  
Username to communicate with Jira
- jira_auth_password  
Password of the username to communicate with Jira
- jira_server_url  
URL of Jira. For example, https://jira.somedomain.com
- jira_project  
The key of project must be migrated
- gitlab_url  
URL of Gitlab. For example, https://gitlab.somedomain.com
- gitlab_private_token  
Private token of the user to communicate with Gitlab.  
**Scope**: api, sudo  
[Personal access tokens](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html)
- gitlab_project_id  
Id of the project in which issues must be migrated  
Project overview => Details. Field "Project ID"
## Run the script
```
python3 jira2gitlab.py
```
And wait until it will finish his work

# Additional
## Scripts
[gitlab_delete_project_issues.py](additional/gitlab_delete_project_issues.py)  
With this script you can delete all tasks in Gitlab project.  
