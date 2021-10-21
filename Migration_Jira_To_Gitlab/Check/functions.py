import numpy as np
import re


def time_searching(time, criterion):
    if re.search(f'(\d+){criterion}', time):
        return int(re.search(f'(\d+){criterion}', time).group(0).replace(f'{criterion}', ''))
    else:
        return 0

  
def time_converting(time):
    minutes = time_searching(time, 'm')
    hours = time_searching(time, 'h') 
    days = time_searching(time, 'd')
    weeks = time_searching(time, 'w')
    
    result = weeks*40*60*60 + days*8*60*60 + hours*60*60 + minutes*60
    return result


def subtask_check(df):
    if df['jira_issue_type'] in ['sub-task', 'test']:
        if ('subtask' in df['gitlab_labels']) & (int(df['jira_parent']) in df['gitlab_links']):
            return 'ok'
        elif ('test' in df['gitlab_labels']) & (int(df['jira_parent']) in df['gitlab_links']):
            return 'ok'
        else:
            return 'need to check'
    elif df['jira_subtasks'] != [-1]:
        if df['jira_subtasks'].sort() == df['gitlab_links'].sort():
            return 'ok'
        else:
            return 'need to check'
    else:
        return 'not a subtask & doesn\'t have it'

   
def status_check(df):
    if df['jira_status'] in ['new', 'indeterminate'] and df['gitlab_status'] == 'opened':
        return 'ok'
    elif df['jira_status'] == 'done' and df['gitlab_status'] == 'closed':
        return 'ok'
    else:
        return 'need to check'
    

def data_check(df, criterion):
    df[criterion] = np.where(df[f'jira_{criterion}'] == df[f'gitlab_{criterion}'], 'ok', 'need to check')
    return df