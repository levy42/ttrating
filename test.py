def bfs(graph, start, end):
    i = 0
    # maintain a queue of paths
    queue = []
    # push the first path into the queue
    queue.append([start])
    while queue:
        # get the first path from the queue
        path = queue.pop(0)
        # get the last node from the path
        node = path[-1]
        # path found
        if node == end:
            return path
        i += 1
        # enumerate all adjacent nodes, construct a new path and push it into the queue
        for adjacent in graph.get(node, []):
            new_path = list(path)
            new_path.append(adjacent)
            queue.append(new_path)
            i += 1
    print(i)


import time
from igraph import *
import json

with open('static/graph.json') as f:
    g = json.load(f)
print('b')
graph = Graph(edges=[(int(v), a) for v in g.keys() for a in g[v]])
time.sleep(20)
print()
print(graph.cohesion(1201, 14))
