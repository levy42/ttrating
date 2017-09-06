import datetime
from flask import request, redirect, url_for, Blueprint
import models as m
from app import cache, render_template, db
from views.common import cities

bp = Blueprint('sparring', __name__, template_folder='templates/sparring/',
               url_prefix='sparring')


@bp.route('/')
def all():
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


@bp.route('/add', methods=['GET', 'POST'])
def add():
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
