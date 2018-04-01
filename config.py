APP_NAME = 'ttennis'
SERVER_NAME = 'ttennis.life'
PREFERRED_URL_SCHEME = 'http'
BRAND = 'ttennis.life'
EMAIL = 'ttennis.life.ua@gmail.com'
SECURITY_PASSWORD_SALT = '12345'
SECRET_KEY = 'secret'
SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
SQLALCHEMY_TRACK_MODIFICATIONS=False
CACHE_TYPE = 'simple'
CACHE_DEFAULT_TIMEOUT = 0  # never expires
SUPPORTED_LANGUAGES = {'ru': 'Русский', 'uk': 'Українська'}
BABEL_DEFAULT_LOCALE = 'uk'
HOME_PAGE = 'rating.rating'
# API
YANDEX_API_KEY = '<your_api_key>'
# MAIL
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 465
MAIL_USE_SSL = True
MAIL_USERNAME = 'ttennis.life.ua'
MAIL_PASSWORD = '*****'
MAIL_DEFAULT_SENDER = EMAIL
ADMINS = ['vitaliylevitskiand@gmail.com']
BLUEPRINTS = ['views.rating', 'views.world_rating', 'views.subscribers']
LOG_PATH = f'{APP_NAME}.log'  # store in working dir
LOG_FORMAT = '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'

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
    # {
    #     'id': 'test',
    #     'func': 'tasks:test',
    #     'trigger': 'interval',
    #     'seconds': 2
    # }
]
SCHEDULER_API_ENABLED = True
# DEPLOYMENT
DEPLOY_HOST = 'root@ttennis.life'
# SEO
APP_DESCRIPTION = 'Table tennis Ukraine'
PAGE_META_DESCRIPTION = 'Рейтинг по настольному теннису, ' \
                        'Рейтинг настільного тенісу'
PAGE_META_KEYWORDS = \
    'Table tennis Ratings, Ranks, ttennis.life, статистика, рейтинг, ' \
    'настільний теніс, настольный теннис, турніри, турниры'
# ADMIN AUTH
ADMIN_PASS = 'admin'
ADMIN_USERNAME = 'admin'
