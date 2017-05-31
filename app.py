import datetime
import json
import uuid

from flask import Flask
from flask import abort
from flask import g
from flask import render_template
from flask import request
from flask import redirect
from flask import jsonify
from flask import url_for
from flask import Blueprint
from flask_cache import Cache
from sqlalchemy.orm import eagerload

import config
import models as m
from models import db
from services.translator import search_translations
from services.translator import translate, load_transations
from services.games import find_chain

app = Flask(config.APP_NAME, static_folder='frontend')
app.config.from_pyfile('config.py')
db.init_app(app)

cache = Cache(app, config=app.config)
api = Blueprint('api', __name__)


def translate_name(text):
    return translate(text, g.get('lang', app.config['DEFAULT_LOCALE']))


@api.before_request
def set_locale():
    g.locale = request.args.get('lang', config.DEFAULT_LOCALE)


@app.before_request
def frontend_proxy():
    if request.blueprint != 'api':
        return redirect('http://localhost:3000' + request.full_path)


@app.before_first_request
def on_startup():
    load_transations()


def get_rating_lists():
    return m.RatingList.query.order_by(m.RatingList.year.desc(),
                                       m.RatingList.month.desc()).all()


# routes
@api.route('/rating/')
@cache.cached(key_prefix='get_rating_lists')
def rating_lists():
    return jsonify([{'year': l.year, 'month': l.month, 'id': l.id} for l in
                    get_rating_lists()])


@api.route('/rating/<category>/<year>/<month>')
@cache.cached(key_prefix=lambda: request.url)
def rating(category, year, month):
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 25, type=int)
    sort_by = request.args.get('sort', 'position')
    city = request.args.get('city', 'all cities')
    min_rating = request.args.get('min_rating', 0)
    max_rating = request.args.get('max_rating', 0)
    min_year = request.args.get('min_year', 0)
    max_year = request.args.get('max_year', 0)
    if request.args.get('desc', False, type=bool):
        sort_by += ' desc'

    rating = m.Rating.query.join(m.Player).options(
            eagerload('player')).filter(
            m.Rating.year == year,
            m.Rating.month == month,
            m.Player.category == category,
            m.Rating.rating >= 10).order_by('rating.' + sort_by)
    if city != 'all cities':
        rating = rating.filter(m.Player.city == city)
    if min_rating:
        rating = rating.filter(m.Rating.rating >= min_rating)
    if max_rating:
        rating = rating.filter(m.Rating.rating <= max_rating)
    if min_year:
        rating = rating.filter(m.Rating.rating >= min_rating)
    if max_year:
        rating = rating.filter(m.Rating.rating <= max_rating)
    rating = rating.paginate(per_page=limit, page=page)
    return jsonify({'items':
                        [{'position': r.position,
                          'name': r.player.name if not g.get(
                                  'locale') else translate_name(
                                  r.player.name),
                          'rating': r.rating,
                          'rating_fine': r.rating_fine,
                          'weight': r.weight,
                          'max': r.player.max,
                          'year': r.player.year} for r in rating.items],
                    'page': page, 'pages': rating.pages,
                    'total': rating.total})


def get_world_rating_lists():
    return m.WorldRatingList.query.order_by(
            m.WorldRatingList.year.desc(),
            m.WorldRatingList.month.desc()).all()


@api.route('/world-rating/')
def world_rating_lists():
    return jsonify([{'year': l.year, 'month': l.month, 'id': l.id} for l in
                    get_world_rating_lists()])


@api.route('/world-rating/<category>/<year>/<month>')
@cache.cached(key_prefix=lambda: request.url)
def world_rating(year, month, category='MEN'):
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 25, type=int)
    sort_by = request.args.get('sort', 'rating')
    if request.args.get('desc', True, type=bool):
        sort_by += ' desc'

    rating = m.WorldRating.query.join(m.WorldPlayer).options(
            eagerload('player')).filter(
            m.WorldRating.year == year,
            m.WorldRating.month == month,
            m.WorldPlayer.category == category,
            m.WorldRating.rating > 0
    ).order_by('world_rating.' + sort_by).paginate(page=page, per_page=limit)

    return jsonify({'items': [{'position': r.position, 'rating': r.rating,
                               'name': r.player.name} for r in rating.items],
                    'total': rating.total,
                    'pages': rating.pages,
                    'page': rating.page})


@api.route("/world-player/<id>/")
@cache.cached()
def world_player(id):
    player = m.WorldPlayer.query.get(id)
    if not player:
        abort(404)
    ratings = m.WorldRating.query.filter_by(player_id=id).order_by(
            m.WorldRating.year, m.WorldRating.month).all()
    ratings = [(r.rating, r.month, r.year) for r in ratings]
    return jsonify({'name': player.name,
                    'position': player.position,
                    'country': player.city,
                    'category': player.category,
                    'ratings': ratings})


@api.route("/player/<id>/")
@cache.cached()
def player(id):
    player = m.Player.query.get(id)
    if not player:
        abort(404)
    ratings = m.Rating.query.filter_by(player_id=id).order_by(
            m.Rating.year, m.Rating.month).all()
    ratings = [(r.rating, r.month, r.year) for r in ratings]
    tournaments = [{'id': t.id,
                    'name': t.name,
                    'tournament_id': t.tournament_id,
                    'start_rating': t.start_rating,
                    'final_rating': t.final_rating,
                    'start_weight': t.start_weight,
                    'final_weight': t.final_weight}
                   for t in player.tournaments]
    return jsonify({'name': player.name,
                    'position': player.position,
                    'year': player.year,
                    'weight': player.weight,
                    'max': player.max,
                    'city': player.city,
                    'city2': player.city2,
                    'category': player.category,
                    'tournament_total': player.info.tournament_total,
                    'game_total': player.info.game_total,
                    'game_won': player.info.game_won,
                    'photo_url': player.info.photo_url,
                    'about': player.info.about,
                    'ratings': ratings,
                    'tournaments': tournaments})


@api.route("/player-tournament/<int:player_id>/<int:tournament_id>/")
@cache.cached()
def player_tournament(player_id, tournament_id):
    player_tournament = m.PlayerTournament.query.filter_by(
            player_id=player_id, tournament_id=tournament_id).first()
    return jsonify({''})


@api.route("/tournament/<int:id>/")
@cache.cached()
def tournament(id):
    tournament = m.Tournament.query.get(id)
    return render_template('tournament.html', tournament=tournament)


@api.route("/tournaments/<int:year>/<int:month>")
@api.route("/tournaments")
@cache.cached()
def tournaments(year=None, month=None):
    years = get_years()
    if not year:
        year = get_rating_lists()[0].year
    if not month:
        month = get_rating_lists()[0].month
    rating_list = m.RatingList.query.filter_by(year=year, month=month).first()
    if not rating_list:
        tournaments = []
    else:
        tournaments = m.Tournament.query.filter_by(
                rating_list_id=rating_list.id).order_by(
                m.Tournament.start_date.desc()).all()
    return render_template('tournaments.html', tournaments=tournaments,
                           year=year, month=month, years=years)


@api.route("/win-chain")
def win_chain():
    player1_id = request.args.get('player1_id', type=int)
    player2_id = request.args.get('player2_id', type=int)
    count_all = request.args.get('count_all', type=bool, default=False)

    chain = []
    player1 = None
    player2 = None
    if player1_id and player2_id:
        player1 = m.Player.query.get(player1_id)
        player2 = m.Player.query.get(player2_id)
        chain = find_chain(player1_id, player2_id, all=count_all)
    return render_template('win_chain.html', player1=player1, player2=player2,
                           chain=chain, count_all=count_all)


@api.route("/games/")
def game_search():
    player1 = request.args.get('player1', '')
    player2 = request.args.get('player2', '')
    player1_id = request.args.get('player1_id')
    player2_id = request.args.get('player2_id')
    page = request.args.get('page', 1, type=int)
    filters = []
    if player1_id:
        filters.append(m.Game.player_id == player1_id)
    elif player1:
        filters.append(m.Game.player_name.like("%" + player1.title() + "%"))
    if player2_id:
        filters.append(m.Game.opponent_id == player2_id)
    elif player2:
        filters.append(m.Game.opponent_name.like("%" + player2.title() + "%"))
    games = None
    if filters:
        games = m.Game.query.filter(*filters).order_by('id').paginate(
                page=page, per_page=25)
    return render_template('games_search.html', games=games, player1=player1,
                           player2=player2, player1_id=player1_id,
                           player2_id=player2_id)


@api.route("/statistics/")
@cache.cached(key_prefix=lambda: request.url)
def statistics():
    page = request.args.get('page', 1, type=int)
    issues = m.TopicIssue.query.join(m.Topic).options(
            eagerload('topic')).order_by(m.TopicIssue.new).order_by(
            m.Topic.index).paginate(per_page=7, page=page)
    return jsonify([{'name': i.topic.name,
                     'type': i.topic.type,
                     'properties': i.topic.properties,
                     'data': i.data,
                     } for i in issues.items])


# live tournament

@api.route("/live-tournament/home/")
def live_tournament_home():
    return render_template('live_tournament_home.html')


@api.route("/live-tournament/<key>")
def live_tournament(key):
    tournament = m.LiveTournament.query.filter_by(key=key).first()
    if not tournament:
        return abort(404)
    if tournament.status == 'created':
        return redirect(url_for('live_tournament_add_players', key=key))
    return render_template('live_tournament_home.html')


@api.route("/live-tournament/create/")
def live_tournament_create():
    name = request.args.get('name')
    if not name:
        return render_template('live_tournament_create.html',
                               date=datetime.datetime.today())
    else:
        tournament = m.LiveTournament()
        tournament.key = str(uuid.uuid4())
        tournament.name = name
        tournament.is_rating = request.args.get('is_rating', type=bool,
                                                default=False)
        tournament.coefficient = request.args.get('coef', type=float)
        tournament.judge = request.args.get('judge')
        tournament._games = '[]'
        tournament._players = '[]'
        m.db.session.add(tournament)
        m.db.session.commit()
        return render_template('live_tournament_get_key.html',
                               key=tournament.key)


@api.route("/live-tournament/<key>/")
def live_tournament_add_players(key):
    tournament = m.LiveTournament.query.filter_by(key=key).first()
    if not tournament:
        return abort(404)
    if tournament.status == 'created':
        return render_template('live_tournament_add_players.html',
                               tournament=tournament,
                               cities=list(cities().values()))
    if tournament.status == 'added_players':
        return render_template('live_tournament_add_players.html',
                               tournament=tournament,
                               cities=list(cities().values()))


@api.route("/live-tournament/<key>/remove-player/<int:number>")
def live_tournament_remove_player(key, number):
    tournament = m.LiveTournament.query.filter_by(key=key).first()
    if not tournament:
        return abort(404)
    players = [p for p in tournament.players if p['number'] != number]
    tournament._players = json.dumps(players)
    m.db.session.add(tournament)
    m.db.session.commit()
    return redirect(url_for('live_tournament_add_players', key=tournament.key))


@api.route("/live-tournament/<key>/add-players", methods=['GET', 'POST'])
def live_tournament_add_player(key):
    error = False
    tournament = m.LiveTournament.query.filter_by(key=key).first()
    if not tournament:
        return abort(404)
    if request.method == 'GET':
        return render_template('live_tournament_add_players.html',
                               tournament=tournament,
                               cities=list(cities().values()))

    player_id = request.form.get('player_id', type=int)
    players = tournament.players
    if player_id:
        if player_id in [p['player_id'] for p in players]:
            error = True
        else:
            real_player = m.Player.query.get(player_id)
            player = {'number': len(players), 'name': real_player.name,
                      'rating': real_player.rating or 0,
                      'city': real_player.city, 'year': real_player.year,
                      'player_id': player_id}
    else:
        name = request.form.get('name')
        if name in [p['name'] for p in players]:
            error = True
        city = request.form.get('city')
        year = request.form.get('year')
        player = {'number': len(players), 'name': name, 'rating': 0,
                  'city': city, 'year': year}
    if not error:
        players.append(player)
        tournament._players = json.dumps(players)
        m.db.session.add(tournament)
        m.db.session.commit()
    return render_template('live_tournament_add_players.html', error=error,
                           tournament=tournament,
                           cities=list(cities().values()))


@api.route('/sparring')
def sparring():
    page = request.args.get('page', 1, type=int)
    city = request.args.get('city')
    sort_by = request.args.get('sort_by', 'rating')
    if sort_by == 'rating':
        query = m.Sparring.query.join(m.Player).order_by(
                m.Player.rating.desc())
    elif sort_by == 'price':
        query = m.Sparring.query.order_by(m.Sparring.price.desc())
    else:
        query = m.Sparring.query
    if city and city != '-':
        query = query.filter_by(city=city)
    sparrings = query.paginate(page=page, per_page=10)
    return render_template('sparring.html', sparrings=sparrings,
                           cities=sparring_cities())


@api.route('/sparring/cities')
@cache.cached(key_prefix="sparring_cities")
def sparring_cities():
    return [x[0] for x in db.session.query(m.Sparring.city).distinct()]


@api.route('/sparring/add', methods=['POST'])
def add_sparring():
    name = request.form.get('name')
    player_id = request.form.get('player_id')
    city = request.form.get('city')
    price = request.form.get('price')
    location = request.form.get('location')
    description = request.form.get('description')
    sparring = m.Sparring()
    sparring.name = name
    sparring.city = city
    sparring.location = location
    sparring.description = description
    sparring.player_id = player_id
    sparring.price = price
    sparring.datetime = datetime.datetime.now()
    db.session.add(sparring)
    db.session.commit()
    return 'OK'


# api

@api.route("/player-search/<name>")
def player_search(name):
    if g.lang == 'ru':  # default player name language
        matches = m.Player.query.filter(
                m.Player.name.like('%' + name.title() + '%')).limit(10).all()
    else:
        translations = search_translations(name.title(), g.lang)
        matches = m.db.session.query(m.Player).filter(
                m.Player.name.in_(translations)).limit(10).all()
    return json.dumps([{'name': translate_name(p.name),
                        'rating': p.rating or '0.0',
                        'url': url_for('.player', id=p.id),
                        'city': translate_name(p.city),
                        'year': p.year,
                        'id': p.id,
                        'image': p.info.photo_url}
                       for p in matches])


@api.route("/world-player-search/<name>")
def world_player_search(name):
    matches = m.WorldPlayer.query.filter(m.WorldPlayer.name.like(
            '%' + name.title() + '%')).limit(10).all()
    return json.dumps([{'name': p.name,
                        'rating': p.rating or '0.0',
                        'url': url_for('.world_player', id=p.id),
                        'country': translate_name(countries().get(
                                p.country_code).name)} for p in matches])


@api.route('/countries')
@cache.cached(key_prefix=lambda: g.lang + 'countries')
def countries():
    return {c.code: c for c in m.Country.query.all()}


@api.route('/cities')
@cache.cached(key_prefix=lambda: g.lang + 'cities')
def cities():
    return {c.name: {'id': c.name, 'weight': c.weight,
                     'title': translate_name(c.name)}
            for c in m.City.query.all()}


if __name__ == '__main__':
    app.register_blueprint(api, url_prefix='/api')
    app.run(port=10000, host='0.0.0.0')
