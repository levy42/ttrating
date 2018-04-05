import json
from flask import abort, g, request, url_for, Blueprint
from sqlalchemy.orm import eagerload
from services.games_chain import find_chain
import models as m
from app import cache, render_template, month_abbr
from services.translator import search_translations
from views.common import cities, get_rating_lists, get_years, translate_name
from flask_mobility.decorators import mobile_template

bp = Blueprint('rating', __name__)


@bp.route('/rating/<category>')
@bp.route('/rating')
@mobile_template('{mobile/}rating/rating.html')
@cache.cached(key_prefix=lambda: request.url + str(request.MOBILE))
def rating(template, category='MEN'):
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
        m.Rating.rating >= 10).order_by(m.Rating.position)
    if city != 'all cities':
        rating = rating.filter(m.Player.city == city)
    rating = rating.paginate(per_page=limit, page=page)
    date = f'{month_abbr[month]} {year}'

    return render_template(template, rating=rating,
                           categories=m.Category.VALUES, category=category,
                           date=date, year=year, month=month, years=years,
                           city=city, cities=cities())


@bp.route('/player/<id>')
@mobile_template('{mobile/}rating/player.html')
@cache.cached(key_prefix=lambda: request.url + str(request.MOBILE))
def player(template, id):
    player = m.Player.query.get(id)
    if not player:
        abort(404)
    ratings = m.Rating.query.filter_by(player_id=id).order_by(
        m.Rating.year, m.Rating.month).all()
    ratings_values = [r.rating for r in ratings]
    weight_values = [r.weight for r in ratings]
    position_values = [r.position for r in ratings]
    dates = [f'{month_abbr[r.month]} {r.year}' for r in
             ratings]
    return render_template(template, player=player,
                           ratings=ratings_values, weights=weight_values,
                           positions=position_values, dates=dates)


@bp.route('/player-tournament/<int:player_id>/<int:tournament_id>/')
@mobile_template('{mobile/}rating/player_tournament.html')
@cache.cached(key_prefix=lambda: request.url + str(request.MOBILE))
def player_tournament(template, player_id, tournament_id):
    player_tournament = m.PlayerTournament.query.filter_by(
        player_id=player_id, tournament_id=tournament_id).first()
    return render_template(template, player_tournament=player_tournament)


@bp.route('/tournament/<int:id>')
@mobile_template('{mobile/}rating/tournament.html')
@cache.cached(key_prefix=lambda: request.url + str(request.MOBILE))
def tournament(template, id):
    tournament = m.Tournament.query.get(id)
    return render_template(template, tournament=tournament)


@bp.route('/tournaments/<int:year>/<int:month>')
@bp.route('/tournaments')
@mobile_template('{mobile/}rating/tournaments.html')
@cache.cached(key_prefix=lambda: request.url + str(request.MOBILE))
def tournaments(template, year=None, month=None):
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
    return render_template(template, tournaments=tournaments,
                           year=year, month=month, years=years)


@bp.route('/win-chain')
@mobile_template('{mobile/}rating/win_chain.html')
@cache.cached(key_prefix=lambda: request.url + str(request.MOBILE))
def win_chain(template):
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
    return render_template(template, player1=player1, player2=player2,
                           chain=chain, count_all=count_all)


@bp.route('/games')
@mobile_template('{mobile/}rating/games_search.html')
@cache.cached(key_prefix=lambda: request.url + str(request.MOBILE))
def game_search(template):
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
        games = m.Game.query.join(m.Tournament).filter(*filters).order_by(
            m.Tournament.start_date.desc()).paginate(page=page, per_page=25)
    return render_template(template, games=games, player1=player1,
                           player2=player2, player1_id=player1_id,
                           player2_id=player2_id)


@bp.route('/statistics')
@mobile_template('{mobile/}rating/statistics.html')
@cache.cached(key_prefix=lambda: request.url + str(request.MOBILE))
def statistics(template):
    page = request.args.get('page', 1, type=int)
    issues = m.TopicIssue.query.join(m.Topic).options(
        eagerload('topic')).order_by(m.TopicIssue.new).order_by(
        m.Topic.index).paginate(per_page=7, page=page)
    return render_template(template, issues=issues)


@bp.route('/player-search/<name>')
@cache.cached()
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
                        'image': p.photo_url}
                       for p in matches])
