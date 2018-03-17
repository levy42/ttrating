import os
import re

from flask.ext.script import Manager

from app import app, db
import models
import config
from services import parser
from flask_migrate import Migrate, MigrateCommand

migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

@manager.command
def parse_world():
    parser.parse_world_rating()
    db.create_all()


@manager.command
def parse_world_all():
    parser.parse_world_rating_all()


@manager.command
def parse_ua():
    parser.parse_ua()
    calculate_statistics()


@manager.command
def parse_ua_all():
    parser.parse_ua_all()


@manager.command
def translate():
    from services import translator
    translator.translate_all()


@manager.command
def calculate_statistics():
    from services import statistics
    statistics.calculate()


@manager.command
def update_statistics():
    from services import statistics
    models.TopicIssue.query.delete()
    statistics.calculate()


@manager.command
def update_user_info():
    from services import rating_update
    rating_update.update_player_info()


@manager.command
def create_translations():
    words = set()
    path = 'templates'
    files = [f for f in os.listdir(path) if
             os.path.isfile(os.path.join(path, f))]
    for file in files:
        with open(os.path.join('templates', file)) as f:
            words.update(re.findall("_\(\'([^']+)\'\)", f.read()))

    for lang in config.SUPPORTED_LANGUAGES:
        with open(os.path.join('translations', lang,
                               'LC_MESSAGES/messages.po'), 'r+') as f:
            text = f.read()
            for w in words:
                if w not in text:
                    f.write('\nmsgid "%s"\nmsgstr ""\n' % w)


@manager.command
def make_translations():
    os.system('pybabel compile -d translations')


@manager.command
def initdb():
    db.create_all()


@manager.command
def deploy(branch='master'):
    host = config.HOST
    os.system(
        f"ssh {host} 'cd ttrating && "
        f"git fetch && "
        f"git checkout {branch} && "
        f"git pull origin {branch} && "
        f"python3.6 manage.py db upgrade && "
        f"(kill -9 `cat app.pid` ; "
        f"nohup python3.6 app.py & "
        f"echo $! > app.pid)'")


if __name__ == '__main__':
    manager.run()
