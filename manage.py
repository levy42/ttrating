# -*- coding: utf-8 -*-
import os
import re

from flask.ext.script import Manager

import config
from app import app, db
from services import parser

manager = Manager(app)


@manager.command
def initdb():
    """Creates all database tables."""
    db.create_all()


@manager.command
def dropdb():
    """Drops all database tables."""
    db.drop_all()


@manager.command
def parse_world():
    parser.parse_world_rating()


@manager.command
def parse_world_all():
    parser.parse_world_rating_all()


@manager.command
def parse_ua():
    parser.parse_ua()


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
    statistics.load_topics()
    statistics.calculate(statistics.calculate(statistics.Period.ENTIRE))
    statistics.calculate(statistics.calculate(statistics.Period.MONTH))
    statistics.calculate(statistics.calculate(statistics.Period.YEAR))


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
def start():
    os.system('nohup python app.py &')
    os.system('echo $! > app.pid')


@manager.command
def stop():
    if os.path.exists('app.pid'):
        os.system('kill %s' % open('app.pid').read())


@manager.command
def restart():
    stop()
    start()


@manager.command
def deploy():
    os.system('git pull')
    initdb()
    restart()


if __name__ == '__main__':
    manager.run()
