import json
import traceback
import requests

from flask import current_app

import models


def _translate_yandex(text, language):
    API_KEY = current_app.config['YANDEX_API_KEY']
    if isinstance(text, str):
        url = f'https://translate.yandex.net/api/v1.5/tr.json/translate?key=' \
              f'{API_KEY}&text={text}&lang={language}'
        translation = requests.get(url)
        if translation.status_code != 200:
            print(text, language)
            traceback.print_exc()
            return text
        return json.loads(translation.text)['text'][0]
    if isinstance(text, list):
        url = f'https://translate.yandex.net/api/v1.5/tr.json/translate?key=' \
              f'{API_KEY}&lang={language}'
        for t in text:
            url += f'&text={t}'
        translation = requests.get(url)
        if translation.status_code != 200:
            print(text, language)
            traceback.print_exc()
            return text

        return json.loads(translation.text)['text']


def _translate(text, language, engine='yandex'):
    if engine == 'yandex':
        return _translate_yandex(text, language)
    else:
        raise NotImplementedError


def get_translated(text, lang):
    if not isinstance(text, str):
        return text
    t = models.Translation.query.get(f'{text}_{lang}')
    if t:
        return t.translated
    else:
        return text


def search_translations(text, lang=None):
    matches = models.Translation.query.filter(
        models.Translation.id.like(text + '%'),
        models.Translation.locale == lang).all()
    # trim last 3 chars to cut off language prefix (e.g. '_uk')
    return [t.id[:-3] for t in matches]


def add_translations(arr, lang):
    for s in arr:
        if not models.Translation.query.get(s + '_' + lang):
            t = models.Translation(s, lang)
            t.translated = _translate(s, lang)
            models.db.session.add(t)
        else:
            print(models.Translation.query.get(s + '_' + lang).translated)
    models.db.session.commit()


def translate_all(lang='uk'):
    current_app.logger.info('Players')
    players = models.Player.query.all()
    for player in players:
        if not models.Translation.query.get(player.name + f'_{lang}'):
            ua_name = models.Translation(player.name, lang)
            ua_name.translated = _translate(player.name, lang)
            models.db.session.add(ua_name)
            print(ua_name.translated)

    models.db.session.commit()

    current_app.logger.info('Cities')
    cities = models.City.query.all()
    for c in cities:
        if not models.Translation.query.get(c.name + f'_{lang}'):
            ua_name = models.Translation(c.name, lang)
            ua_name.translated = _translate(c.name, lang)
            models.db.session.add(ua_name)
            print(ua_name.translated)

    models.db.session.commit()

    current_app.loggerger.info('Tournaments')
    tourns = models.Tournament.query.all()
    for t in tourns:
        if not models.Translation.query.get(t.name + f'_{lang}'):
            ua_name = models.Translation(t.name, lang)
            ua_name.translated = _translate(t.name, lang)
            models.db.session.add(ua_name)
            print(ua_name.translated)

    models.db.session.commit()
