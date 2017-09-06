from flask import g
from app import cache, translate_name
import models as m


@cache.cached(key_prefix=lambda: g.lang + 'cities')
def cities():
    return {c.name: {'id': c.name, 'weight': c.weight,
                     'title': translate_name(c.name)}
            for c in m.City.query.all()}


@cache.cached(key_prefix=lambda: g.lang + 'countries')
def countries():
    return {c.code: c for c in m.Country.query.all()}


@cache.cached(key_prefix='get_rating_lists')
def get_rating_lists():
    return m.RatingList.query.order_by(m.RatingList.year.desc(),
                                       m.RatingList.month.desc()).all()


@cache.cached(key_prefix='get_years')
def get_years():
    return sorted(list(set([x.year for x in get_rating_lists()])))
