from fabric.api import *

# the user to use for the remote commands
env.user = 'root'
# the servers where the commands are executed
env.hosts = ['ttennis.life']


def deploy(branch='master'):
    # go to project dir
    run('cd ttrating')
    # pull changes from git
    run(f'git pull origin {branch}')
    # run db migrations
    run('python manage.py db upgrade')
    # stop application
    run('kill -9 `cat app.pid`')
    # run application
    run('nohup python app.py &')
    run('echo $! > app.pid')
