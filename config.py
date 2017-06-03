# -*- coding: utf-8 -*-
APP_NAME = 'ttennis'
APP_DESCRIPTION = 'Table tennis Ukraine'
PAGE_META_DESCRIPTION = u'Рейтинг по настольному теннису, ' \
                        u'Рейтинг настільного тенісу'
PAGE_META_KEYWORDS = \
    u'Table tennis Ratings, Ranks, ttennis.life, статистика, рейтинг, ' \
    u'настільний теніс, настольный теннис, турніри, турниры'
BRAND = 'ttennis.life'
EMAIL = 'ttennis.life.ua@gmail.com'

SECURITY_PASSWORD_SALT = '12345'
SECRET_KEY = 'secret'

SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
SQLALCHEMY_ECHO = False

CACHE_TYPE = 'simple'
CACHE_DEFAULT_TIMEOUT = 3600 * 4

SUPPORTED_LANGUAGES = {'ru': u'Русский', 'uk': u'Українська'}
BABEL_DEFAULT_LOCALE = 'uk'

MODE = 'DEV'  # DEV | PROD
