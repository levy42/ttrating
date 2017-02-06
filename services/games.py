import networkx as nx
import json
import os
import models as m

GRAPH = {}
GRAPH_ALL = {}
graph_path = 'static/graph.json'
graph_all_path = 'static/graph_all.json'


def create_graphs():
    global GRAPH
    global GRAPH_ALL

    def format_graph(graph):
        return nx.DiGraph(
                [(int(k), v) for k, nodes in graph.items() for v in nodes])

    if os.path.exists(graph_path):
        with open(graph_path) as f, open(graph_all_path) as f2:
            g = json.load(f)
            g_all = json.load(f2)
            GRAPH = format_graph(g)
            GRAPH_ALL = format_graph(g_all)
            print("Graph initialized from file")
            return
    # else
    graph = {}
    graph_all = {}
    all_games = m.Game.query.all()
    for g in all_games:
        if g.opponent_id:
            if g.result:
                if not graph.get(g.player_id):
                    graph[g.player_id] = set()
                graph[g.player_id].add(g.opponent_id)

            if not graph_all.get(g.player_id):
                graph_all[g.player_id] = {}
            if not graph_all[g.player_id].get(g.opponent_id):
                graph_all[g.player_id][g.opponent_id] = 1 if g.result else -1
            else:
                graph_all[g.player_id][g.opponent_id] += 1 if g.result else -1
    for g in graph:
        graph[g] = list(graph[g])
    for g in graph_all:
        graph[g] = list(graph_all[g])

    GRAPH = format_graph(graph)
    GRAPH_ALL = format_graph(graph_all)

    with open(graph_path, 'w') as f:
        f.write(json.dumps(GRAPH))

    with open(graph_all_path, 'w') as f:
        f.write(json.dumps(GRAPH_ALL))

    print("Graph initialized")


def find_chain(player1_id, player2_id, all=False):
    if not GRAPH:
        create_graphs()
    try:
        g = GRAPH_ALL if all else GRAPH
        path = nx.dijkstra_path(g, player1_id, player2_id)
    except nx.NetworkXNoPath:
        return None
    return [m.Player.query.get(id) for id in path]


create_graphs()
