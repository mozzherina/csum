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
                relations[row.relator] = []
            relations[row.relator].append((row.endurant, row.bnode))

        for relator in graph.relators:
            qres = graph.data.query(query, initBindings={'relator': relator})
            mediations = []
            for row in qres:
                if row.endurant in graph.endurants:
                    mediations.append(row.endurant)
            if len(mediations) > 1:
                for i in range(len(mediations)):
                    endurant1 = mediations[i]
                    for j in range(i + 1, len(mediations)):
                        endurant2 = mediations[j]
                        # speed? query?
                        s1 = self._check_connection(graph.data, endurant1, endurant2)
                        s2 = self._check_connection(graph.data, endurant2, endurant1)
                        s = s1 if s1 else s2
                        if s:
                            print(f"Connection between {endurant1} and {endurant2}")
                            # delete everything
                            # Change type of <y:> from <c:> to <d:>
                            graph.data.update("""
                                     DELETE { <y:> a <c:> }
                                     INSERT { <y:> a <d:> }
                                     WHERE { <y:> a <c:> }
                                     """)
                        else:
                            print(f"No connection between {endurant1} and {endurant2}")

    def _check_connection(self, g, endurant1, endurant2):
        for (s, _, _) in g.triples((None, RDFS.domain, endurant1)):
            for (s, _, _) in g.triples((s, RDFS.range, endurant2)):
                return s
