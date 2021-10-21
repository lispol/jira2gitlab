import gitlab
import pandas as pd
import urllib3
from jira import JIRA
import os
import re

from functions import time_converting
from functions import data_check
from functions import status_check
from functions import subtask_check

if not os.path.exists('Check'):
    os.mkdir('Check')

# Disable "InsecureRequestWarning" messages
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Jira section
jira_auth_username = ''
jira_auth_password = ''
jira_server_url = ''
jira_options = {
    "verify": False
}
jira = JIRA(server=jira_server_url, basic_auth=(jira_auth_username, jira_auth_password), options=jira_options)

# Giltab section
gitlab_url = ''
gitlab_private_token = ''
gitlab_ssl_verify = False # Set to False if you want to ignore ssl warnings
gl = gitlab.Gitlab(gitlab_url, private_token=gitlab_private_token, ssl_verify=gitlab_ssl_verify)

projects_mapping = {
    
}

# Auth into Gitlab as current user (gitlab_private_token)
gl.auth()

# Data collecting
projects = []
for jira_project in projects_mapping:
    gitlab_project_id = projects_mapping[jira_project]
    print(f'Collecting data from {jira_project} Jira project and corresponding {gitlab_project_id} Gitlab project')
    jira_issues = jira.search_issues('project=%s ORDER BY key asc' % jira_project, maxResults=0)
    gitlab_project = gl.projects.get(gitlab_project_id)
    gitlab_issues = gitlab_project.issues.list(order_by='created_at', sort='desc', all=True)
        
    ## jira 
    jira_dict = {}
    jira_comments = []
    jira_worklogs = []
    jira_worklogs_comments = []
    jira_logged_time = []
    jira_attachments = []
    jira_subtasks = []
    jira_labels = []
    
    for issue in jira_issues:
        jira_issue_key = issue.key
        print(f'Collecting data from {jira_issue_key} Jira issue')
        jira_issue = jira.issue(jira_issue_key)
        jira_comment = jira.comments(jira_issue_key)
        # issue comments
        for comment in jira_comment:
            jira_comments.append(comment.id)
        # worklogs & logged time
        for comment in jira_issue.fields.worklog.worklogs:
            jira_worklogs.append(comment.id)
            try:
                jira_worklogs_comments.append(comment.comment)
            except AttributeError:
                pass
            jira_logged_time.append(comment.timeSpent)
        
        # logged time in sec
        jira_logged_time_sec = sum([time_converting(time) for time in jira_logged_time])
        # asignee
        if jira_issue.fields.assignee:
            jira_assignee = jira_issue.fields.assignee.displayName
        else:
            jira_assignee = 'Unassigned'
        # status
        jira_status = jira_issue.fields.status.statusCategory.key.lower()
        # attachments
        for attachment in jira_issue.fields.attachment:
            jira_attachments.append(attachment.id)
        jira_issue_type = jira_issue.fields.issuetype.name.lower()
        # subtasks
        if jira_issue.fields.issuetype.subtask:
            jira_parent = jira_issue.fields.parent.id
        else:
            jira_parent = -1
        if jira_issue.fields.subtasks:
            for subtask in jira_issue.fields.subtasks:
                jira_subtasks.append(subtask.id)
        else:
            jira_subtasks.append(-1)
        for label in jira_issue.fields.labels:
            jira_labels.append(label)
        # time estimate
        jira_time_estimate = jira_issue.fields.timeoriginalestimate
        
        
        # gathering info into dictionary
        jira_dict[issue.id] = {
            'jira_issue_key': jira_issue_key,
            'comments': jira_comments, 
            'worklogs': jira_worklogs, 
            'worklogs_comments': jira_worklogs_comments,
            'logged_time': jira_logged_time,
            'logged_time_sec': jira_logged_time_sec,
            'assignee': jira_assignee,
            'status': jira_status,
            'attachments': jira_attachments,
            'issue_type': jira_issue_type,
            'parent': jira_parent,
            'subtasks': jira_subtasks,
            'labels': jira_labels,
            'time_estimate': jira_time_estimate,
        }
        
        jira_comments = []
        jira_worklogs = []
        jira_worklogs_comments = []
        jira_logged_time = []
        logged_time_sec = []
        jira_attachments = []
        jira_subtasks = []
        jira_labels = []
        
    ## gitlab
    gitlab_dict = {}
    gitlab_comments = []
    gitlab_worklogs = []
    gitlab_worklogs_comments = []
    gitlab_logged_time = []
    gitlab_labels = []
    gitlab_links = []
    
    for issue in gitlab_issues:
        print(f'Collecting data from {issue.iid} GitLab issue')
        # issue comments
        for comment in issue.notes.list():
            if (('assigned to' not in comment.body) & 
                ('unassigned' not in comment.body) &
                ('Worklog message:' not in comment.body) & 
                ('changed time estimate to' not in comment.body) & 
                ('of time spent' not in comment.body) &
                ('closed' not in comment.body) &
                ('changed due date to' not in comment.body) &
                ('marked this issue as related to' not in comment.body) &
                ('removed the relation with' not in comment.body)):
                gitlab_comments.append(comment.id)
            # worklogs
            if ('of time spent' in comment.body):
                gitlab_worklogs.append(comment.id)
            # worklog comments
            if ('Worklog message:' in comment.body):
                gitlab_worklogs_comments.append(comment.id)
        # logged time
        gitlab_logged_time = issue.time_stats()['human_total_time_spent']
        gitlab_logged_time_sec = issue.time_stats()['total_time_spent']
        # assignee
        if issue.assignee:
            gitlab_assignee = issue.assignee['username']
        else:
            gitlab_assignee = 'Unassigned'
        # status
        gitlab_status = issue.state
        # links
        for link in issue.links.list():
            if link:
                gitlab_links.append(link.iid)
            else:
                gitlab_links.append(-1)
        # labels
        gitlab_labels = issue.labels
        # attachments
        gitlab_description = issue.description
        gitlab_attachments = len(re.findall('/uploads/', gitlab_description))
        # time estimate
        gitlab_time_estimate = issue.time_stats()['time_estimate']
        
        # gathering info into dictionary
        gitlab_dict[issue.iid] = {
            'comments': gitlab_comments, 
            'worklogs': gitlab_worklogs, 
            'worklogs_comments': gitlab_worklogs_comments,
            'logged_time': gitlab_logged_time,
            'logged_time_sec': gitlab_logged_time_sec,
            'assignee': gitlab_assignee,
            'status': gitlab_status,
            'links': gitlab_links,
            'labels': gitlab_labels,
            'description': gitlab_description,
            'attachments': gitlab_attachments,
            'time_estimate': gitlab_time_estimate,
        }
        
        gitlab_comments = []
        gitlab_worklogs = []
        gitlab_worklogs_comments = []
        gitlab_logged_time = []
        gitlab_links = []
        gitlab_labels = []
        
    # gathering information into tables
    print(f'Gathering projects ({jira_project} - Jira project, {gitlab_project_id} - GitLab project) information into tables')
    ## jira
    jira_df = pd.DataFrame(
            {
                'jira_project': jira_project,
                'jira_issue_key': [jira_dict[jira_issue]['jira_issue_key'] for jira_issue in jira_dict],
                'jira_issue': [int(jira_issue) for jira_issue in jira_dict],
                'jira_comments': [len(jira_dict[jira_issue]['comments']) for jira_issue in jira_dict],
                'jira_worklogs': [len(jira_dict[jira_issue]['worklogs']) for jira_issue in jira_dict],
                'jira_worklogs_comments': [len(jira_dict[jira_issue]['worklogs_comments']) for jira_issue in jira_dict],
                'jira_logged_time_sec': [jira_dict[jira_issue]['logged_time_sec'] for jira_issue in jira_dict],
                'jira_assignee': [jira_dict[jira_issue]['assignee'] for jira_issue in jira_dict],
                'jira_status': [jira_dict[jira_issue]['status'] for jira_issue in jira_dict],
                'jira_attachments': [len(jira_dict[jira_issue]['attachments']) for jira_issue in jira_dict],
                'jira_issue_type': [jira_dict[jira_issue]['issue_type'] for jira_issue in jira_dict],
                'jira_parent': [jira_dict[jira_issue]['parent'] for jira_issue in jira_dict],
                'jira_subtasks': [jira_dict[jira_issue]['subtasks'] for jira_issue in jira_dict],
                'jira_labels': [jira_dict[jira_issue]['labels'] for jira_issue in jira_dict],
                'jira_time_estimate': [jira_dict[jira_issue]['time_estimate'] for jira_issue in jira_dict],
            })
        
    ## gitlab
    gitlab_df = pd.DataFrame(
            {
                'gitlab_project': gitlab_project_id,
                'gitlab_issue': [gitlab_issue for gitlab_issue in gitlab_dict],
                'gitlab_comments': [len(gitlab_dict[gitlab_issue]['comments']) for gitlab_issue in gitlab_dict],
                'gitlab_worklogs': [len(gitlab_dict[gitlab_issue]['worklogs']) for gitlab_issue in gitlab_dict],
                'gitlab_worklogs_comments': [len(gitlab_dict[gitlab_issue]['worklogs_comments']) for gitlab_issue in gitlab_dict],
                'gitlab_logged_time_sec': [gitlab_dict[gitlab_issue]['logged_time_sec'] for gitlab_issue in gitlab_dict],
                'gitlab_assignee': [gitlab_dict[gitlab_issue]['assignee'] for gitlab_issue in gitlab_dict],
                'gitlab_status': [gitlab_dict[gitlab_issue]['status'] for gitlab_issue in gitlab_dict],
                'gitlab_links': [gitlab_dict[gitlab_issue]['links'] for gitlab_issue in gitlab_dict],
                'gitlab_labels': [gitlab_dict[gitlab_issue]['labels'] for gitlab_issue in gitlab_dict],
                'gitlab_attachments': [gitlab_dict[gitlab_issue]['attachments'] for gitlab_issue in gitlab_dict],
                'gitlab_time_estimate': [gitlab_dict[gitlab_issue]['time_estimate'] for gitlab_issue in gitlab_dict],
            })
    projects.append(jira_df.merge(gitlab_df, left_on='jira_issue', right_on='gitlab_issue', how='outer'))

print(f'Union all projects data ({", ".join(list(projects_mapping.keys()))})')
df_issues = pd.concat(projects)
df_issues.fillna(0, inplace=True)

#### Checks
# Issues check
print(f'Validation all projects data ({", ".join(list(projects_mapping.keys()))}), issues level')
columns_to_check = ['comments', 'worklogs', 'worklogs_comments', 'logged_time_sec', 'assignee', 'attachments', 'time_estimate']
for column in columns_to_check:
    df_issues = data_check(df_issues, column)
    
df_issues['status'] = df_issues.apply(status_check, axis=1)
df_issues['subtask'] = df_issues.apply(subtask_check, axis=1)

# Summary projects check
print(f'Validation all projects data ({", ".join(list(projects_mapping.keys()))}), projects level')
df_projects = df_issues.groupby(['jira_project', 'gitlab_project'], as_index=False).agg(
    jira_issues=('jira_issue', 'count'),
    gitlab_issues=('gitlab_issue', 'count'),
    jira_comments=('jira_comments', 'sum'),
    gitlab_comments=('gitlab_comments', 'sum'),
    jira_worklogs=('jira_worklogs', 'sum'),
    gitlab_worklogs=('gitlab_worklogs', 'sum'),
    jira_worklogs_comments=('jira_worklogs_comments', 'sum'),
    gitlab_worklogs_comments=('gitlab_worklogs_comments', 'sum'),
    jira_logged_time_sec=('jira_logged_time_sec', 'sum'),
    gitlab_logged_time_sec=('gitlab_logged_time_sec', 'sum'),
    jira_attachments=('jira_attachments', 'sum'),
    gitlab_attachments=('gitlab_attachments', 'sum'),
    jira_time_estimate=('jira_time_estimate', 'sum'),
    gitlab_time_estimate=('gitlab_time_estimate', 'sum'),
)

columns_to_check_project = ['issues', 'comments', 'worklogs', 'worklogs_comments', 'logged_time_sec', 'attachments', 'time_estimate']
for column in columns_to_check_project:
    df_projects = data_check(df_projects, column)

# Saving reports into disk
print('Creating reports') 
df_issues.to_csv('Check/Issues_check.csv', 
                   index=False, 
                #    header=False,
                   mode='a')  
df_projects.to_csv('Check/Projects_check.csv', 
                   index=False, 
                #    header=False,
                   mode='a')