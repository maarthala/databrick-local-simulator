# ./jupyter-config/jupyter_notebook_config.py

c = get_config()
# c.NotebookApp.base_url = '/jupyter/'
c.NotebookApp.token = ''
c.NotebookApp.allow_origin = '*'
c.NotebookApp.disable_check_xsrf = True
