import gitlab
import urllib3

# Disable "InsecureRequestWarning" messages
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

gitlab_url = ''
gitlab_private_token = ''
gitlab_project_id =
gitlab_ssl_verify = False # Set to False if you want to ignore ssl warnings


gl = gitlab.Gitlab(gitlab_url, private_token=gitlab_private_token, ssl_verify=gitlab_ssl_verify)
gl.auth()

project = gl.projects.get(gitlab_project_id)
issues_gitlab = project.issues.list()

for i in issues_gitlab:
    print(i.iid)
    project.issues.delete(i.iid)
