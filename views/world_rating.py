import json
from flask import abort, request, url_for, Blueprint
from sqlalchemy.orm import eagerload
import models as m
from app import cache, render_template, month_abbr
from views.common import countries, translate_name

bp = Blueprint('world_rating', __name__,
               template_folder='templates/world_rating/')


@bp.route('/world-rating/<category>/')
@bp.route('/world-rating/')
@cache.cached(key_prefix=lambda: request.url)
def rating(category='MEN'):
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
    ).order_by('world.' + sort_by).paginate(page=page, per_page=limit)

    return render_template('world-rating.html', rating=rating,
                           categories=m.Category.VALUES, category=category,
                           year=year, month=month, years=years)


@bp.route("/world-player/<id>/")
@cache.cached()
def player(id):
    player = m.WorldPlayer.query.get(id)
    if not player:
        abort(404)
    rating_history = m.WorldRating.query.filter_by(player_id=id).order_by(
        m.WorldRating.year, m.WorldRating.month).all()[-36:]  # tmp limit
    ratings = [r.rating for r in rating_history]
    positions = [r.position for r in rating_history]
    dates = [f'{month_abbr[r.month]} {r.year}' for r in
             rating_history]
    return render_template('world-player.html', player=player, ratings=ratings,
                           positions=positions, dates=dates)


@bp.route("/world-player-search/<name>")
def player_search(name):
    matches = m.WorldPlayer.query.filter(m.WorldPlayer.name.like(
        '%' + name.title() + '%')).limit(10).all()
    return json.dumps([{'name': p.name,
                        'rating': p.rating or '0.0',
                        'url': url_for('.world_player', id=p.id),
                        'country': translate_name(countries().get(
                            p.country_code).name)} for p in matches])
