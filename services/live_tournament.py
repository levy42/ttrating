import random
import math


class Type:
    OLIMPIC = 1
    MINUS_TWO = 2


class Tournament(object):
    def __init__(self, type, judge):
        self.type = type


class Cell(object):
    def __init__(self, number, number_up, number_down):
        self.number = number
        self.number_up = number_up
        self.number_down = number_down
        self.player1_number = None
        self.player2_number = None

    def __repr__(self):
        return str((self.number, self.number_up, self.number_down))


def olimpic_grid(n):
    grid = {}  # cells: Cell
    i = 0  # cell counter
    j = n / 2 + 1
    while i < n - 2:
        grid[i + 1] = Cell(i + 1, j, None)
        i += 1
        j += 0 if i % 2 else 1
    grid[n - 3] = Cell(n - 3, n - 1, n)
    grid[n - 2] = Cell(n - 2, n - 1, n)
    grid[n - 1] = Cell(n - 1, None, None)
    grid[n] = Cell(n, None, None)
    return grid


class GroupScheme():
    def __init__(self, **kwargs):
        self.play_2_final = True
        self.group_stage = True
        self.player_per_group = kwargs.get('player_per_group', 8)
        self.player_out_from_group = kwargs.get('player_out_from_group', 2)
        self.total_player_out = 0

    def add_result(self, tournament):
        tournament.games.append

    def create_groups(self, tournament):
        group_nuber = math.ceil(len(tournament.players) /
                                self.player_per_group)
        _players = [number for number, p in
                    sorted(tournament.players.items(),
                           key=lambda x: x[1]['rating'],
                           reverse=True)]
        self.groups = [[] for i in range(1, group_nuber + 1)]
        i = 0
        for step in range(0, self.player_per_group):
            start = step * group_nuber
            end = start + group_nuber
            if end >= len(_players):
                end = len(_players) - 1
            copy = _players[start:end]
            random.shuffle(copy)
            _players[start: end] = copy
            for g in self.groups:
                if i < len(_players):
                    g.append(_players[i])
                    i += 1
        return self.groups

    def create_final(self, tournament):
        pass


class A(object):
    players = {i: {'number': i, 'rating': random.randint(0, 115)}
               for i in range(1, 123)}
    pass
