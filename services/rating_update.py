from services import parser
from services import translator
from services import statistics
from services import email_reports
import models
from models import db
from flask_mail import Message
from app import mail
from flask import request
from flask_babel import _
from flask import render_template
from app import app
from app import cache
from itsdangerous import URLSafeSerializer
import config
from views import common

LOG = app.logger


def update_ua():
    updated_data = parser.parse_ua()
    if not updated_data:
        return
    translate_new_strings(updated_data)
    statistics.calculate(statistics)
    send_ua_monthly_report()
    cache.clear()


def update_world():
    if parser.parse_world_rating():
        send_world_monthly_report()


def atomic_subtask(name):
    def wrapper(f):
        def wrapped(*args, **kwargs):
            try:
                LOG.info(f'{name} started')
                return f(*args, **kwargs)
            except Exception as e:
                LOG.error(f'{name} failed! {e}')

        return wrapped

    return wrapper


@atomic_subtask('Translate new strings')
def translate_new_strings(updated_data):
    translator.add_translations(updated_data['players'], 'ua')
    translator.add_translations(updated_data['cities'], 'ua')
    translator.add_translations(updated_data['tournaments'], 'ua')


@atomic_subtask('Update statistics')
def update_statistics():
    update_player_info()
    statistics.calculate(statistics)


def generate_confirmation_token(email):
    serializer = URLSafeSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])


@atomic_subtask('Send ua rating reports')
def send_ua_monthly_report():
    report = email_reports.generate_ua_monthly_report()
    users = models.User.query.all()
    users_divided_by_lang = {lang: [u for u in users if u.language == lang] for
                             lang in config.SUPPORTED_LANGUAGES}

    for lang, users in users_divided_by_lang.items():
        with app.test_request_context(f'/{lang}/'):
            request.lang = lang
            with mail.connect() as conn:
                for user in users:
                    token = generate_confirmation_token(user.email)
                    msg = Message(subject=_("Hoвий рейтинг"),
                                  html=render_template('email/new_rating.html',
                                                       user=user,
                                                       token=token,
                                                       report=report),
                                  recipients=[user.email])
                    conn.send(msg)


@atomic_subtask('Send world rating reports')
def send_world_monthly_report():
    report = email_reports.generate_ua_monthly_report()
    users = models.User.query.all()
    users_divided_by_lang = {lang: [u for u in users if u.language == lang] for
                             lang in config.SUPPORTED_LANGUAGES}

    for lang, users in users_divided_by_lang.items():
        with app.test_request_context(f'/{lang}/'):
            request.lang = lang
            with mail.connect() as conn:
                for user in users:
                    token = generate_confirmation_token(user.email)
                    msg = Message(subject=_("Hoвий світовий рейтинг"),
                                  html=render_template('email/new_rating.html',
                                                       user=user,
                                                       token=token,
                                                       report=report),
                                  recipients=[user.email])
                    conn.send(msg)


def update_player_info():
    LOG.info('Updating players info')
    LOG.info('progress: ')
    n = 10000
    player_infos = models.PlayerInfo.query.all()
    last_rating_list = common.get_current_rating_list()
    month = last_rating_list.month
    year = last_rating_list.year
    ratings = models.Rating.query.filter(year=year, month=month).all
    players = models.PlayerInfo.query.all()
    players_by_id = {p.id: p for p in players}

    for r in ratings:
        player = players_by_id[r.player_id]
        player.rating = r.rating
        db.session.add(player)
    db.session.commit()

    for p in player_infos:
        p.game_total = 0
        p.game_won = 0
        p.tournaments_total = 0
        models.db.session.add(p)
    models.db.session.commit()

    page = 0
    pages = 1
    while page < pages:
        page += 1
        _games = models.Game.query.paginate(page=page, per_page=n)
        if page == 1:
            LOG.info('Count: %s' % _games.total)
            LOG.info('Pages %s' % _games.pages)
            pages = _games.pages
        games = _games.items
        player_games = {}
        for g in games:
            if not player_games.get(g.player_id):
                player_games[g.player_id] = list()
            player_games[g.player_id].append(g)
        for i, p in enumerate(player_infos):
            if not player_games.get(p.id):
                continue
            won = [g for g in player_games[p.id] if g.result]
            tourns = set([g.tournament_id for g in player_games[p.id]])
            p.game_total += len(player_games[p.id])
            p.game_won += len(won)
            p.tournaments_total += len(tourns)
            db.session.add(p)
        db.session.commit()
        LOG.info(f'{page}/{pages}')
