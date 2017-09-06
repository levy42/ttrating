APP_NAME = 'ttennis'
SERVER_NAME = 'localhost:10000'
PREFERRED_URL_SCHEME = 'http'
APP_DESCRIPTION = 'Table tennis Ukraine'
PAGE_META_DESCRIPTION = 'Рейтинг по настольному теннису, ' \
                        'Рейтинг настільного тенісу'
PAGE_META_KEYWORDS = \
    'Table tennis Ratings, Ranks, ttennis.life, статистика, рейтинг, ' \
    'настільний теніс, настольный теннис, турніри, турниры'
BRAND = 'ttennis.life'
EMAIL = 'ttennis.life.ua@gmail.com'

SECURITY_PASSWORD_SALT = '12345'
SECRET_KEY = 'secret'

SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
SQLALCHEMY_ECHO = False

CACHE_TYPE = 'simple'
CACHE_DEFAULT_TIMEOUT = 0  # never expires

SUPPORTED_LANGUAGES = {'ru': 'Русский', 'uk': 'Українська'}
BABEL_DEFAULT_LOCALE = 'uk'

MODE = 'DEV'  # DEV | PROD
HOME_PAGE = 'main.rating'

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
ADMINS = ['vitaliylevitskiabd@gmail.com']

# JOBS
JOBS = [
    {
        'id': 'update_ua_rating',
        'func': 'tasks:update_ua_rating',
        'trigger': 'interval',
        'seconds': 3660
    },
    {
        'id': 'update_world_rating',
        'func': 'tasks:update_world_rating',
        'trigger': 'interval',
        'seconds': 3600
    },
    {
        'id': 'delete_expired_users',
        'func': 'tasks:delete_expired_users',
        'trigger': 'interval',
        'seconds': 3660 * 24
    },
    {
        'id': 'test',
        'func': 'tasks:test',
        'trigger': 'interval',
        'seconds': 2
    }
]
SCHEDULER_API_ENABLED = True
FLASK_DEBUG = True