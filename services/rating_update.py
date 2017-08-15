import requests

from services import parser
from services import translator
from services import statistics
from services import email_reports
import models
from models import db
from flask_mail import Message
from app import mail


def update_ua():
    updated_data = parser.parse_ua()
    translator.add_translations(updated_data['players'], 'ua')
    translator.add_translations(updated_data['cities'], 'ua')
    translator.add_translations(updated_data['tournaments'], 'ua')

    update_player_info()
    update_statistics()
    send_ua_monthly_report()


def update_world():
    parser.parse_world_rating()


def update_statistics():
    statistics.calculate(statistics.Period.ENTIRE)
    statistics.calculate(statistics.Period.MONTH)
    statistics.calculate(statistics.Period.YEAR)


def send_ua_monthly_report():
    report = email_reports.generate_ua_monthly_report()
    users = models.User.query.all()
    anons = [u for u in users if u.player_id]
    email_reports.create_anon_report_email(report)

    msg = Message(subject=f'',
                      body=render_template('email/subscribe_confirm.html',
                                           token=token), recipients=[email])




def send_world_monthly_report():
    pass


def update_player_info():
    print('progress: ')
    n = 10000
    player_infos = models.PlayerInfo.query.all()

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
            print('Count: %s' % _games.total)
            print('Pages %s' % _games.pages)
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
        print('+')
