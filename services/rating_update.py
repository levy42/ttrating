"""
Module contains tasks for ranking data update:
    - Update rankings.
    - Translate new strings.
    - Update rankings statistics.
    - Update player statistics.
    - Send email reports.
"""
from time import time
from services import parser, translator, statistics, email_reports, games_chain
from models import db, User, Game, Player, Tournament
from flask_mail import Message
from app import mail
from flask import request
from flask_babel import _
from flask import render_template
from app import app, cache
from itsdangerous import URLSafeSerializer
from views import common


def update_ua(raises=False):
    success = True
    updated_data = parser.parse_ua()
    if not updated_data:
        return
    translate_new_strings(updated_data, raises=raises)
    update_statistics(raises=raises)
    send_ua_monthly_report(raises=raises)
    update_graph_for_games_chain(raises=raises)
    cache.clear()
    return success


def update_world():
    if parser.parse_world_rating():
        send_world_monthly_report()


def subtask(name):
    """Wraps a func in 'try except' block and log result."""

    def wrapper(f):
        def wrapped(*args, **kwargs):
            raises = kwargs.pop('raises', None)
            try:
                start = time()
                app.logger.info(f'Task "{name}" started')
                result = f(*args, **kwargs)
                end = time()
                app.logger.info(f'Task "{name}" finished. Time: {end-start}')
                return result
            except Exception as e:
                app.logger.error(f'Task "{name}" failed! {e}')
                if raises:
                    raise

        return wrapped

    return wrapper


@subtask('Update graph for games chain')
def update_graph_for_games_chain():
    games_chain.update_graphs()


@subtask('Translate new strings')
def translate_new_strings(updated_data):
    translator.add_translations(updated_data['players'], 'ua')
    translator.add_translations(updated_data['cities'], 'ua')
    translator.add_translations(updated_data['tournaments'], 'ua')


@subtask('Update statistics')
def update_statistics():
    update_player_stats()
    statistics.calculate()


def generate_confirmation_token(email):
    serializer = URLSafeSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])


@subtask('Send ua rating reports')
def send_ua_monthly_report():
    report = email_reports.generate_ua_monthly_report()
    users = User.query.filter_by(confirmed=True).all()
    users_divided_by_lang = {lang: [u for u in users if u.language == lang] for
                             lang in app.config['SUPPORTED_LANGUAGES']}

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


@subtask('Send world rating reports')
def send_world_monthly_report():
    report = email_reports.generate_ua_monthly_report()
    users = User.query.filter_by(confirmed=True).all()
    users_divided_by_lang = {lang: [u for u in users if u.language == lang] for
                             lang in app.config['SUPPORTED_LANGUAGES']}

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


@subtask('Update player stats for last month')
def update_player_stats(update_all=False):
    app.logger.info('Updating players info...')
    players = Player.query.filter(Player.rating != 0).all()
    current_rating = common.get_current_rating_list()

    if update_all:
        Player.query.update(tournaments_total=0, game_total=0, game_won=0)
        tournaments = Tournament.query.all()
    else:
        tournaments = Tournament.query.filter_by(
            rating_list_id=current_rating.id).all()

    for tournament in tournaments:
        app.logger.debug(f'Processing tournament {tournament.name}')
        games = Game.query.filter_by(tournament_id=tournament.id).all()
        player_games = {}
        for g in games:
            if not player_games.get(g.player_id):
                player_games[g.player_id] = list()
            player_games[g.player_id].append(g)
        for p in players:
            if not player_games.get(p.id):
                continue
            won = [g for g in player_games[p.id] if g.result]
            tourns = set([g.tournament_id for g in player_games[p.id]])
            p.game_total += len(player_games[p.id])
            p.game_won += len(won)
            p.tournaments_total += len(tourns)
            db.session.add(p)
    db.session.commit()
