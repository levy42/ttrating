"""
Module contains tasks for ranking data update:
    - Update rankings.
    - Translate new strings.
    - Update rankings statistics.
    - Update player statistics.
    - Send email reports.
"""
from services import parser, translator, statistics, email_reports
from models import db, User, Game, Player, Rating, Tournament
from flask_mail import Message
from app import mail
from flask import request
from flask_babel import _
from flask import render_template
from app import app, cache
from itsdangerous import URLSafeSerializer
from views import common


def update_ua():
    updated_data = parser.parse_ua()
    if not updated_data:
        return
    translate_new_strings(updated_data)
    update_statistics()
    send_ua_monthly_report()
    cache.clear()


def update_world():
    if parser.parse_world_rating():
        send_world_monthly_report()


def subtask(name):
    """Wraps a func in try catch block and log result."""
    def wrapper(f):
        def wrapped(*args, **kwargs):
            try:
                app.logger.info(f'{name} started')
                return f(*args, **kwargs)
            except Exception as e:
                app.logger.error(f'{name} failed! {e}')

        return wrapped

    return wrapper


@subtask('Translate new strings')
def translate_new_strings(updated_data):
    translator.add_translations(updated_data['players'], 'ua')
    translator.add_translations(updated_data['cities'], 'ua')
    translator.add_translations(updated_data['tournaments'], 'ua')


@subtask('Update statistics')
def update_statistics():
    update_player_stats()
    statistics.calculate(statistics)


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


@subtask('Recalculate player stats')
def calculate_player_stats():
    app.logger.info('Updating players info')
    app.logger.info('progress: ')
    n = 10000
    players = Player.query.all()
    last_rating_list = common.get_current_rating_list()
    month = last_rating_list.month
    year = last_rating_list.year
    ratings = Rating.query.filter_by(year=year, month=month).all()
    players_by_id = {p.id: p for p in players}

    for r in ratings:
        player = players_by_id[r.player_id]
        player.rating = r.rating
        db.session.add(player)
    db.session.commit()

    for p in players:
        p.game_total = 0
        p.game_won = 0
        p.tournaments_total = 0
        db.session.add(p)
    db.session.commit()

    page = 0
    pages = 1
    while page < pages:
        page += 1
        _games = Game.query.paginate(page=page, per_page=n)
        if page == 1:
            app.logger.info('Count: %s' % _games.total)
            app.logger.info('Pages %s' % _games.pages)
            pages = _games.pages
        games = _games.items
        player_games = {}
        for g in games:
            if not player_games.get(g.player_id):
                player_games[g.player_id] = list()
            player_games[g.player_id].append(g)
        for i, p in enumerate(players):
            if not player_games.get(p.id):
                continue
            won = [g for g in player_games[p.id] if g.result]
            tourns = set([g.tournament_id for g in player_games[p.id]])
            p.game_total += len(player_games[p.id])
            p.game_won += len(won)
            p.tournaments_total += len(tourns)
            db.session.add(p)
        db.session.commit()
        app.logger.info(f'{page}/{pages}')


@subtask('Update player stats for last month')
def update_player_stats():
    app.logger.info('Updating players info...')
    players = Player.query.filter(Player.rating != 0).all()
    current_rating = common.get_current_rating_list()
    tournaments = Tournament.query.filter_by(
        rating_list_id=current_rating.id).all

    for tournament in tournaments:
        games = Game.query.filter_by(tournamet_id=tournament.id).all()
        player_games = {}
        for g in games:
            if not player_games.get(g.player_id):
                player_games[g.player_id] = list()
            player_games[g.player_id].append(g)
        for i, p in enumerate(players):
            if not player_games.get(p.id):
                continue
            won = [g for g in player_games[p.id] if g.result]
            tourns = set([g.tournament_id for g in player_games[p.id]])
            p.game_total += len(player_games[p.id])
            p.game_won += len(won)
            p.tournaments_total += len(tourns)
            db.session.add(p)
        db.session.commit()
