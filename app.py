import logging
import os
from logging.handlers import RotatingFileHandler
from importlib import import_module

import jinja2
from flask import (Flask, g, redirect, render_template, request, url_for,
                   Blueprint, Response)
from flask_babel import (Babel, _)
from flask_caching import Cache
from flask_mobility import Mobility
from jinja2 import filters
from flask_mail import Mail, Message
from flask_apscheduler import APScheduler

import config
from models import db
from views.admin import admin
from services.translator import get_translated

app = Flask(config.APP_NAME)
app.config.from_object(config)
app.config.from_pyfile(os.environ.get('APP_CONFIG', 'config.cfg'), silent=True)

main = Blueprint('main', 'main')
db.init_app(app)
admin.init_app(app)
cron = APScheduler()
babel = Babel(app)
Mobility(app)
cache = Cache(app, config=app.config)
setattr(app, 'cache', cache)
mail = Mail(app)


# logging
class FlaskMailLogHandler(logging.Handler):
    def __init__(self, mail, recipients, *args, **kwargs):
        super(FlaskMailLogHandler, self).__init__(*args, **kwargs)
        self.mail = mail
        self.recipients = recipients

    def emit(self, record):
        self.mail.send(Message(
            recipients=self.recipients,
            body=self.format(record),
            subject=f'{config.APP_NAME} ERROR!'))


if not app.debug:
    formatter = logging.Formatter(app.config['LOG_FORMAT'])
    handler = RotatingFileHandler(app.config['LOG_PATH'],
                                  maxBytes=1000000, backupCount=1)
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    handler.setLevel(logging.INFO)
    mail_handler = FlaskMailLogHandler(mail, app.config['ADMINS'])
    mail_handler.setLevel(logging.ERROR)
    mail_handler.setFormatter(formatter)
    app.logger.addHandler(mail_handler)


def mail_alert(text):
    mail.send(Message(
        recipients=app.config['ADMINS'],
        body=text,
        subject=f'{config.APP_NAME} ALERT!'))


# localization
month_abbr = ['', 'січ', 'лют', 'бер', 'кві', 'тра', 'чер', 'лип', 'сер',
              'вер', 'жов', 'лис', 'гру']


@babel.localeselector
def get_locale():
    return g.get('lang', app.config['BABEL_DEFAULT_LOCALE'])


@app.url_defaults
def set_language_code(endpoint, values):
    if 'lang' in values or not g.get('lang', None):
        return
    if app.url_map.is_endpoint_expecting(endpoint, 'lang'):
        values['lang'] = g.lang
    pass


@app.url_value_preprocessor
def get_lang_code(endpoint, values):
    if values is not None:
        lang = values.get('lang', None)
        if lang in app.config['SUPPORTED_LANGUAGES'].keys():
            g.lang = values.pop('lang', None)


@app.before_request
def ensure_lang_support():
    lang = g.get('lang', None)
    if lang not in app.config['SUPPORTED_LANGUAGES'].keys():
        g.lang = app.config['BABEL_DEFAULT_LOCALE']


# context filters

@jinja2.contextfilter
@app.template_filter(name='month_abbr')
def month_filter(context, value):
    return month_abbr[value]


@jinja2.contextfilter
@app.template_filter(name='color')
def number_color(context, value):
    if value > 0:
        value = f'<p style="color:green">+{value}</p>'
    elif value < 0:
        value = f'<p style="color:red">{value}</p>'
    else:
        return value
    return filters.do_mark_safe(value)


# custom template context
def translate_name(text):
    @cache.memoize(timeout=24 * 60 * 60)
    def _translate(_text, lang):
        return get_translated(_text, lang)

    return _translate(text, g.get('lang', app.config['BABEL_DEFAULT_LOCALE']))


def translate_array(arr):
    return [translate_name(_(x)) for x in arr]


def url_for_other_page(page):
    args = request.view_args.copy()
    args.update(request.args)
    args['page'] = page
    return url_for(request.endpoint, **args)


@app.context_processor
def dynamic_translate_processor():
    return dict(name=translate_name,
                translate_arr=translate_array,
                url_for_other_page=url_for_other_page)


@app.context_processor
def form_parameters():
    return {k: request.args.get(k) for k in request.args}


# base routes
@main.route('/about/')
def about():
    return render_template('about.html')


@app.route('/')
def home():
    return redirect(url_for(f'{app.config["HOME_PAGE"]}'))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


@app.before_first_request
def start_cron():
    cron.init_app(app)  # init scheduler
    cron.start()


@app.before_request
def basic_auth():
    if request.path.startswith('/admin') or \
            request.path.startswith('/scheduler'):
        auth = request.authorization
        if not auth or not (auth.username == app.config['ADMIN_USERNAME']
                            and auth.password == app.config['ADMIN_PASS']):
            return Response(
                '<Not public access...>', 401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'})


def load_modules():
    import_module('cli')  # init commands

    app.register_blueprint(main, url_prefix='/<lang>')
    app.register_blueprint(main, url_prefix='')

    for _module in app.config.get('BLUEPRINTS', []):
        bp = import_module(_module).bp
        app.register_blueprint(bp, url_prefix='/<lang>')
        app.register_blueprint(bp, url_prefix='')

