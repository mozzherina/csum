from rdflib import URIRef, Namespace, Graph as RDFGraph
import rdflib.plugins.sparql as sparql
from rdflib.namespace import RDFS

from csum.graph import Graph

class RApplicator:
    def __init__(self, logger):
        self.logger = logger

    def apply_r1(self, graph: Graph):
        # this one is only possible, because we know relators already
        query = """
            SELECT ?relator ?bnode ?endurant WHERE {
                ?relator rdfs:subClassOf ?bnode.
                ?bnode owl:onClass ?endurant.
            }
            """
        qres_all = graph.data.query(query)
        relations = {}
        for row in qres_all:
            if row.relator not in relations:
                relations[row.relator] = {}
            relations[row.relator][row.endurant] = row.bnode

        for relator in graph.relators:
            if relator in relations:
                mediations = list(relations[relator].keys())
                if len(mediations) > 1:
                    for i in range(len(mediations)):
                        endurant1 = mediations[i]
                        for j in range(i + 1, len(mediations)):
                            endurant2 = mediations[j]
                            # speed? query?
                            if self._check_connection(graph.data, endurant1, endurant2) or \
                                    self._check_connection(graph.data, endurant2, endurant1):
                                #print(f"Connection between {endurant1} and {endurant2}")
                                bnode1 = relations[relator][endurant1]
                                bnode2 = relations[relator][endurant2]
                                graph.data.update(self._generate_update(),
                                                  initBindings={'from': bnode1, 'old': relator, 'to': endurant2})
                                graph.data.update(self._generate_update(),
                                                  initBindings={'from': bnode2, 'old': relator, 'to': endurant1})
                            else:
                                print(f"No connection between {endurant1} and {endurant2}")
                for r in mediations:
                    graph.data.remove((relations[relator][r], None, None))
                graph.data.remove((relator, None, None))

    @staticmethod
    def _check_connection(g, endurant1, endurant2):
        for (s, _, _) in g.triples((None, RDFS.domain, endurant1)):
            for (s, _, _) in g.triples((s, RDFS.range, endurant2)):
                return True
        return False

    @staticmethod
    def _generate_update():
        s = """
            DELETE { ?from owl:onClass ?old } 
            INSERT { ?from owl:onClass ?to } 
            WHERE { ?from owl:onClass ?old }
            """
        return s
