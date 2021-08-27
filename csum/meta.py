import copy

from csum.graph import Graph
from csum.raplicator import RApplicator


class MetaGraph:
    def __init__(self, logger):
        self.logger = logger
        self.data = None
        self._state = 0
        self._original = False
        self._excluded = []
        self._rules_applicator = RApplicator(logger)

    def load_data(self, graph_data, original: bool, excluded: list):
        graph = Graph(self.logger)
        if graph.load_data(graph_data):
            self.data = {0: graph}
            self._state = 0
            self._original = original
            self._excluded = excluded
            return True
        return False

    def visualize(self):
        if self.data:
            if self._state in self.data:
                return self.data[self._state].visualize(self._original, self._excluded)

    def plus(self):
        if self._state + 1 in self.data:
            self._state += 1
        elif self._state + 1 > 4:
            self.logger.info("No further zoom-in is possible")
        else:
            self._state += 1
            self.data[self._state] = copy.deepcopy(self.data[self._state - 1])
            if self._state == 1:
                self._rules_applicator.apply_r1(self.data[self._state])
            if self._state == 2:
                self._rules_applicator.apply_r2(self.data[self._state])
            if self._state == 3:
                self._rules_applicator.apply_r3(self.data[self._state])
            if self._state == 4:
                self._rules_applicator.apply_r4(self.data[self._state])
        return self.visualize()

    def minus(self):
        if self._state - 1 in self.data:
            self._state -= 1
        else:
            self.logger.info("No further zoom-out is possible")
        return self.visualize()
