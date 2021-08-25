from rdflib import URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL

from csum import LANGUAGE
from csum.graph import Graph


class RApplicator:
    def __init__(self, logger):
        self.logger = logger

    ##############################################
    # R1
    ##############################################
    def apply_r1(self, graph: Graph):
        """
        Applies R1 rule to the given graph
        :param graph: graph for processing
        """
        # this one is only possible, because we know relators already
        relations = self._get_relator_endurants(graph.data, graph.relators, graph.endurants)
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
        # set relators to None
        graph.clear_relators()

    def _get_relator_endurants(self, graph, relators: set, endurants: set):
        """
        Forms a dictionary with bnodes between relators-endurants
        :param graph: RDFGraph object
        :param relators: set of relators
        :param endurants: set of endurants
        :return: dictionary {relator -> {endurant -> bnode}}
        """
        result = {}
        all_nodes = relators.copy()
        all_nodes.update(endurants)
        for relator in all_nodes:
            for (_, _, bnode) in graph.triples((relator, RDFS.subClassOf, None)):
                for (_, _, endurant) in graph.triples((bnode, OWL.onClass, None)):
                    if relator not in result:
                        result[relator] = {}
                    result[relator][endurant] = bnode
                    endurants.add(endurant)
                for (_, _, endurant) in graph.triples((bnode, OWL.someValuesFrom, None)):
                    if relator not in result:
                        result[relator] = {}
                    result[relator][endurant] = bnode
                    endurants.add(endurant)
        return result

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

    ##############################################
    # R2
    ##############################################
    def apply_r2(self, graph: Graph):
        """
        Applies R2 rule to the given graph
        :param graph: graph for processing
        """
        for nonsortal in graph.nonsortals:
            base_sortal = False
            for (relation, _, _) in graph.data.triples((None, RDFS.domain, nonsortal)):
                # check for RDFS.range is endurant or datatype?!
                i = 0
                for (endurant, _, _) in graph.data.triples((None, RDFS.subClassOf, nonsortal)):
                    base_sortal = True
                    if endurant in graph.endurants:
                        self._move_connection(graph, relation, nonsortal, i, endurant)
                        i += 1
                    graph.data.remove((endurant, RDFS.subClassOf, nonsortal))
                    # if endurant in graph.nonsortals:
                    #     print("recursion on: " + endurant)
                graph.data.remove((relation, None, None))
            # remove nonsortal
            if base_sortal:
                graph.data.remove((nonsortal, None, None))
        # set nonsortals to None
        graph.clear_nonsortals()

    @staticmethod
    def _move_connection(graph, relation_name, role_name: str, idx: int, endurant):
        """
        Moves connection with relation_name to endurant as domain
        Keeps all the properties, adds role_name as comment
        :param graph: Graph object
        :param relation_name: name of the relation to be moved
        :param role_name: NonSortal role name
        :param idx: number of the relation
        :param endurant: where to move
        :return: new connection
        """
        connection = URIRef(str(relation_name) + str(idx))
        for (_, p, o) in graph.data.triples((relation_name, None, None)):
            if p == RDFS.domain:
                graph.data.add((connection, p, endurant))
            else:
                graph.data.add((connection, p, o))
        name, _ = graph.reduce_prefix(role_name)
        # is there anything better?
        graph.data.add((connection, RDFS.comment, Literal(name)))
        return connection


