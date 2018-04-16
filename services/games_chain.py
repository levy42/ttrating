"""
Module provide searching for "chain of wins" between two player.
Example: player1 - 'Bob', player2 - 'John'
Bob never won John, but Bob won Bill and Bill won John,
so the result would be Bob -> Bill -> John.
Potentially even very weak player would have such "chain of wins" for best
players:
    <some_player> -> <player1> -> <player2> ... <playerN>.
Module uses `networkx` with Dijkstra search. It is a real memory devourer...
In order not to compile json data each time you restart the app, it uses
compiled json file witch is initialized if it`s doesn`t exist.
"""
import sys
import networkx as nx
import json
import os
import models as m
from flask import current_app

GRAPH = {}
GRAPH_ALL = {}
graph_path = 'static/graph.json'
graph_all_path = 'static/graph_all.json'


def update_graphs():
    current_app.logger.info('Updating Game chain Graphs:')
    graph = {}
    graph_all = {}
    games_iter = m.Game.query.paginate(per_page=10000, page=1)
    pages = games_iter.pages
    all_games = games_iter.items
    sys.stdout.write('Progress: 0 %')
    for page in range(2, pages + 1):
        for g in all_games:
            if g.opponent_id:
                if g.result:
                    if not graph.get(g.player_id):
                        graph[g.player_id] = set()
                    graph[g.player_id].add(g.opponent_id)

                if not graph_all.get(g.player_id):
                    graph_all[g.player_id] = {}
                if not graph_all[g.player_id].get(g.opponent_id):
                    graph_all[g.player_id][
                        g.opponent_id] = 1 if g.result else -1
                else:
                    graph_all[g.player_id][
                        g.opponent_id] += 1 if g.result else -1
        all_games = m.Game.query.paginate(per_page=10000, page=page).items
        sys.stdout.write(f'\rProgress: {(page-1)/pages*100:.3} %')
    for g in graph:
        graph[g] = list(graph[g])
    for g in graph_all:
        graph_all[g] = [p for p, s in graph_all[g].items() if s > 0]

    with open(graph_path, 'w') as f:
        f.write(json.dumps(graph))

    with open(graph_all_path, 'w') as f:
        f.write(json.dumps(graph_all))

    sys.stdout.write('\rProgress: 100 %\n')
    current_app.logger.info("Graph initialized.")


def format_graph(graph):
    return nx.DiGraph(
        [(int(k), v) for k, nodes in graph.items() for v in nodes])


def init_nx():
    global GRAPH
    global GRAPH_ALL

    if os.path.exists(graph_path):
        with open(graph_path) as f, open(graph_all_path) as f2:
            g = json.load(f)
            g_all = json.load(f2)
            GRAPH = format_graph(g)
            GRAPH_ALL = format_graph(g_all)
            current_app.logger.info('Graph initialized from file')
    else:
        raise Exception('Failed to load games chain graph. No such file')


def find_chain(player1_id, player2_id, all=False):
    if not GRAPH:
        init_nx()
    try:
        g = GRAPH_ALL if all else GRAPH
        path = nx.dijkstra_path(g, player1_id, player2_id)
    except nx.NetworkXNoPath:
        return None
    return [m.Player.query.get(id) for id in path]
