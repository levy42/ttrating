import json
import traceback
import six

import requests

import models

API_KEY = 'trnsl.1.1.20170317T133701Z.9ef6d1256a8576ac.573492aef994d1df8f13b84c3740dc337dd52104'
TRANSLATIONS = {}
RETRANSLATION = {}


def _translate_yandex(text, language):
    if isinstance(text, str):
        url = 'https://translate.yandex.net/api/v1.5/tr.json/translate?key=' \
              '%s&text=%s&lang=%s' % (
                  API_KEY, text, language)
        translation = requests.get(url)
        if translation.status_code != 200:
            print(text, language)
            traceback.print_exc()
            return text
        return json.loads(translation.text)['text'][0]
    if isinstance(text, list):
        url = 'https://translate.yandex.net/api/v1.5/tr.json/translate?key=' \
              '%s&lang=%s' % (
                  API_KEY, language)
        for t in text:
            url += '&text=%s' % t
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


def load_transations():
    global TRANSLATIONS, RETRANSLATION

    def retrieve_origin(id):
        return id.rsplit('_', 1)[0]

    TRANSLATIONS = {t.id: t for t in models.Translation.query.all()}
    for t in TRANSLATIONS.values():
        if not t.origin:
            t.origin = retrieve_origin(t.id)

    RETRANSLATION = {v: retrieve_origin(k) for k, v in TRANSLATIONS.items()}


def translate(text, lang):
    if not isinstance(text, six.text_type):
        return text
    t = TRANSLATIONS.get(text + '_' + lang)
    if t:
        return t.translated
    else:
        return text


def retranslate(text):
    return RETRANSLATION.get(text, text)


def search_translations(text, lang=None):
    return [t.origin for t in TRANSLATIONS.values() if
            t.locale == lang and (text in t.translated or text in t.origin)]


def add_translations(arr, lang):
    for s in arr:
        if not models.Translation.query.get(s + '_' + lang):
            t = models.Translation(s, lang)
            t.translated = _translate(s, lang)
            models.db.session.add(t)
        else:
            print(models.Translation.query.get(s + '_' + lang).translated)
    models.db.session.commit()


def translate_all():
    print('Players')
    players = models.Player.query.all()
    for player in players:
        if not models.Translation.query.get(player.name + '_uk'):
            ua_name = models.Translation(player.name, 'uk')
            ua_name.translated = _translate(player.name, 'uk')
            models.db.session.add(ua_name)
            print(ua_name.translated)

    models.db.session.commit()

    print('Cities')
    cities = models.City.query.all()
    for c in cities:
        if not models.Translation.query.get(c.name + '_uk'):
            ua_name = models.Translation(c.name, 'uk')
            ua_name.translated = _translate(c.name, 'uk')
            models.db.session.add(ua_name)
            print(ua_name.translated)

    models.db.session.commit()

    print('Tournaments')
    tourns = models.Tournament.query.all()
    for t in tourns:
        if not models.Translation.query.get(t.name + '_uk'):
            ua_name = models.Translation(t.name, 'uk')
            ua_name.translated = _translate(t.name, 'uk')
            models.db.session.add(ua_name)
            print(ua_name.translated)

    models.db.session.commit()
