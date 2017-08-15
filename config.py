# -*- coding: utf-8 -*-
APP_NAME = 'ttennis'
SERVER_NAME = 'localhost:10000'
PREFERRED_URL_SCHEME = 'http'
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
HOME_PAGE = 'rating'

# API
YANDEX_API_KEY = 'trnsl.1.1.20170317T133701Z.9ef6d1256a8576ac.573492aef' \
                 '994d1df8f13b84c3740dc337dd52104'

# MAIL
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 465
MAIL_USE_SSL = True
MAIL_USERNAME = 'ttennis.life.ua'
MAIL_PASSWORD = 'ttennispassword'
MAIL_DEFAULT_SENDER = 'ttennis.life.ua@gmail.com'

# JOBS
JOBS = [
    {
        'id': 'update_ua_rating',
        'func': 'app:update_ua_rating',
        'trigger': 'interval',
        'seconds': 3660
    },
    {
        'id': 'update_world_rating',
        'func': 'app:update_world_rating',
        'trigger': 'interval',
        'seconds': 3600
    },
    {
        'id': 'delete_expired_users',
        'func': 'app:delete_expired_users',
        'trigger': 'interval',
        'seconds': 3660 * 24
    }
]
SCHEDULER_API_ENABLED = True
