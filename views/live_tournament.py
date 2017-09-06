import json
import uuid
import datetime
from flask import request, render_template, redirect, url_for, Blueprint
import models as m
from views.common import cities

bp = Blueprint('live_tournament', __name__,
               template_folder='templates/live_tournament/',
               url_prefix='live-tournament')


@bp.route("/home/")
def home():
    return render_template('live_tournament_home.html')


@bp.route("/<key>")
def get(key):
    tournament = m.LiveTournament.query.filter_by(key=key).first_or_404()
    if tournament.status == 'created':
        return redirect(url_for('.live_tournament_add_players', key=key))
    return render_template('live_tournament_home.html')


@bp.route("/create/")
def create():
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


@bp.route("/add-player/<key>/")
def add_players(key):
    tournament = m.LiveTournament.query.filter_by(key=key).first_or_404()
    if tournament.status == 'created':
        return render_template('live_tournament_add_players.html',
                               tournament=tournament,
                               cities=list(cities().values()))
    if tournament.status == 'added_players':
        return render_template('live_tournament_add_players.html',
                               tournament=tournament,
                               cities=list(cities().values()))


@bp.route("/<key>/remove-player/<int:number>")
def remove_player(key, number):
    tournament = m.LiveTournament.query.filter_by(key=key).first_or_404()
    players = [p for p in tournament.players if p['number'] != number]
    tournament._players = json.dumps(players)
    m.db.session.add(tournament)
    m.db.session.commit()
    return redirect(
        url_for('.live_tournament_add_players', key=tournament.key))


@bp.route("/<key>/add-players", methods=['GET', 'POST'])
def add_player(key):
    error = False
    tournament = m.LiveTournament.query.filter_by(key=key).first_or_404()
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
