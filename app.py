import logging
from logging.handlers import SMTPHandler
from logging.handlers import RotatingFileHandler

import jinja2
from flask import (Flask, g, redirect, render_template, request, url_for)
from flask_babel import (Babel, _)
from flask_cache import Cache
from flask_mobility import Mobility
from jinja2 import filters
from flask_mail import Mail

import config
import models as m
from services.translator import translate, load_transations

app = Flask(config.APP_NAME)
app.config.from_pyfile('config.py')

db = m.db
m.db.init_app(app)

babel = Babel(app)
Mobility(app)
cache = Cache(app, config=app.config)
mail = Mail(app)

# logging
handler = RotatingFileHandler(f'{config.APP_NAME}.log', maxBytes=10000,
                              backupCount=1)
app.logger.addHandler(handler)
handler.setLevel(logging.DEBUG)
mail_handler = SMTPHandler(mailhost=(config.MAIL_SERVER, config.MAIL_PORT),
                           fromaddr=config.MAIL_DEFAULT_SENDER,
                           secure=config.MAIL_USE_SSL,
                           credentials=(
                               config.MAIL_USERNAME, config.MAIL_PASSWORD),
                           toaddrs=[config.ADMINS],
                           subject='YourApplication Failed')
mail_handler.setLevel(logging.ERROR)
app.logger.addHandler(mail_handler)

# localization
month_abbr = ['', 'січ', 'лют', 'бер', 'кві', 'тра', 'чер', 'лип', 'сер',
              'вер', 'жов', 'лис', 'гру']


@babel.localeselector
def get_locale():
    return g.get('lang')


@app.url_defaults
def set_language_code(endpoint, values):
    if 'lang' in values or not g.get('lang', None):
        return
    if app.url_map.is_endpoint_expecting(endpoint, 'lang'):
        values['lang'] = g.lang


@app.url_value_preprocessor
def get_lang_code(endpoint, values):
    if values is not None:
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


# custom context

def translate_name(text):
    return translate(text, g.get('lang', app.config['BABEL_DEFAULT_LOCALE']))


def translate_array(arr):
    return [translate_name(_(x)) for x in arr]


def url_for_other_page(page):
    args = request.view_args.copy()
    args.update(request.args)
    args['page'] = page
    return url_for(request.endpoint, **args)


def iter_pages(pagination, left_edge=2, left_current=2,
               right_current=5, right_edge=2):
    last = 0
    for num in range(1, pagination.pages + 1):
        if num <= left_edge or (
                                pagination.page - left_current - 1 < num < pagination.page + right_current) or num > pagination.pages - right_edge:
            if last + 1 != num:
                yield None
            yield num
            last = num


@app.context_processor
def dynamic_translate_processor():
    return dict(name=translate_name,
                translate_arr=translate_array,
                url_for_other_page=url_for_other_page,
                iter_pages=iter_pages)


@app.context_processor
def form_parameters():
    return {k: request.args.get(k) for k in request.args}


@app.before_first_request
def on_startup():
    load_transations()


# base routes
@app.route('/<lang>/about/')
def about(lang=None):
    return render_template('about.html')


@app.route('/change-version')
def change_version():
    is_mobile = request.args['mobile']
    request.MOBILE = is_mobile == 'on'
    page = request.args['page']
    redirect_to = redirect(page)
    response = app.make_response(redirect_to)
    response.set_cookie('mobile', value=is_mobile)
    return response


@app.route('/')
def home():
    return redirect(url_for(f'{config.HOME_PAGE}'))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    app.logger.error(f'500 error: {e}')
    return render_template('500.html'), 500


if __name__ == '__main__':
    # register views
    from views import (rating, world_rating, subscribers)
    from tasks import cron

    app.register_blueprint(rating.bp, url_prefix='/<lang>')
    app.register_blueprint(world_rating.bp, url_prefix='/<lang>')
    app.register_blueprint(subscribers.bp, url_prefix='/<lang>')

    # cron.start()
    app.run(port=10000, host='0.0.0.0')
