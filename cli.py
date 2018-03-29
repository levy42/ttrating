import click
import os
import re

from app import app, db
import models
import config
from services import parser
from flask.cli import with_appcontext
from flask_migrate import Migrate

migrate = Migrate(app, db)


@app.cli.command()
@with_appcontext
def parse_world():
    parser.parse_world_rating()
    db.create_all()


@app.cli.command()
@with_appcontext
def parse_world_all():
    parser.parse_world_rating_all()


@app.cli.command()
@with_appcontext
def parse_ua():
    parser.parse_ua()
    calculate_statistics()


@app.cli.command()
@with_appcontext
def parse_ua_all():
    parser.parse_ua_all()


@app.cli.command()
@with_appcontext
def translate():
    from services import translator
    translator.translate_all()


@app.cli.command()
@with_appcontext
def calculate_statistics():
    from services import statistics
    statistics.calculate()


@app.cli.command()
@with_appcontext
def update_statistics():
    from services import statistics
    models.TopicIssue.query.delete()
    statistics.calculate()


@app.cli.command()
@with_appcontext
def update_user_info():
    from services import rating_update
    rating_update.update_player_info()


@app.cli.command()
@with_appcontext
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


@app.cli.command()
def make_translations():
    os.system('pybabel compile -d translations')


@app.cli.command()
def initdb():
    db.create_all()


@app.cli.command()
@click.argument('migrate')
@click.argument('branch')
def deploy(migrate=False, branch='master'):
    # TODO do it better
    host = config.HOST
    migrate_script = "python3.6 manage.py db upgrade &&"
    os.system(
        f"ssh {host} 'cd ttrating && "
        f"git fetch && "
        f"git checkout {branch} && "
        f"git pull origin {branch} && "
        f"pip3.6 install -r requirements.txt && "
        f"{migrate_script if migrate else ''} "
        f"(kill -9 `cat app.pid` ; "
        f"nohup python3.6 app.py & "
        f"echo $! > app.pid)'")
