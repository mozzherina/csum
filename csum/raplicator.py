from rdflib import URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL

from csum import LANGUAGE
from csum.graph import Graph
from csum.queries import QueriesGenerator as QG


class RApplicator:
    def __init__(self, logger):
        self.logger = logger

    def apply_r1(self, graph: Graph):
        # this one is only possible, because we know relators already
        query_all = graph.data.query(QG.get_relators())
        relations = {}
        for row in query_all:
            if row.relator not in relations:
                relations[row.relator] = {}
            relations[row.relator][row.endurant] = row.bnode
        # process relators one by one
        for relator in graph.relators:
            if relator in relations:
                mediations = list(relations[relator].keys())
                # if this relator mediates at least 2 endurants
                if len(mediations) > 1:
                    for i in range(len(mediations)):
                        for j in range(i + 1, len(mediations)):
                            self._process_endurants(
                                graph.data, relations, relator, mediations[i], mediations[j]
                            )
                    # remove relator and all bnodes from it
                    graph.data.remove((relator, None, None))
                    for r in mediations:
                       graph.data.remove((relations[relator][r], None, None))


    def _process_endurants(self, graph, relations, relator, endurant1, endurant2):
        connection = self._get_connection(graph, endurant1, endurant2)
        if not connection:
            # No connection between {endurant1} and {endurant2}
            connection = self._create_connection(graph, relator, endurant1, endurant2)
        # There is a connection between {endurant1} and {endurant2}
        # need to take care about cardinality
        for endurant in [endurant1, endurant2]:
            bnode = relations[endurant][relator]
            self._move_cardinality(graph, bnode, connection)
            graph.remove((endurant, None, bnode))
            graph.remove((bnode, None, None))
        """
            for (_, relation, _) in graph.triples((bnode1, None, relator)):
                graph.add((bnode1, relation, endurant2))
                graph.remove((bnode1, relation, relator))
            bnode2 = relations[endurant2][relator]
            for (_, relation, _) in graph.triples((bnode2, None, relator)):
                graph.add((bnode2, relation, endurant1))
                graph.remove((bnode2, relation, relator))
        """

    @staticmethod
    def _create_connection(graph, name: str, endurant1, endurant2):
        connection = URIRef(name.lower())
        graph.add((connection, RDFS.label, Literal(name, lang=LANGUAGE)))
        graph.add((connection, RDF.type, OWL.ObjectProperty))
        graph.add((connection, RDFS.domain, endurant1))
        graph.add((connection, RDFS.range, endurant2))
        return connection

    @staticmethod
    def _move_cardinality(graph, from_node, to_node):
        for cardinality in [OWL.qualifiedCardinality,
                            OWL.minQualifiedCardinality,
                            OWL.maxQualifiedCardinality]:
            for (s, p, o) in graph.triples((from_node, cardinality, None)):
                graph.add((to_node, p, o))

    @staticmethod
    def _get_connection(graph, endurant1, endurant2):
        """
        Returns a node, that connects endurants
        :param graph: RDFGraph object
        :param endurant1: first endurant
        :param endurant2: second endurant
        :return: a connection node if exists
        """
        for (s, _, _) in graph.triples((None, RDFS.domain, endurant1)):
            for (s, _, _) in graph.triples((s, RDFS.range, endurant2)):
                return s
        for (s, _, _) in graph.triples((None, RDFS.domain, endurant2)):
            for (s, _, _) in graph.triples((s, RDFS.range, endurant1)):
                return s
        return None



