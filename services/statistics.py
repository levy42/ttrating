import calendar
import datetime

from sqlalchemy import extract

import models


class Type():
    CHART = 1
    LIST = 2


class Period():
    MONTH = 1
    YEAR = 2
    ENTIRE = 3


PROCESSORS = {}


def set_date(topic_issue, date):
    topic_issue.date = date
    if topic_issue.topic.period == Period.MONTH:
        topic_issue.period_date = datetime.date(year=date.year,
                                                month=date.month - 1,
                                                day=1)
    elif topic_issue.topic.period == Period.YEAR:
        topic_issue.period_date = datetime.date(year=date.year - 1, month=1,
                                                day=1)
    elif topic_issue.topic.period == Period.ENTIRE:
        topic_issue.period_date = datetime.date(year=2000, month=1,
                                                day=1)


def topic_processor(func):
    PROCESSORS[func.__name__] = func


@topic_processor
def top_rating_list(topic):
    year = datetime.date.today().year
    props = topic.properties
    headers = ['Гравець', 'Рейтинг', 'Вага', 'Рік', 'Місто']
    top10 = models.Player.query.order_by(
        models.Player.rating.desc()).filter(
        models.Player.category == props['category'],
        models.Player.year >= (year - props['max_age'])).limit(
        props['count'])
    data = [{'Гравець': {'text': x.name,
                         'href': 'main.player',
                         'name': True,
                         'id': x.id},
             'Рейтинг': x.rating,
             'Вага': x.weight,
             'Рік': x.year,
             'Місто': {'text': x.city, 'name': True}}
            for x in top10]
    return dict(headers=headers, data=data)


@topic_processor
def top_win(topic):
    props = topic.properties
    headers = ['Гравець', 'Рейтинг', 'Суперник', 'Рейтинг суперника',
               'Вклад']
    games = models.Game.query.join(models.Tournament).filter(
        models.Game.opponent_rating > props['rating_limit']).order_by(
        models.Game.contribution.desc()).limit(props['count']).all()
    data = [{'Гравець': {'text': g.player_name,
                         'href': 'main.player',
                         'id': g.player_id,
                         'name': True},
             'Рейтинг': g.player_rating,
             'Суперник': {'text': g.opponent_name,
                          'href': 'main.player' if g.opponent_id else None,
                          'id': g.opponent_id,
                          'name': True},
             'Рейтинг суперника': g.opponent_rating,
             'Вклад': g.contribution}
            for g in games]
    return dict(data=data, headers=headers)


@topic_processor
def top_total(topic):
    props = topic.properties
    order = props.get('order', 'desc')
    criteria = getattr(getattr(models.PlayerInfo, props['field']), order)()
    header = props['header']
    player_infos = models.PlayerInfo.query.order_by(criteria).limit(
        props['count'])
    headers = ['Гравець', header, 'Рік', 'Місто']
    data = [{'Гравець': {'text': x.player.name,
                         'href': 'main.player',
                         'name': True,
                         'id': x.id},
             header: getattr(x, props['field']),
             'Рік': x.player.year,
             'Місто': {'text': x.player.city, 'name': True}}
            for x in player_infos]
    return dict(headers=headers, data=data)


@topic_processor
def top_player_age(topic):
    props = topic.properties
    order = props.get('order', 'desc')
    player_infos = models.Player.query.order_by(
        getattr(models.Player.year, order)()).filter(
        models.Player.year).limit(props['count'])
    headers = ['Гравець', 'Рік', 'Місто']
    data = [{'Гравець': {'text': x.name,
                         'href': 'main.player',
                         'name': True,
                         'id': x.id},
             'Рік': x.year,
             'Місто': {'text': x.city, 'name': True}}
            for x in player_infos]
    return dict(headers=headers, data=data)


@topic_processor
def top_winner(topic):
    min_game_total = topic.properties['min_game_total']
    count = topic.properties['count']
    player_infos = models.PlayerInfo.query.filter(
        models.PlayerInfo.game_total > min_game_total).all()

    top_list = sorted(player_infos, key=lambda x: float(
        x.game_won) / x.game_total, reverse=True)[:count]

    headers = ['Гравець', 'Перемога', 'Поразка', 'Рік', 'Місто']
    data = [{'Гравець': {'text': x.player.name,
                         'href': 'main.player',
                         'name': True,
                         'id': x.id},
             'Перемога': x.game_won,
             'Поразка': x.game_total - x.game_won,
             'Рік': x.player.year,
             'Місто': {'text': x.player.city, 'name': True}}
            for x in top_list]
    return dict(headers=headers, data=data)


@topic_processor
def rating_dynamics(topic):
    rating_limit = topic.properties['rating_limit']
    label = 'Кількість гравців'
    rating_lists = models.RatingList.query.order_by('year', 'month').all()
    x = []
    y = [f'{r.month:0>2} {r.year}' for r in rating_lists]
    for r in rating_lists:
        player60_count = models.Rating.query.filter(
            models.Rating.rating > rating_limit,
            models.Rating.year == r.year,
            models.Rating.month == r.month).count()
        x.append(player60_count)
    return dict(label=label, x=x, y=y)


@topic_processor
def tournament_dynamics_by_year(topic):
    city = topic.properties.get('city')
    label = 'Кількість турнірів'
    rating_lists = models.RatingList.query.all()
    years = set()
    for l in rating_lists:
        years.add(l.year)
    x = []
    years = sorted(list(years))
    for y in years:
        if city:
            total = models.Tournament.query.filter(
                extract('year', models.Tournament.start_date) == y).filter_by(
                city=city).count()
        else:
            total = models.Tournament.query.filter(
                extract('year', models.Tournament.start_date) == y).count()
        x.append(total)
    return dict(label=label, x=x, y=years)


@topic_processor
def tournament_dynamics_by_city(topic):
    count = topic.properties.get('count')
    tournaments = models.Tournament.query.all()
    label = 'Кількість турнірів'
    city_totals = {}
    for t in tournaments:
        city_totals[t.city] = city_totals.get(t.city, 0) + 1

    city_totals_sorted = sorted(city_totals.items(), key=lambda x: x[1],
                                reverse=True)
    top_totals = city_totals_sorted[:count]
    other_total = sum([x[1] for x in city_totals_sorted])
    x = []
    y = []
    for i in top_totals:
        y.append(i[0])
        x.append(i[1])
    y.append('Інші')
    x.append(other_total)

    return dict(label=label, x=x, y=y)


@topic_processor
def most_active_judges(topic):
    count = topic.properties.get('count')
    tournaments = models.Tournament.query.all()
    judges_totals = {}
    for t in tournaments:
        judges_totals[t.judge] = judges_totals.get(t.judge, 0) + 1

    judges_totals_sorted = sorted(judges_totals.items(), key=lambda x: x[1],
                                  reverse=True)
    top_totals = judges_totals_sorted[:count]
    headers = ['Суддя', 'Кількість турнірів']
    data = [{'Суддя': k,
             'Кількість турнірів': v}
            for k, v in top_totals]

    return dict(headers=headers, data=data)


def calculate(only_new=False):
    for t in models.Topic.query.filter_by(active=True).all():
        if only_new and models.TopicIssue.query.filter_by(
                topic_id=t.id).first():
            continue
        data = PROCESSORS[t.processor](t)
        topic_issue = models.TopicIssue(t.id, data)
        topic_issue.topic = t
        set_date(topic_issue, datetime.date.today())
        old_issue = models.TopicIssue.query. \
            filter_by(new=True, topic_id=t.id).first()
        if old_issue:
            old_issue.new = False
            models.db.session.add(old_issue)
        models.db.session.add(topic_issue)

    models.db.session.commit()
