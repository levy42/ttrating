import datetime
import os
import traceback
import re

import requests
import xlrd
from bs4 import BeautifulSoup

import models as m
from models import Category

WORLD_RATING = "http://www.old.ittf.com/ittf_ranking/PDF/%s_%s_%s.xls"
UA_RATING = "http://reiting.com.ua/rating"
UA_RATING_T = "http://reiting.com.ua/rating/nat/%s/0/?fs=&limit=0&male=%s"
UA_RATING_DOMEN = 'http://reiting.com.ua'

CATEGORY_MAPPINGS = {
    '100_M': Category.MEN,
    '100_W': Category.WOMEN,
}


def parse_ua(month=None, year=None, rating_id=None):
    print('Called rating parse: month: %s, year: %s' % (month, year))
    year = year or datetime.datetime.now().year
    month = month or datetime.datetime.now().month
    rating_list = m.RatingList.query.filter_by(month=month, year=year).first()
    if rating_list:  # rating was already parsed
        print('Rating already parsed')
        return
    if not rating_id:
        remote_rating_lists = get_all_rating_lists()
        rating_id = remote_rating_lists[0][0]
        if remote_rating_lists[0][2] != month:  # no new rating available
            print('No new rating available')
            return
    res = parse_ua_by_category(month, year, category=Category.MEN,
                               rating_id=rating_id,
                               parse_tourn=False)
    if res == -1:
        print('Rating cannot be parsed')
        return
    parse_ua_by_category(month, year, category=Category.WOMEN,
                         rating_id=rating_id)
    rating_list = m.RatingList()
    rating_list.year = year
    rating_list.month = month
    rating_list.id = str(rating_id)

    m.db.session.add(rating_list)
    m.db.session.commit()


def get_all_rating_lists():
    page = requests.get(UA_RATING_DOMEN + '/rating/all/?limit=1000')
    if page.status_code != 200:
        return []
    soup = BeautifulSoup(page.text)
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
    for rating_id, year, month in rating_lists:
        parse_ua(month=month, year=year, rating_id=rating_id)


def parse_ua_by_category(month, year, category=m.Category.MEN,
                         rating_id=None, parse_tourn=True, previous_id=None):
    print('Parsing rating: month = %s, year = %s, external id = %s' % (
        month, year, rating_id))
    updated_data = {'players': [], 'cities': [], 'tournaments': []}

    cities = {c.name: c.name for c in m.City.query.all()}
    new_cities = []
    male = 1 if category == Category.MEN else 2
    link = UA_RATING_T % (rating_id, male) if id else UA_RATING
    page = requests.get(link)
    if page.status_code != 200:
        return -1
    if int(page.url.rsplit('/', 3)[1]) == previous_id:
        return -1
    soup = BeautifulSoup(page.text)
    table = soup.find("table", {"id": "sortTable"})
    prev_position = 1
    m.Player.query.update({'rating': 0})
    m.db.session.commit()
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
        rating = float(cells[3].find(text=True).replace(',', '.'))
        rating_fine = float(cells[2].find(text=True).replace(',', '.'))
        weight = int(cells[4].find(text=True))
        p_year = int(cells[5].find(text=True) or 0)
        city = cells[6].find(text=True)
        prev_rating = float(cells[7].find(text=True).replace(',', '.'))

        player = m.Player.query.filter_by(
                external_id=external_id).first()
        if not player:
            player = m.Player()
            updated_data['players'].append(name)

        player.prev_rating = player.rating
        if player.max < rating:
            player.max = rating
        player.rating = rating
        player.year = p_year
        player.name = name
        player.fine_rating = rating_fine
        player.category = category
        player.external_id = external_id

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

        player.position = position
        player.prev_rating = prev_rating
        player.weight = weight
        m.db.session.add(player)
        players.append(player)

    m.db.session.commit()
    for p in players:
        p_rating = m.Rating()
        p_rating.player_id = p.id
        p_rating.rating = p.rating
        p_rating.weight = p.weight
        p_rating.position = p.position
        p_rating.month = month
        p_rating.year = year
        p_rating.rating_fine = p.fine_rating
        m.db.session.add(p_rating)

    for c in new_cities:
        if not c:
            continue
        new_city = m.City()
        new_city.name = c
        m.db.session.add(new_city)

    m.db.session.commit()

    if parse_tourn:
        print('Parsing tournaments...')
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
                        tourn_soup = BeautifulSoup(tourn_page.text)
                        subtourn_table = tourn_soup.find("table",
                                                         {"id": "sortTable"})
                        for row in subtourn_table.findAll("tr"):
                            try:
                                cells = row.findAll("td")
                                if len(cells) < 3:
                                    continue
                                sub_name = cells[0].find(text=True)
                                sub_href = cells[0].find('a').get('href')
                                tournament = m.Tournament()
                                tournament.city = city
                                tournament.judge = judge
                                tournament.name = name + " " + sub_name
                                tourn_external_id = int(
                                        sub_href.rsplit('/', 2)[1])
                                if m.Tournament.query.filter_by(
                                        external_id=tourn_external_id).first():
                                    print('Tournament already exist')
                                    continue
                                updated_data['tournaments'].append(
                                        tournament.name)
                                tournament.external_id = tourn_external_id
                                tournament.rating_list_id = rating_id
                                parce_tournament_date(tournament)
                                tournaments.append((tournament, sub_href))
                                print("--Parsed tournaments %s" % tourn_href)
                            except Exception:
                                traceback.print_exc()
                                pass
                    else:
                        tournament = m.Tournament()
                        tournament.city = city
                        tournament.judge = judge
                        tournament.name = name
                        tourn_external_id = int(tourn_href.rsplit('/', 2)[1])
                        if m.Tournament.query.filter_by(
                                external_id=tourn_external_id).first():
                            print('Tournament already exist')
                            continue
                        updated_data['tournaments'].append(
                                tournament.name)
                        tournament.external_id = tourn_external_id
                        tournament.rating_list_id = rating_id
                        parce_tournament_date(tournament)
                        tournaments.append((tournament, tourn_href))
                        print("--Parsed tournaments %s" % tourn_href)
                except Exception:
                    traceback.print_exc()
                    print(
                            'ERROR. Failed to pasre tournaments. Rating id %s' %
                            rating_id)
                    pass

            for tournament, _ in tournaments:
                m.db.session.add(tournament)
            m.db.session.commit()

            for tournament, href in tournaments:
                parse_tournament(href, tournament.id)
            m.db.session.commit()

    return int(page.url.rsplit('/', 3)[1])


def parse_world_rating_all():
    i = 0
    for year in range(2014, 2018):
        for month in range(1, 13):
            for category in CATEGORY_MAPPINGS:
                i += 1
                print(year, month, category)
                parse_world_by_category(category, year=year, month=month)


def parse_world_rating():
    for category in CATEGORY_MAPPINGS:
        parse_world_by_category(category)


def parse_world_by_category(category='100_M', year=None, month=None):
    countries = {c.code: c.code for c in m.Country.query.all()}
    countries_codes = []
    mapped_category = CATEGORY_MAPPINGS[category]
    now = datetime.datetime.now()
    if not year:
        year = now.year
    if not month:
        month = now.month
    rating_id = category + str(month) + str(year)
    previous_rating = m.WorldRatingList.query.get(rating_id)
    if previous_rating:
        return
    man_rating_link = WORLD_RATING % (category, month, year)
    latest_ratings = requests.get(man_rating_link)
    if latest_ratings.status_code != 200:
        return
    document_name = os.path.join('/tmp/WorldRating_%s_%s_%s.xls' % (
        category, month, year))

    with open(document_name, 'wb') as f:
        f.write(latest_ratings.content)

    xls_book = xlrd.open_workbook(document_name)
    sheet = xls_book.sheet_by_index(0)
    players = {p.name: p for p in
               m.WorldPlayer.query.filter_by(
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
            player = m.WorldPlayer()
            player.category = mapped_category
            player.country_code = country_code
            player.name = name

            if not countries.get(country_code, None):
                countries[country_code] = country_code
                countries_codes.append(country_code)

        player.rating = rating
        player.position = position
        players[name] = player
        m.db.session.add(player)

    m.db.session.commit()
    previous_world_ratings = {r.player_id: 1 for r in
                              m.WorldRating.query.filter_by(
                                      year=year, month=month).all()}
    for p in players.values():
        if not p.id or previous_world_ratings.get(p.id):
            continue
        world_rating = m.WorldRating()
        world_rating.month = month
        world_rating.year = year
        world_rating.player_id = p.id
        world_rating.rating = p.rating
        world_rating.position = p.position
        m.db.session.add(world_rating)

    for c in countries_codes:
        country = m.Country()
        country.code = str(c)
        country.name = str(c)
        m.db.session.add(country)

    rating_list = m.WorldRatingList()
    rating_list.year = year
    rating_list.month = month
    rating_list.category = category
    rating_list.id = rating_id
    m.db.session.add(rating_list)
    m.db.session.commit()
    os.remove(document_name)


def parse_tournament(href, tournament_id):
    page = requests.get(UA_RATING_DOMEN + href + '?limit=1000')
    if page.status_code != 200:
        return []
    soup = BeautifulSoup(page.text)
    table = soup.find("table")
    games = []
    player_tourns = []
    for row in table.findAll("tr"):
        cells = row.findAll("td")
        if len(cells) < 1:
            continue
        href = cells[0].find('a').get('href')
        external_id = int(href.rsplit('/', 2)[1])
        player = m.Player.query.filter_by(external_id=external_id).first()
        if not player:
            player = m.Player()
            player.name = cells[0].find(text=True)
            parsed_player_info = parse_player(external_id)
            if not parsed_player_info:
                continue
            city, year = parsed_player_info
            player.city = city
            player.year = year
            player.external_id = external_id
            m.db.session.add(player)
            m.db.session.commit()
        player_tourn = m.PlayerTournament()
        player_tourn.player_id = player.id
        player_tourn.tournament_id = tournament_id
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
        games += player_games
        player_tourn.game_total = len(player_games)
        player_tourns.append(player_tourn)
    for g in games:
        g.tournament_id = tournament_id
        m.db.session.add(g)
    for p_t in player_tourns:
        m.db.session.add(p_t)


def parse_player(player_id):
    print("Found not existing player, parsing new player")
    page = requests.get(UA_RATING_DOMEN + '/rating/p/1/%s/' % player_id)
    if page.status_code != 200:
        return []
    soup = BeautifulSoup(page.text)
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
    print("----Parse games %s" % player_href)
    games = []
    page = requests.get(UA_RATING_DOMEN + player_href)
    if page.status_code != 200:
        return []
    soup = BeautifulSoup(page.text)
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
        game = m.Game()
        game.player_id = player.id
        game.player_name = player.name
        oponent = m.Player.query.filter_by(
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
        print(e)
        print(tournament.name)


def parse_tt_cup_photos():
    import json
    players_data = {}
    for i in range(1, 27):
        page = requests.get('http://tt-cup.com/player/%s' % i)
        if page.status_code != 200:
            continue
        soup = BeautifulSoup(page.text)
        players = soup.findAll("div", {'class': 'player left'})
        if not players:
            continue
        for p in players:
            try:
                photo_url = p.find("a", {'class': 'fancybox'}).get('href')
                name = p.find("div", {'class': 'player-name'}).find('a').get(
                    'title')
                print(name)
                print(photo_url)
                players_data[name] = photo_url
            except Exception as e:
                print("Error: %s" % e)
    with open('photos.json', 'w') as f:
        json.dump(players_data, f)
