import calendar
import datetime
import json
import uuid

import jinja2
from flask import Blueprint
from flask import Flask
from flask import abort
from flask import g
from flask import redirect
from flask import render_template as _render_template
from flask import request
from flask import url_for
from flask_babel import Babel
from flask_babel import _
from flask_cache import Cache
from flask_mobility import Mobility
from jinja2 import filters
from sqlalchemy.orm import eagerload

import config
import models as m
from services.translator import search_translations
from services.translator import translate, load_transations
from services.games import find_chain

app = Flask(config.APP_NAME)
app.config.from_pyfile('config.py')

db = m.db
m.db.init_app(app)

babel = Babel(app)
cache = Cache(app, config=app.config)
main = Blueprint('main', __name__)
mobile = Blueprint('mobile', __name__)
Mobility(app)


def render_template(name, **kwargs):
    if request.blueprint == 'mobile':
        return _render_template('mobile/' + name, **kwargs)
    else:
        return _render_template(name, **kwargs)


def route(rule, **options):
    def decorator(f):
        endpoint = options.pop("endpoint", f.__name__)
        main.add_url_rule(rule, endpoint, f, **options)
        mobile.add_url_rule(rule, endpoint, f, **options)
        return f

    return decorator


main.route = route


# localization

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
    return calendar.month_abbr[value]


@jinja2.contextfilter
@app.template_filter(name='color')
def number_color(context, value):
    if value > 0:
        value = '<p style="color:green">+%s</p>' % value
    elif value < 0:
        value = '<p style="color:red">%s</p>' % value
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


# utils
@cache.cached(key_prefix='get_rating_lists')
def get_rating_lists():
    return m.RatingList.query.order_by(m.RatingList.year.desc(),
                                       m.RatingList.month.desc()).all()


@cache.cached(key_prefix='get_years')
def get_years():
    return sorted(list(set([x.year for x in get_rating_lists()])))


# routes

@main.route('/rating/<category>/')
@main.route('/rating/')
@cache.cached(key_prefix=lambda: request.url)
def rating(category='MEN'):
    rating_lists = get_rating_lists()
    year = request.args.get('year', rating_lists[0].year, type=int)
    month = request.args.get('month', rating_lists[0].month, type=int)
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 25, type=int)
    sort_by = request.args.get('sort', 'position')
    city = request.args.get('city', 'all cities')
    if request.args.get('desc', False, type=bool):
        sort_by += ' desc'

    years = get_years()
    rating = m.Rating.query.join(m.Player).options(
            eagerload('player')).filter(
            m.Rating.year == year,
            m.Rating.month == month,
            m.Player.category == category,
            m.Rating.rating >= 10).order_by('rating.' + sort_by)
    if city != 'all cities':
        rating = rating.filter(m.Player.city == city)
    rating = rating.paginate(per_page=limit, page=page)
    date = '%s %s' % (_(calendar.month_abbr[month]), year)

    return render_template('rating.html', rating=rating,
                           categories=m.Category.VALUES, category=category,
                           date=date, year=year, month=month, years=years,
                           city=city, cities=cities())


@main.route('/world-rating/<category>/')
@main.route('/world-rating/')
@cache.cached(key_prefix=lambda: request.url)
def world_rating(year=None, month=None, category='MEN'):
    rating_lists = m.WorldRatingList.query.order_by(
            m.WorldRatingList.year.desc(),
            m.WorldRatingList.month.desc()).all()

    year = request.args.get('year', rating_lists[0].year, type=int)
    month = request.args.get('month', rating_lists[0].month, type=int)
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 25, type=int)
    sort_by = request.args.get('sort', 'rating')
    if request.args.get('desc', True, type=bool):
        sort_by += ' desc'

    if not year or not month:
        year = rating_lists[0].year
        month = rating_lists[0].month

    years = sorted(list(set([l.year for l in rating_lists])), reverse=True)

    rating = m.WorldRating.query.join(m.WorldPlayer).options(
            eagerload('player')).filter(
            m.WorldRating.year == year,
            m.WorldRating.month == month,
            m.WorldPlayer.category == category,
            m.WorldRating.rating > 0
    ).order_by('world_rating.' + sort_by).paginate(page=page, per_page=limit)

    return render_template('world-rating.html', rating=rating,
                           categories=m.Category.VALUES, category=category,
                           year=year, month=month, years=years)


@main.route("/world-player/<id>/")
@cache.cached()
def world_player(id):
    player = m.WorldPlayer.query.get(id)
    if not player:
        abort(404)
    ratings = m.WorldRating.query.filter_by(player_id=id).order_by(
            m.WorldRating.year, m.WorldRating.month).all()[-36:]  # tmp limit
    ratings_values = [r.rating for r in ratings]
    dates = ["%s %s" % (_(calendar.month_abbr[r.month]), r.year) for r in
             ratings]
    return render_template('world-player.html', player=player,
                           ratings=ratings_values, dates=dates)


@main.route("/player/<id>/")
@cache.cached()
def player(id):
    player = m.Player.query.get(id)
    if not player:
        abort(404)
    ratings = m.Rating.query.filter_by(player_id=id).order_by(
            m.Rating.year, m.Rating.month).all()
    ratings_values = [r.rating for r in ratings]
    weight_values = [r.weight for r in ratings]
    position_values = [r.position for r in ratings]
    dates = ["%s %s" % (_(calendar.month_abbr[r.month]), r.year) for r in
             ratings]
    return render_template('player.html', player=player,
                           ratings=ratings_values, weights=weight_values,
                           positions=position_values, dates=dates)


@main.route("/player-tournament/<int:player_id>/<int:tournament_id>/")
@cache.cached()
def player_tournament(player_id, tournament_id):
    player_tournament = m.PlayerTournament.query.filter_by(
            player_id=player_id, tournament_id=tournament_id).first()
    return render_template('player_tournament.html',
                           player_tournament=player_tournament)


@main.route("/tournament/<int:id>/")
@cache.cached()
def tournament(id):
    tournament = m.Tournament.query.get(id)
    return render_template('tournament.html', tournament=tournament)


@main.route("/tournaments/<int:year>/<int:month>")
@main.route("/tournaments")
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


@main.route("/win-chain")
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


@main.route("/games/")
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


@main.route("/statistics/")
@cache.cached(key_prefix=lambda: request.url)
def statistics():
    page = request.args.get('page', 1, type=int)
    issues = m.TopicIssue.query.join(m.Topic).options(
            eagerload('topic')).order_by(m.TopicIssue.new).order_by(
            m.Topic.index).paginate(per_page=7, page=page)
    return render_template('statistics.html', issues=issues)


# live tournament

@main.route("/live-tournament/home/")
def live_tournament_home():
    return render_template('live_tournament_home.html')


@main.route("/live-tournament/<key>")
def live_tournament(key):
    tournament = m.LiveTournament.query.filter_by(key=key).first()
    if not tournament:
        return abort(404)
    if tournament.status == 'created':
        return redirect(url_for('.live_tournament_add_players', key=key))
    return render_template('live_tournament_home.html')


@main.route("/live-tournament/create/")
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


@main.route("/live-tournament/<key>/")
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


@main.route("/live-tournament/<key>/remove-player/<int:number>")
def live_tournament_remove_player(key, number):
    tournament = m.LiveTournament.query.filter_by(key=key).first()
    if not tournament:
        return abort(404)
    players = [p for p in tournament.players if p['number'] != number]
    tournament._players = json.dumps(players)
    m.db.session.add(tournament)
    m.db.session.commit()
    return redirect(
            url_for('.live_tournament_add_players', key=tournament.key))


@main.route("/live-tournament/<key>/add-players", methods=['GET', 'POST'])
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


@main.route('/sparring')
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


@cache.cached(key_prefix="sparring_cities")
def sparring_cities():
    return [x[0] for x in db.session.query(m.Sparring.city).distinct()]


@main.route('/sparring/add', methods=['GET', 'POST'])
def add_sparring():
    if request.method == 'POST':
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
        return redirect(url_for('.sparring'))
    else:
        return render_template('sparring_add.html', cities=cities())


# api

@main.route("/player-search/<name>")
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


@main.route("/world-player-search/<name>")
def world_player_search(name):
    matches = m.WorldPlayer.query.filter(m.WorldPlayer.name.like(
            '%' + name.title() + '%')).limit(10).all()
    return json.dumps([{'name': p.name,
                        'rating': p.rating or '0.0',
                        'url': url_for('.world_player', id=p.id),
                        'country': translate_name(countries().get(
                                p.country_code).name)} for p in matches])


# cached

@cache.cached(key_prefix=lambda: g.lang + 'countries')
def countries():
    return {c.code: c for c in m.Country.query.all()}


@cache.cached(key_prefix=lambda: g.lang + 'cities')
def cities():
    return {c.name: {'id': c.name, 'weight': c.weight,
                     'title': translate_name(c.name)}
            for c in m.City.query.all()}


# base routes
@main.route('/about')
def about():
    return render_template('about.html')


@app.route('/')
@main.route('/')
def home():
    if request.args.get('version'):
        return redirect(url_for('.statistics'))
    else:
        if request.MOBILE:
            return redirect(url_for('mobile.statistics'))
        else:
            return redirect(url_for('main.statistics'))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.register_blueprint(main, url_prefix='/<lang>')
    app.register_blueprint(mobile, url_prefix='/<lang>/m')
    app.run(port=10000, host='0.0.0.0')
