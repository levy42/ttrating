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
    headers = ['Player name', 'Rating', 'Weight', 'Year', 'City']
    top10 = models.Player.query.order_by(
        models.Player.rating.desc()).filter(
        models.Player.category == props['category'],
        models.Player.year >= (year - props['max_age'])).limit(
        props['count'])
    data = [{'Player name': {'text': x.name,
                             'href': '.player',
                             'name': True,
                             'id': x.id},
             'Rating': x.rating,
             'Weight': x.weight,
             'Year': x.year,
             'City': {'text': x.city, 'name': True}}
            for x in top10]
    return dict(headers=headers, data=data)


@topic_processor
def top_win(topic):
    props = topic.properties
    headers = ['Player', 'Rating', 'Opponent', 'Opponent rating',
               'Contribution']
    games = models.Game.query.join(models.Tournament).filter(
        models.Game.opponent_rating > props['rating_limit']).order_by(
        models.Game.contribution.desc()).limit(props['count']).all()
    data = [{'Player': {'text': g.player_name,
                        'href': 'main.player',
                        'id': g.player_id,
                        'name': True},
             'Rating': g.player_rating,
             'Opponent': {'text': g.opponent_name,
                          'href': 'main.player' if g.opponent_id else None,
                          'id': g.opponent_id,
                          'name': True},
             'Opponent rating': g.opponent_rating,
             'Contribution': g.contribution}
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
    headers = ['Player name', header, 'Year', 'City']
    data = [{'Player name': {'text': x.player.name,
                             'href': 'main.player',
                             'name': True,
                             'id': x.id},
             header: getattr(x, props['field']),
             'Year': x.player.year,
             'City': {'text': x.player.city, 'name': True}}
            for x in player_infos]
    return dict(headers=headers, data=data)


@topic_processor
def top_player_age(topic):
    props = topic.properties
    order = props.get('order', 'desc')
    player_infos = models.Player.query.order_by(
        getattr(models.Player.year, order)()).filter(
        models.Player.year).limit(props['count'])
    headers = ['Player name', 'Year', 'City']
    data = [{'Player name': {'text': x.name,
                             'href': 'main.player',
                             'name': True,
                             'id': x.id},
             'Year': x.year,
             'City': {'text': x.city, 'name': True}}
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

    headers = ['Player name', 'Win', 'Lose', 'Year', 'City']
    data = [{'Player name': {'text': x.player.name,
                             'href': 'main.player',
                             'name': True,
                             'id': x.id},
             'Win': x.game_won,
             'Lose': x.game_total - x.game_won,
             'Year': x.player.year,
             'City': {'text': x.player.city, 'name': True}}
            for x in top_list]
    return dict(headers=headers, data=data)


@topic_processor
def rating_dynamics(topic):
    rating_limit = topic.properties['rating_limit']
    label = 'Players count'
    rating_lists = models.RatingList.query.order_by('year', 'month').all()
    x = []
    y = ["%s %s" % (calendar.month_abbr[r.month], r.year) for r in
         rating_lists]
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
    label = 'Tournament count'
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
    label = 'Tournament count'
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
    y.append('Other')
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
    headers = ['Judge', 'Tournament total']
    data = [{'Judge': k,
             'Tournament total': v}
            for k, v in top_totals]

    return dict(headers=headers, data=data)


TOPICS = []


def load_topics():
    global TOPICS
    TOPICS = models.Topic.query.filter_by(active=True).all()


def calculate(period, only_new=False):
    for t in TOPICS:
        if only_new and models.TopicIssue.query.filter_by(
                topic_id=t.id).first():
            continue
        if period == t.period:
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
