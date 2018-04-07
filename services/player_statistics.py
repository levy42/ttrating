from models import Game


def calculate_game_stability(player):
    player_games = Game.query.filter_by(player_id=player.id).order_by('date')
    stability = 0
    for g in player_games:
        g.
