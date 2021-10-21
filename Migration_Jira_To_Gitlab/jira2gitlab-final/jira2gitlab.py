import gitlab
import os
import pandas as pd
import re
import urllib3
from jira import JIRA
from jira2markdown import convert

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
jira_project = ''

# Giltab section
gitlab_url = ''
gitlab_private_token = ''
gitlab_project_id =
gitlab_ssl_verify = False # Set to False if you want to ignore ssl warnings
gl = gitlab.Gitlab(gitlab_url, private_token=gitlab_private_token, ssl_verify=gitlab_ssl_verify)


def search_user(email):
    try:
        user_id = gl.users.list(search=email)[0].attributes['id']
    except IndexError:
        return None
    return user_id


def create_impersonate_token(email):
    try:
        user_id = gl.users.list(search=email)[0].attributes['id']
        impersonate_token = gl.users.get(user_id).impersonationtokens.create({'name': 'impersonate_token',
                                                                              'scopes': ['api']})
        impersonate_token_value = impersonate_token.token
        impersonate_token_id = impersonate_token.id
    except IndexError:
        return None
    return impersonate_token_value, impersonate_token_id


def convert_text(ct, adf, adf_fname, adf_furl):
    ct = re.sub(r'\r', '', ct)
    # Add separator between numbered lists
    ct = re.sub(r'(\n){2,}\s?(#)', r'  \1-separator-\n\2', ct)
    # Delete whitespaces in the lines with numbered lists because of converting issue
    ct = re.sub(r'\n\s+#', r'\n#', ct)
    # Delete whitespaces in the lines with bulleted lists because of converting issue
    ct = re.sub(r'\n\s+\*', r'\n*', ct)
    ct = convert(ct)
    # Change links to the attachments on attachments in Gitlab (Use after converting into Markdown!!!)
    for up_file in adf[[adf_fname, adf_furl]].values:
        ct = re.sub(r'\(%s\)' % up_file[0], r'(%s)' % up_file[1], ct)
    return ct

# Get all issues in the project
issues_in_proj = jira.search_issues('project=%s ORDER BY key asc' % jira_project, maxResults=0)
# Define attachments dir locally
attachments_dir = str(re.sub(r'\\', '/', os.getcwd())) + '/' + 'attachments'

# Auth into Gitlab as current user (gitlab_private_token)
gl.auth()
# Get gitlab project
gitlab_project = gl.projects.get(gitlab_project_id)

# Create attachments dir locally
if not os.path.exists(attachments_dir):
    os.mkdir(attachments_dir)

# Users (Start)
# Create empty list for users from Jira
jira_users_list = list()
# Get current user Id and use it in the next as Id for absent users
current_user_id = gl.user.attributes['id']
# Fill the list for Jira users
for issue_in_proj in issues_in_proj:
    issue = jira.issue(issue_in_proj.key)
    # Get assignee email
    if issue.fields.assignee:
        jira_users_list.append(issue.fields.assignee.emailAddress)
    # Get reporter email
    jira_users_list.append(issue.fields.creator.emailAddress)
    # Get reporters email
    for comment in issue.fields.comment.comments:
        jira_users_list.append(jira.comment(issue_in_proj.key, comment).author.emailAddress)

# Convert email of the users to lower case
jira_users_list = [item.lower() for item in jira_users_list]
# Delete duplicates from list of the users
unique_jira_users_list = [x for i, x in enumerate(jira_users_list) if i == jira_users_list.index(x)]
# Create pandas dataframe from the list for Jira users
df_users = pd.DataFrame(unique_jira_users_list, columns=['email'])
# Fill column with Id of Jira users in Gitlab based on email addresses
df_users['gitlabUserId'] = df_users['email'].apply(search_user)
# Create impersonate tokens for users in Gitlab
df_users['impersonateTokenId'] = df_users['email'].apply(create_impersonate_token)
df_users[['tokenValue', 'tokenId']] = pd.DataFrame(df_users['impersonateTokenId'].tolist(), index=df_users.index)
df_users = df_users.drop(columns=['impersonateTokenId'])
# Set current user Id as Id for absent users
df_users['gitlabUserId'] = df_users['gitlabUserId'].fillna(current_user_id)
# Users (End)

# Attachments (Start)
attachments_list = []

for issue_in_proj in issues_in_proj:
    issue = jira.issue(issue_in_proj.key)
    if issue.fields.attachment:
        if not os.path.exists(attachments_dir + '/' + str(issue_in_proj.key)):
            os.mkdir(attachments_dir + '/' + str(issue_in_proj.key))
        for attachment_loop in issue.fields.attachment:
            attachment = jira.attachment(attachment_loop.id)
            attachment_content = attachment.get()
            with open(str(attachments_dir + '/' + str(issue_in_proj.key)) + '/' + str(attachment_loop.filename),
                      'wb') as f:
                f.write(attachment_content)
            attachments_list.append({'jiraIssueId': issue_in_proj.key, 'attachmentId': attachment_loop.id,
                                     'attachmentFileName': attachment_loop.filename,
                                     'attachmentPath': str(attachments_dir + '/' + str(issue_in_proj.key)) + '/' + str(
                                         attachment_loop.filename)})
df_attachments = pd.DataFrame(attachments_list)

for attachment_from_df in df_attachments[['attachmentFileName', 'attachmentPath']].values:
    gitlabUploadedFile = gitlab_project.upload(attachment_from_df[0], filepath=attachment_from_df[1])
    df_attachments.loc[df_attachments['attachmentFileName'] == attachment_from_df[0], 'Markdown'] = gitlabUploadedFile['markdown']
    df_attachments.loc[df_attachments['attachmentFileName'] == attachment_from_df[0], 'URL'] = gitlabUploadedFile['url']
# Attachments (End)

# Issues (Start)
for issue_in_proj in issues_in_proj:
    # Empty assignee variable. Must be empty for case with Unassigned issue in Jira
    assignee_id = None
    issue = jira.issue(issue_in_proj.key)
    # Description
    desc = issue.fields.description
    # Assignee => assignee_ids
    if issue.fields.assignee:
        assignee_id = issue.fields.assignee.emailAddress.lower()
        assignee_id = df_users.at[df_users.loc[df_users['email'] == assignee_id].index[0], 'gitlabUserId']
    # Issue type => label
    issue_type = issue.fields.issuetype.name.lower()
    # Is it a subtask
    is_subtask = issue.fields.issuetype.subtask
    # Creator
    creator = issue.fields.creator.emailAddress.lower()
    creator = df_users.at[df_users.loc[df_users['email'] == creator].index[0], 'gitlabUserId']
    # When was created
    created = issue.fields.created
    # When was updated
    updated = issue.fields.updated
    # Summary => title
    title = issue.fields.summary
    # Status
    status = issue.fields.status.statusCategory.key.lower()
    # Convert description
    if desc is not None:
        desc = convert_text(desc, df_attachments, 'attachmentFileName', 'URL')
    # Set assignee id based on condition
    if assignee_id is None:
        assingee_id = None
    else:
        assingee_id = int(assignee_id)
    issue_body = {'title': str(title),
                 'description': str(desc),
                 'labels': [str(issue_type)],
                 'iid': int(issue_in_proj.id),
                 'assignee_ids': [assingee_id],
                 'created_at': str(created)
                 }
    # Print info about creating issue in Gitlab
    print('Creating issue with ' + 'id: ' + str(issue_in_proj.id) + ', ' + 'key: ' + str(issue_in_proj.key) + ', '
          + 'type: ' + str(issue_type) + ', ' + 'subtask: ' + str(is_subtask) + ', '
          + 'assignee_id: ' + str(assingee_id) + ', ' + 'creator_id: ' + str(creator))
    impersonate_token = df_users.at[df_users.loc[df_users['gitlabUserId'] == creator].index[0], 'tokenValue']
    gl_user = gitlab.Gitlab(gitlab_url, private_token=impersonate_token, ssl_verify=gitlab_ssl_verify)
    gl_user.auth()
    gitlab_project_user = gl_user.projects.get(gitlab_project_id)
    # Create issue in Gitlab
    issue_gitlab = gitlab_project_user.issues.create(issue_body)
    # Set closing note if task id Done
    if status == "done":
        if assingee_id is None:
            issue_gitlab_to_close = gitlab_project_user.issues.get(issue_in_proj.id)
            issue_gitlab_to_close.notes.create({'body': '/close',
                                                'created_at': str(updated)})
        else:
            impersonate_token = df_users.at[df_users.loc[df_users['gitlabUserId'] == assingee_id].index[0], 'tokenValue']
            gl_close_comment = gitlab.Gitlab(gitlab_url, private_token=impersonate_token, ssl_verify=gitlab_ssl_verify)
            gl_close_comment.auth()
            gitlab_project_close_comment = gl_close_comment.projects.get(gitlab_project_id)
            issue_gitlab_to_close = gitlab_project_close_comment.issues.get(issue_in_proj.id)
            issue_gitlab_to_close.notes.create({'body': '/close',
                                                'created_at': str(updated)})
    # Create link between subtasks and tasks
    if is_subtask:
        parent = issue.fields.parent.id
        data = {
            'target_project_id': int(gitlab_project_id),
            'target_issue_iid': int(parent),
            'link_type': 'relates_to'
        }
        issue_link = gitlab_project_user.issues.get(issue_gitlab.iid)
        # Print info about creating links
        print('\tCreating link between child issue ' + str(issue_gitlab.iid) + ' and parent issue id: ' + str(parent)
              + ' with key: ' + str(issue.fields.parent.key))
        issue_link.links.create(data)
# Issues (End)

# Comments and Worklogs (Start)
for issue_in_proj in issues_in_proj:
    issue = jira.issue(issue_in_proj.key)
    comments = jira.comments(issue)
    for com in range(0, len(comments)):
        comment = jira.comment(issue_in_proj.key, comments[com])
        comment_created = comment.created
        comment_author = int(df_users.at[df_users.loc[df_users['email'] == comment.author.emailAddress.lower()].index[0],
                                     'gitlabUserId'])
        comment_body = convert_text(comment.body, df_attachments, 'attachmentFileName', 'URL')
        impersonate_token_comment = df_users.at[df_users.loc[df_users['gitlabUserId'] == comment_author].index[0], 'tokenValue']
        gl_user_comment = gitlab.Gitlab(gitlab_url, private_token=impersonate_token_comment, ssl_verify=gitlab_ssl_verify)
        gl_user_comment.auth()
        gitlab_project_user_comment = gl_user_comment.projects.get(gitlab_project_id)
        issue_gitlab = gitlab_project_user_comment.issues.get(issue_in_proj.id)
        comment_note = issue_gitlab.notes.create({'body': str(comment_body),
                                                  'created_at': str(comment_created),
                                                  'author': comment_author})
    # Estimate
    if issue.fields.timeoriginalestimate:
        estimate_jira = issue.fields.timeoriginalestimate
        estimate_gitlab_message = '/estimate ' + str(estimate_jira) + 's'
        gitlab_project_estimate = gl.projects.get(gitlab_project_id)
        issue_gitlab_estimate = gitlab_project_estimate.issues.get(issue_in_proj.id)
        issue_gitlab_estimate.notes.create({'body': estimate_gitlab_message})

    # Worklogs
    if issue.fields.worklog.worklogs:
        for worklog in range(0, len(issue.fields.worklog.worklogs)):
            worklog_author = issue.fields.worklog.worklogs[worklog].author.emailAddress.lower()
            worklog_time_spend = issue.fields.worklog.worklogs[worklog].timeSpent
            worklog_updated = issue.fields.worklog.worklogs[worklog].updated
            worklog_comment = issue.fields.worklog.worklogs[worklog].comment
            impersonate_token_worklog = df_users.at[df_users.loc[df_users['email'] == worklog_author].index[0],
                                                    'tokenValue']
            gl_user_worklog = gitlab.Gitlab(gitlab_url, private_token=impersonate_token_worklog,
                                            ssl_verify=gitlab_ssl_verify)
            gl_user_worklog.auth()
            gitlab_project_user_worklog = gl_user_worklog.projects.get(gitlab_project_id)
            issue_gitlab_worklog = gitlab_project_user_worklog.issues.get(issue_in_proj.id)
            # Create worklog comment based on condition
            if worklog_comment:
                worklog_comment = convert_text(worklog_comment, df_attachments, 'attachmentFileName', 'URL')
                message_body = 'Worklog message:  \n' + \
                               str(worklog_comment) + '\n' + \
                               '/spend ' + str(worklog_time_spend)
            else:
                message_body = '/spend ' + str(worklog_time_spend)
            # Create worklog note
            issue_gitlab_worklog.notes.create({'body': message_body, 'created_at': str(worklog_updated)})
# Comments and Worklogs (End)

# Delete impersonate tokens
for row in df_users.itertuples(index=True):
    gl.users.get(row.gitlabUserId).impersonationtokens.delete(row.tokenId)
