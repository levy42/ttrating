from services import parser
from services import translator
import models
from models import db


def every_day():
    updated_date = parser.parse_ua()
    parser.parse_world_rating()

    translator.add_translations(updated_date['players'], 'ua')
    translator.add_translations(updated_date['cities'], 'ua')
    translator.add_translations(updated_date['tournaments'], 'ua')

    update_player_info()


def update_ratings():
    models.db.engine.execute("")


def update_player_info():
    print('progress: ')
    n = 10
    games = models.Game.query.all()
    page = 0
    pages = 1
    while page < pages:
        page += 1
        player_infos = models.PlayerInfo.query.paginate(page=page, per_page=n)
        print('got')
        if page == 1:
            print('Count: %s' % player_infos.total)
            print('Pages %s' % player_infos.pages)
            pages = player_infos.pages
        player_games = {}
        print('got2')
        for g in games:
            if not player_games.get(g.player_id):
                player_games[g.player_id] = list()
            player_games[g.player_id].append(g)
        print('got3')
        for i, p in enumerate(player_infos.items):
            print(i)
            if not player_games.get(p.id):
                continue
            won = [g for g in player_games[p.id] if g.result]
            tourns = set([g.tournament_id for g in player_games[p.id]])
            p.game_total = len(player_games[p.id])
            p.game_won = len(won)
            p.tournaments_total = len(tourns)
            db.session.add(p)
        print('+')
    db.session.commit()
