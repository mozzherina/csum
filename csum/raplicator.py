from rdflib import URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL

from csum import LANGUAGE
from csum.graph import Graph
from csum.queries import QueriesGenerator as QG


class RApplicator:
    def __init__(self, logger):
        self.logger = logger

    def apply_r1(self, graph: Graph):
        """
        Applies R1 rule to the given graph
        :param graph: graph for processing
        """
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
                                graph.data, relations, relator, mediations[i], mediations[j], str(i)+str(j)
                            )
                    # remove relator and all bnodes from it
                    graph.data.remove((relator, None, None))
                    for r in mediations:
                       graph.data.remove((relations[relator][r], None, None))

    def _process_endurants(self, graph, relations, relator, endurant1, endurant2, rname: str):
        """
        Main function for processing relator-endurant2-endurant2
        :param graph: RDFGraph object
        :param relations: results of the query
        :param relator: relator object
        :param endurant1: first of the endurant objects
        :param endurant2: second of the endurant objects
        :param rname: string to be added to the name at the end (for rewriting issues)
        """
        connection = self._get_connection(graph, endurant1, endurant2)
        if not connection:
            # No connection between {endurant1} and {endurant2}
            connection = self._create_connection(graph, str(relator) + rname, endurant1, endurant2)
        # There is a connection between {endurant1} and {endurant2}
        for endurant in [endurant1, endurant2]:
            bnode1 = relations[endurant][relator]
            bnode2 = relations[relator][endurant]
            self._move_cardinality(graph, bnode1, connection)
            self._move_cardinality(graph, bnode2, connection)
            graph.remove((endurant, None, bnode1))
            graph.remove((bnode1, None, None))

    @staticmethod
    def _get_connection(graph, endurant1, endurant2):
        """
        Returns a node, that connects endurants if ther is any
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

    @staticmethod
    def _create_connection(graph, name: str, endurant1, endurant2):
        """
        Creates connection between endurant1 and endurant2
        by defining a node with the corresponding range and domain
        :param graph: RDFGraph object
        :param name: label
        :param endurant1: first endurant
        :param endurant2: second endurant
        """
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





