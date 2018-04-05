import click
import os
import re
import logging

from app import app, db
import models
import config
from services import parser, rating_update, statistics, translator, games_chain
from flask.cli import with_appcontext
from flask_migrate import Migrate

app.logger.handlers[1].setLevel(logging.DEBUG)
app.logger.setLevel(logging.DEBUG)
app.logger.handlers[1].setFormatter(logging.Formatter('%(message)s'))

migrate = Migrate(app, db)


@app.cli.command(help='Runs parsing world rating for last month.')
@with_appcontext
def parse_world():
    parser.parse_world_rating()


@app.cli.command(help='Runs parsing world rating for all months.')
@with_appcontext
def parse_world_all():
    parser.parse_world_rating_all()


@app.cli.command(help='Runs parsing UA rating for last month.')
@with_appcontext
def parse_ua():
    parser.parse_ua()
    update_statistics()


@app.cli.command(help='Runs tasks for updating ratings.')
@with_appcontext
def update_ua_rating():
    rating_update.update_ua()


@app.cli.command(help='Runs parsing UA rating for all months.')
@with_appcontext
def parse_ua_all():
    parser.parse_ua_all()


@app.cli.command(help='Looks for new names in DB and create '
                      'translations for them.')
@with_appcontext
def translate_names():
    translator.translate_all()


@app.cli.command(help='Updates rating statistics.')
@with_appcontext
def update_statistics():
    models.TopicIssue.query.delete()
    statistics.calculate()


@app.cli.command(help='Updates players statistics.')
@with_appcontext
def update_players_stat():
    rating_update.update_player_stats()


@app.cli.command(help='Updates (or create) player games graph.')
@with_appcontext
def update_games_graph():
    games_chain.update_graphs()


@app.cli.command(help='Looks for new string and automatically '
                      'creates translations for then.')
@with_appcontext
def create_translations():
    words = set()
    path = 'templates'
    files = [f for f in os.listdir(path) if
             os.path.isfile(os.path.join(path, f))]
    for file in files:
        with open(os.path.join('templates', file)) as f:
            words.update(re.findall("_\(\'([^']+)\'\)", f.read()))

    for lang in app.config['SUPPORTED_LANGUAGES']:
        with open(os.path.join('translations', lang,
                               'LC_MESSAGES/messages.po'), 'r+') as f:
            text = f.read()
            for w in words:
                if w not in text:
                    f.write('\nmsgid "%s"\nmsgstr ""\n' % w)


@app.cli.command(help='Runs translation compile.')
def compile_translations():
    os.system('pybabel compile -d translations')


@app.cli.command(help='Creates all tables.')
@with_appcontext
def initdb():
    db.create_all()


@app.cli.command(help='Runs deployment.')
@with_appcontext
@click.argument('branch', default='master')
@click.option('--migrate/--no-migrate', default=False)
@click.option('--run', '-run', multiple=True)
def deploy(migrate, branch, run):
    # TODO do it more readable, this is shit man
    host = app.config['DEPLOY_HOST']
    commands = [f'flask {command}' for command in run]
    commands_cli = ('&&' + '&&'.join(commands)) if run else ''
    print(
        f'''
        ssh {host} "cd ttrating &&
        git fetch &&
        git checkout {branch} &&
        git pull origin {branch} &&
        pip3.6 install -r requirements.txt &&
        export FLASK_APP=app.py APP_CONFIG=config.cfg &&
        {'FLASK_APP=cli.py flask db upgrade &&' if migrate else ''}
        (screen -S {config.APP_NAME} -X quit;
         screen -S {config.APP_NAME} -dm bash -c 'flask run --port 10000')
         {commands_cli}"
        '''
    )

