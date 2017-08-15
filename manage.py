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
    statistics.load_topics()
    statistics.calculate(statistics.Period.ENTIRE)
    statistics.calculate(statistics.Period.MONTH)
    statistics.calculate(statistics.Period.YEAR)


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
def update_player_info():
    import models
    players = models.Player.query.all()
    for p in players:
        if p.rating and p.rating > p.max:
            p.max = p.rating
            models.db.session.add(p)
    models.db.session.commit()
    print('Updated max rating values')
    from services import rating_update
    rating_update.update_player_info()


@manager.command
def tmp():
    from app import _
    import glob
    import os
    import re

    os.chdir(".")
    files = []

    for f in glob.iglob("./**/*.py", recursive=True):
        files.append(f)

    for f in glob.iglob("./**/*.html", recursive=True):
        files.append(f)

    print(files)
    all_phrases = set()
    for f in files:
        data = open(f).read()
        phrases = re.findall("{{ _\([\',\"](.+)[\',\"]\) }}", data)
        if phrases:
            all_phrases.update(phrases)

    print(all_phrases)
    all_phrases = sorted(all_phrases, key=lambda x: -len(x))

    word_dict = {}
    for phrase in all_phrases:
        uk_version = _(phrase)
        word_dict[phrase] = uk_version
        print(uk_version)

    for f in files:
        with open(f, 'w') as fd:
            data = fd.read()
            for phrase in all_phrases:
                if phrase not in data:
                    continue
                data = data.replace(f"{{ _('{phrase}') }}",
                                    f"{{ _('{word_dict[phrase]}') }}")

    with open('translation/ru/LC_MESSAGES/messages.po', 'w') as f:
        data = f.read()
        for w in all_phrases:
            data = data.replace(w, word_dict[w])


if __name__ == '__main__':
    manager.run()
