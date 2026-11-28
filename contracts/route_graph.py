"""Shortest path in the released undirected source graph, not a historical journey."""
from heapq import heappop, heappush

def shortest(edges,start,end):
    adjacency={}
    for e in edges:
        a,b,w=e["from_id"],e["to_id"],e["meters"]
        adjacency.setdefault(a,[]).append((b,w,e["id"],False))
        adjacency.setdefault(b,[]).append((a,w,e["id"],True))
    if start not in adjacency or end not in adjacency:
        raise KeyError("unknown node")
    best={start:0}
    previous={}
    queue=[(0,start)]
    while queue:
        dist,node=heappop(queue)
        if dist!=best[node]: continue
        if node==end:
            steps=[]
            while node!=start:
                prior,edge,reverse=previous[node]
                steps.append({"id":edge,"from_id":prior,"to_id":node,"reversed":reverse})
                node=prior
            return {"meters":dist,"steps":steps[::-1]}
        for neighbor,w,edge,reverse in sorted(adjacency[node]):
            cost=dist+w
            if cost<best.get(neighbor,float("inf")):
                best[neighbor]=cost
                previous[neighbor]=(node,edge,reverse)
                heappush(queue,(cost,neighbor))
    return None
