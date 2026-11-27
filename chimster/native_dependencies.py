"""Cycle-safe dependency traversal with explicit incomplete coverage."""
from collections import defaultdict, deque

class Dependencies:
    def __init__(self, edges, indexed, opaque=()):
        self.forward=defaultdict(set)
        self.reverse=defaultdict(set)
        self.indexed=set(indexed)
        self.opaque=set(opaque)
        for owner,target in edges:
            self.forward[owner].add(target)
            self.reverse[target].add(owner)

    def closure(self, roots, reverse=False):
        graph=self.reverse if reverse else self.forward
        seen=set(roots)
        queue=deque(seen)
        while queue:
            for target in graph.get(queue.popleft(),()):
                if target not in seen:
                    seen.add(target)
                    queue.append(target)
        unknown=seen-self.indexed
        opaque=(self.opaque if reverse else seen & self.opaque)
        return {"reachable":seen,"unindexed":unknown,"opaque":opaque,
                "complete":not unknown and not opaque and not reverse}
