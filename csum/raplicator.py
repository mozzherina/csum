from rdflib import URIRef, Namespace, Graph as RDFGraph

from csum.graph import Graph

class RApplicator:
    def __init__(self, logger):
        self.logger = logger

    def apply_r1(self, graph: Graph):
        # graph.data.bind('gufo', Namespace('http://purl.org/nemo/gufo#'))
        query = """
            SELECT DISTINCT ?relator ?endurant WHERE {
                ?relator rdfs:subClassOf gufo:Relator.
                ?relator (rdfs:subClassOf/owl:onProperty
                         |rdfs:subClassOf/owl:onProperty/owl:inverseOf) gufo:mediates.
                ?relator rdfs:subClassOf/owl:onClass ?endurant.
            }
        """
        qres = graph.data.query(query)
        for row in qres:
            print(f"{row.relator} {row.endurant}")
        return "ok"