"""
Utils service for parsing rankings data from reiting.com.ua
"""
import datetime
import os
import re

import requests
import xlrd
from bs4 import BeautifulSoup
from flask import current_app
from werkzeug.local import LocalProxy

from models import (
    db, Player, Tournament, WorldRating, Game, WorldPlayer,
    WorldRatingList, RatingList, Rating, Country, PlayerTournament, City)
from models import Category

WORLD_RATING = "http://www.old.ittf.com/ittf_ranking/PDF/%s_%s_%s.xls"
UA_RATING = "http://reiting.com.ua/rating"
UA_RATING_T = "http://reiting.com.ua/rating/nat/%s/0/?fs=&limit=0&male=%s"
UA_RATING_DOMEN = 'http://reiting.com.ua'

CATEGORY_MAPPINGS = {
    '100_M': Category.MEN,
    '100_W': Category.WOMEN,
}

LOG = LocalProxy(lambda: current_app.logger)


def parse_ua(month=None, year=None, rating_id=None):
    LOG.debug(f'Called rating parse: month: {month}, year: {year}.')
    year = year or datetime.datetime.now().year
    month = month or datetime.datetime.now().month
    rating_list = RatingList.query.filter_by(month=month, year=year).first()
    if rating_list:  # rating was already parsed
        LOG.debug('Rating already parsed')
        return
    if not rating_id:
        remote_rating_lists = get_all_rating_lists()
        rating_id = remote_rating_lists[0][0]
        if remote_rating_lists[0][2] != month:  # no new rating available
            LOG.debug('No new rating available')
            return
    updated_data = {'players': set(), 'cities': set(), 'tournaments': set(),
                    'changed_rating_players': set()}
    res = parse_ua_by_category(month, year, category=Category.MEN,
                               rating_id=rating_id,
                               parse_tourn=False)
    for k, v in res.items():
        updated_data[k].update(v)
    if res == -1:
        LOG.debug('Rating cannot be parsed')
        return
    res = parse_ua_by_category(month, year, category=Category.WOMEN,
                               rating_id=rating_id)
    for k, v in res.items():
        updated_data[k].update(v)
    rating_list = RatingList()
    rating_list.year = year
    rating_list.month = month
    rating_list.id = str(rating_id)

    db.session.add(rating_list)
    db.session.commit()

    return updated_data


def get_all_rating_lists():
    page = requests.get(UA_RATING_DOMEN + '/rating/all/?limit=1000')
    if page.status_code != 200:
        return []
    soup = BeautifulSoup(page.text, 'html.parser')
    table = soup.find("table")
    ratings = []
    for row in table.findAll("tr"):
        cells = row.findAll("td")
        if len(cells) < 3:
            continue
        href = cells[0].find('a').get('href')
        date = cells[2].find(text=True)
        month, year = date.split('-')[1:]
        month = int(month)
        year = int(year)
        ratings.append((int(href.rsplit('/', 3)[1]), year, month))

    return ratings


def parse_ua_all():
    rating_lists = get_all_rating_lists()
    all_data = {'players': set(), 'cities': set(), 'tournaments': set(),
                'was_updated': False}
    for rating_id, year, month in rating_lists:
        updated_data = parse_ua(month=month, year=year, rating_id=rating_id)
        if updated_data:
            all_data['was_updated'] = True
            all_data['players'].update(updated_data['players'])
            all_data['cities'].update(updated_data['cities'])
            all_data['tournaments'].update(updated_data['tournament'])
    return all_data


def _trim_city(city: str):
    if city.startswith('г.'):
        return city[2:].strip()


def parse_ua_by_category(month, year, rating_id, category=Category.MEN,
                         parse_tourn=True, previous_id=None):
    LOG.debug(
        f'Parsing rating: month = {month}, year = {year}, id = {rating_id}.')
    updated_data = {'players': [], 'cities': [], 'tournaments': [],
                    'changed_rating_players': []}

    cities = {c.name: c.name for c in City.query.all()}
    new_cities = []
    male = 1 if category == Category.MEN else 2
    link = UA_RATING_T % (rating_id, male) if id else UA_RATING
    page = requests.get(link)
    if page.status_code != 200:
        return -1
    if int(page.url.rsplit('/', 3)[1]) == previous_id:
        return -1
    soup = BeautifulSoup(page.text, 'html.parser')
    table = soup.find("table", {"id": "sortTable"})
    prev_position = 1
    Player.query.filter_by(category=category).update(
        {'prev_rating': Player.rating})
    Player.query.filter_by(category=category).update({'rating': 0})
    db.session.commit()
    db.session.expire_all()
    players = []
    for row in table.findAll("tr"):
        cells = row.findAll("td")
        if len(cells) < 6:
            continue

        position = cells[0].find(text=True)
        if not position:
            position = prev_position
        position = int(position)

        prev_position = position
        name = cells[1].find(text=True)
        href = cells[1].find('a').get('href')
        external_id = int(href.rsplit('/', 2)[1])

        player = Player.query.filter_by(
            external_id=external_id).first()
        if not player:
            player = Player()
            updated_data['players'].append(name)

        player.rating = float(cells[3].find(text=True).replace(',', '.'))
        player.rating_fine = float(cells[2].find(text=True).replace(',', '.'))
        player.weight = int(cells[4].find(text=True))
        player.year = int(cells[5].find(text=True) or 0)
        city = cells[6].find(text=True)
        locations = city.split('-')
        player.city = locations[0]

        if len(locations) > 1:
            player.city2 = locations[1]
        player.prev_rating = float(cells[7].find(text=True).replace(',', '.'))

        if not player.max or player.max < player.rating:
            player.max = player.rating

        player.name = name
        player.category = category
        player.external_id = external_id
        player.position = position

        locations = city.split('-')
        player.city = locations[0]

        if len(locations) > 1:
            player.city2 = locations[1]

        if not cities.get(player.city):
            cities[player.city] = player.city
            new_cities.append(player.city)
            updated_data['cities'].append(player.city)

        if not cities.get(player.city2):
            cities[player.city2] = player.city2
            new_cities.append(player.city2)
            updated_data['cities'].append(player.city2)

        players.append(player)
        db.session.add(player)

    db.session.commit()
    for p in players:
        p_rating = Rating.query.filter_by(
            player_id=p.id, year=year, month=month).first() or Rating()
        p_rating.player_id = p.id
        p_rating.rating = p.rating
        p_rating.weight = p.weight
        p_rating.position = p.position
        p_rating.month = month
        p_rating.year = year
        p_rating.rating_fine = p.fine_rating
        db.session.add(p_rating)

    for c in new_cities:
        if not c:
            continue
        new_city = City()
        new_city.name = c
        db.session.add(new_city)

    db.session.commit()

    if parse_tourn:
        LOG.debug('Parsing tournaments...')
        tourn_table = soup.find("table", {"id": "tourn-table"})
        if tourn_table:
            tournaments = []
            for row in tourn_table.findAll("tr"):
                try:
                    cells = row.findAll("td")
                    if len(cells) < 3:
                        continue

                    tourn_href = cells[0].find('a').get('href')
                    name = cells[0].find(text=True)
                    city = cells[1].find(text=True)
                    judge = cells[2].find(text=True)
                    if 'subtourn' in tourn_href:
                        tourn_page = requests.get(UA_RATING_DOMEN + tourn_href)
                        if tourn_page.status_code != 200:
                            continue
                        tourn_soup = BeautifulSoup(tourn_page.text,
                                                   'html.parser')
                        subtourn_table = tourn_soup.find("table",
                                                         {"id": "sortTable"})
                        for row in subtourn_table.findAll("tr"):
                            try:
                                cells = row.findAll("td")
                                if len(cells) < 3:
                                    continue
                                sub_name = cells[0].find(text=True)
                                sub_href = cells[0].find('a').get('href')
                                tournament = Tournament()
                                tournament.city = _trim_city(city)
                                tournament.judge = judge
                                tournament.name = name + " " + sub_name
                                tourn_external_id = \
                                    int(sub_href.rsplit('/', 2)[1])
                                if Tournament.query.filter_by(
                                        external_id=tourn_external_id).first():
                                    LOG.debug('Tournament already exist')
                                    continue
                                updated_data['tournaments'].append(
                                    tournament.name)
                                tournament.external_id = tourn_external_id
                                tournament.rating_list_id = rating_id
                                parce_tournament_date(tournament)
                                tournaments.append((tournament, sub_href))
                                LOG.debug(f'--Parsed tournaments {tourn_href}')
                            except Exception as e:
                                LOG.debug(f'Failed to pasre tournaments. '
                                          f'Rating id {rating_id}')
                    else:
                        tournament = Tournament()
                        tournament.city = city
                        tournament.judge = judge
                        tournament.name = name
                        tourn_external_id = int(tourn_href.rsplit('/', 2)[1])
                        if Tournament.query.filter_by(
                                external_id=tourn_external_id).first():
                            LOG.debug('Tournament already exist')
                            continue
                        updated_data['tournaments'].append(
                            tournament.name)
                        tournament.external_id = tourn_external_id
                        tournament.rating_list_id = rating_id
                        parce_tournament_date(tournament)
                        tournaments.append((tournament, tourn_href))
                        LOG.debug(f'--Parsed tournaments {tourn_href}')
                except Exception as e:
                    LOG.debug(f'Failed to pasre tournaments. '
                              f'Rating id {rating_id}. Reason {e}')

            for tournament, _ in tournaments:
                db.session.add(tournament)
            db.session.commit()

            for tournament, href in tournaments:
                parse_tournament(href, tournament)
            db.session.commit()

    return updated_data


def parse_world_rating_all():
    i = 0
    for year in range(2014, 2018):
        for month in range(1, 13):
            for category in CATEGORY_MAPPINGS:
                i += 1
                LOG.debug(year, month, category)
                parse_world_by_category(category, year=year, month=month)


def parse_world_rating():
    was_updated = False
    for category in CATEGORY_MAPPINGS:
        if parse_world_by_category(category):
            was_updated = True
    return was_updated


def parse_world_by_category(category='100_M', year=None, month=None):
    countries = {c.code: c.code for c in Country.query.all()}
    countries_codes = []
    mapped_category = CATEGORY_MAPPINGS[category]
    now = datetime.datetime.now()
    if not year:
        year = now.year
    if not month:
        month = now.month
    rating_id = category + str(month) + str(year)
    previous_rating = WorldRatingList.query.get(rating_id)
    if previous_rating:
        return
    man_rating_link = WORLD_RATING % (category, month, year)
    latest_ratings = requests.get(man_rating_link)
    if latest_ratings.status_code != 200:
        return
    document_name = os.path.join(
        f'/tmp/WorldRating_{category}_{month}_{year}.xls')

    with open(document_name, 'wb') as f:
        f.write(latest_ratings.content)

    xls_book = xlrd.open_workbook(document_name)
    sheet = xls_book.sheet_by_index(0)
    players = {p.name: p for p in
               WorldPlayer.query.filter_by(
                   category=mapped_category).all()}
    for p in players.values():
        p.rating = 0
    for index in range(0, sheet.nrows):
        position = sheet.cell(index, 0).value
        try:
            position = int(position)
        except Exception:
            continue
        name = str(sheet.cell(index, 2).value.replace('^', '').strip())
        country_code = str(sheet.cell(index, 3).value.replace('^', '').strip())
        rating = int(sheet.cell(index, 4).value.strip())
        player = players.get(name)

        if not player:
            player = WorldPlayer()
            player.category = mapped_category
            player.country_code = country_code
            player.name = name

            if not countries.get(country_code, None):
                countries[country_code] = country_code
                countries_codes.append(country_code)

        player.rating = rating
        player.position = position
        players[name] = player
        db.session.add(player)

    db.session.commit()
    previous_world_ratings = {r.player_id: 1 for r in
                              WorldRating.query.filter_by(
                                  year=year, month=month).all()}
    for p in players.values():
        if not p.id or previous_world_ratings.get(p.id):
            continue
        world_rating = WorldRating()
        world_rating.month = month
        world_rating.year = year
        world_rating.player_id = p.id
        world_rating.rating = p.rating
        world_rating.position = p.position
        db.session.add(world_rating)

    for c in countries_codes:
        country = Country()
        country.code = str(c)
        country.name = str(c)
        db.session.add(country)

    rating_list = WorldRatingList()
    rating_list.year = year
    rating_list.month = month
    rating_list.category = category
    rating_list.id = rating_id
    db.session.add(rating_list)
    db.session.commit()
    os.remove(document_name)

    return True


def parse_tournament(href, tournament):
    page = requests.get(UA_RATING_DOMEN + href + '?limit=1000')
    if page.status_code != 200:
        return []
    soup = BeautifulSoup(page.text, 'html.parser')
    table = soup.find("table")
    games = []
    player_tourns = []
    for row in table.findAll("tr"):
        cells = row.findAll("td")
        if len(cells) < 1:
            continue
        href = cells[0].find('a').get('href')
        external_id = int(href.rsplit('/', 2)[1])
        player = Player.query.filter_by(external_id=external_id).first()
        if not player:
            player = Player()
            player.name = cells[0].find(text=True)
            parsed_player_info = parse_player(external_id)
            if not parsed_player_info:
                continue
            city, year = parsed_player_info
            player.city = city
            player.year = year
            player.external_id = external_id
            db.session.add(player)
            db.session.commit()
        player_tourn = PlayerTournament()
        player_tourn.player_id = player.id
        player_tourn.tournament_id = tournament.id
        player_tourn.start_rating = float(
            cells[1].find(text=True).replace(',', '.'))
        player_tourn.final_rating = float(
            cells[5].find(text=True).replace(',', '.'))
        player_tourn.start_weight = int(cells[2].find(text=True))
        player_tourn.final_weight = int(cells[6].find(text=True))
        player_tourn.delta_rating = float(
            cells[3].find(text=True).replace(',', '.'))
        player_tourn.delta_weight = int(cells[4].find(text=True))
        player_games = parse_games(player, href, player_tourn.start_rating)
        for g in player_games:
            g.date = tournament.start_date
        games += player_games
        player_tourn.game_total = len(player_games)
        player_tourns.append(player_tourn)
    for g in games:
        g.tournament_id = tournament.id
        db.session.add(g)
    for p_t in player_tourns:
        db.session.add(p_t)


def parse_player(player_id):
    LOG.debug("Found not existing player, parsing new player")
    page = requests.get(UA_RATING_DOMEN + f'/rating/p/1/{player_id}/')
    if page.status_code != 200:
        return []
    soup = BeautifulSoup(page.text, 'html.parser')
    table = soup.find("table")
    if not table:
        return None
    row1, row2 = table.findAll("tr")[1:3]
    city = row1.findAll("td")[1].find(text=True)
    year = row2.findAll("td")[1].find(text=True)
    if not year:
        year = 0
    return city, int(year)


def parse_games(player, player_href, start_rating):
    LOG.debug(f'----Parse games {player_href}')
    games = []
    page = requests.get(UA_RATING_DOMEN + player_href)
    if page.status_code != 200:
        return []
    soup = BeautifulSoup(page.text, 'html.parser')
    if not player:
        return []
    table = soup.find("table", {'class': 'striped'})
    if not table:
        return []
    for row in table.findAll("tr"):
        cells = row.findAll("td")
        if len(cells) < 1:
            continue
        oponent_name = cells[2].find(text=True)
        contribution = cells[4].find(text=True)
        oponent_rating = cells[3].find(text=True)
        o_href = cells[2].find('a')
        if o_href:
            o_href = o_href.get('href')
            oponent_external_id = int(o_href.rsplit('/', 2)[1])
        else:
            oponent_external_id = -1
        result = cells[1].find(text=True)
        result = False if result == u'проиграл' else True
        game = Game()
        game.player_id = player.id
        game.player_name = player.name
        oponent = Player.query.filter_by(
            external_id=oponent_external_id).first()
        game.opponent_name = oponent_name
        if oponent:
            game.opponent_id = oponent.id
        game.result = result
        game.contribution = int(contribution)
        game.opponent_rating = float(oponent_rating.replace(',', '.'))
        game.player_rating = start_rating
        games.append(game)
    return games


def parce_tournament_date(tournament):
    def case2(date, t):
        date = date.group(0)
        days, month, year = date.split('.')
        days = days.split('-')
        t.start_date = datetime.date(year=int(year), month=int(month),
                                     day=int(days[0]))
        t.end_date = datetime.date(year=int(year), month=int(month),
                                   day=int(days[1]))

    def case3(date, t):
        date = date.group(0)
        day, month, year = date.split('.')
        t.start_date = datetime.date(year=int(year), month=int(month),
                                     day=int(day))
        t.end_date = t.start_date

    def case1(date, t):
        date = date.group(0)
        parts = date.split('-')
        sub_dates = []
        sub_dates += parts[0].split('.')
        sub_dates += parts[1].split('.')
        t.start_date = datetime.date(year=int(sub_dates[4]),
                                     month=int(sub_dates[1]),
                                     day=int(sub_dates[0]))
        t.end_date = datetime.date(year=int(sub_dates[4]),
                                   month=int(sub_dates[3]),
                                   day=int(sub_dates[2]))

    cases = [('[0-9]+\.[0-9]+-[0-9]+\.[0-9]+\.[0-9]+', case1),
             ('[0-9]+-[0-9]+\.[0-9]+\.[0-9]+', case2),
             ('[0-9]+\.[0-9]+\.[0-9]+', case3)]
    try:
        date = None
        for c, d in cases:
            date = re.search(c, tournament.name)
            if date:
                d(date, tournament)
                break
        if not date:
            tournament.start_date = datetime.date(
                year=tournament.rating_list.year,
                month=tournament.rating_list.month,
                day=1)
    except Exception as e:
        tournament.start_date = datetime.date(
            year=tournament.rating_list.year,
            month=tournament.rating_list.month,
            day=1)
        LOG.debug(e)
        LOG.debug(tournament.name)


def parse_tt_cup_photos():
    import json
    players_data = {}
    for i in range(1, 27):
        page = requests.get(f'http://tt-cup.com/player/{i}')
        if page.status_code != 200:
            continue
        soup = BeautifulSoup(page.text, 'html.parser')
        players = soup.findAll("div", {'class': 'player left'})
        if not players:
            continue
        for p in players:
            try:
                photo_url = p.find("a", {'class': 'fancybox'}).get('href')
                name = p.find("div", {'class': 'player-name'}).find('a').get(
                    'title')
                LOG.debug(name)
                LOG.debug(photo_url)
                players_data[name] = photo_url
            except Exception as e:
                LOG.debug(f'Error processing image for url {photo_url} : {e}')
    with open('photos.json', 'w') as f:
        json.dump(players_data, f)
