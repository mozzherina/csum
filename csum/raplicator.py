from rdflib import URIRef, Literal, BNode
from rdflib.collection import Collection
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
        # update relators
        graph.reset_relators()

    @staticmethod
    def _get_relator_endurants(graph, relators: set, endurants: set):
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
        :param relations: dict of all relations
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
        Creates connections between endurant1 and endurant2
        by defining a node with the corresponding range and domain
        :param graph: RDFGraph object
        :param name: label
        :param endurant1: first endurant
        :param endurant2: second endurant
        """
        connection = URIRef(name.lower())
        graph.add((connection, RDFS.label, Literal(name, lang=LANGUAGE)))
        graph.add((connection, RDF.type, OWL.ObjectProperty))
        # or vice versa
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
    # Additional functions, to be used by R2-R4 rules
    ##############################################
    @staticmethod
    def _get_super_classes(graph) -> set:
        """
        Forms set of classes that have subclasses
        :param graph: graph for processing
        :return: set of superclasses
        """
        result = set()
        for sortal in graph.sortals:
            for (_, _, o) in graph.data.triples((None, RDFS.subClassOf, sortal)):
                result.add(o)
        return result

    @staticmethod
    def _get_sub_classes(graph, name) -> set:
        """
        Forms set of subclasses
        :param graph: graph for processing
        :param name: name of superclass
        :return: set of superclasses
        """
        result = set()
        for (endurant, _, _) in graph.data.triples((None, RDFS.subClassOf, name)):
            if endurant in graph.endurants:
                result.add(endurant)
        return result

    @staticmethod
    def _update_comment(graph, connection, role_name: str):
        """
        Updates existing comment with role name
        :param graph: Graph object
        :param connection: URIRef that exists or was created
        :param role_name: to be added as comment
        """
        comment = ''
        for (_, _, c) in graph.data.triples((connection, RDFS.comment, None)):
            comment = c
            graph.data.remove((connection, RDFS.comment, c))
        name, _ = graph.reduce_prefix(role_name)
        name = str(comment) + '-' + name if comment else name
        graph.data.add((connection, RDFS.comment, Literal(name)))

    def _move_relation(self, graph, relation, role, target):
        """
        Moves relation to target as domain or range
        Keeps all the properties, adds role as comment
        :param graph: Graph object
        :param relation: Relation to be moved
        :param role: NonSortal role name
        :param target: where to move
        :return: new connection
        """
        for (s, p, o) in graph.data.triples((relation, None, None)):
            if ((p == RDFS.domain) or (p == RDFS.range)) and (o == role):
                graph.data.remove((s, p, o))
                graph.data.add((s, p, target))
                # TODO: is there anything better for a role?
                self._update_comment(graph, relation, str(role))

    def _create_relation(self, graph, relation, idx, role, target):
        """
        Duplicates relation to target as domain or range
        Keeps all the properties, adds role as comment
        :param graph: Graph object
        :param relation: Relation to be duplicated
        :param idx: Index of the created relation
        :param role: Role name
        :param target: where to move
        """
        connection = URIRef(str(relation) + str(idx))
        for (_, p, o) in graph.data.triples((relation, None, None)):
            if ((p == RDFS.domain) or (p == RDFS.range)) and (o == role):
                graph.data.add((connection, p, target))
            else:
                graph.data.add((connection, p, o))
        # TODO: is there anything better for a role?
        self._update_comment(graph, connection, str(role))

    ##############################################
    # R2
    ##############################################
    def apply_r2(self, graph: Graph):
        """
        Applies R2 rule to the given graph
        :param graph: graph for processing
        """
        for nonsortal in graph.nonsortals:
            endurants = self._get_sub_classes(graph, nonsortal)
            if endurants:
                for predicate in [RDFS.domain, RDFS.range]:
                    for (relation, _, _) in graph.data.triples((None, predicate, nonsortal)):
                        # TODO: check for RDFS.range is endurant or datatype?!
                        for endurant, i in zip(endurants, range(len(endurants))):
                            self._create_relation(graph, relation, i, nonsortal, endurant)
                        graph.data.remove((relation, None, None))
                for endurant in endurants:
                    graph.data.remove((endurant, RDFS.subClassOf, nonsortal))
                # remove nonsortal
                graph.data.remove((nonsortal, None, None))
        # nonsortals should be updated
        graph.reset_endurants()

    ##############################################
    # R3
    ##############################################
    def apply_r3(self, graph: Graph):
        """
        Applies R3 rule to the given graph
        :param graph: graph for processing
        """
        roles_tree = dict()
        graph.get_disjoint_by_name('Role', roles_tree)
        not_seen = set(roles_tree.keys())
        for kind in roles_tree.keys():
            if kind in not_seen:
                self._moves_to_ancestor(graph, roles_tree, not_seen, kind)
        # reset sortals
        # TODO: fix an error, removes organization?
        graph.reset_endurants()

    def _moves_to_ancestor(self, graph, roles_tree, not_seen, ancestor):
        for descendant in roles_tree[ancestor]['Role']:
            if descendant in not_seen and descendant in roles_tree.keys():
                self._moves_to_ancestor(graph, roles_tree, not_seen, descendant)
            for predicate in [RDFS.domain, RDFS.range]:
                for (relation, _, _) in graph.data.triples((None, predicate, descendant)):
                    self._move_relation(graph, relation, descendant, ancestor)
            graph.data.remove((descendant, None, None))
        not_seen.remove(ancestor)

    ##############################################
    # R4
    ##############################################
    def apply_r4(self, graph: Graph):
        """
        Applies R4 rule to the given graph
        :param graph: graph for processing
        """
        superclasses = self._get_super_classes(graph)
        disjoints = dict()
        graph.get_disjoint_by_name('SubKind', disjoints)
        graph.get_disjoint_by_name('Phase', disjoints)
        for kind in disjoints.keys():
            self._process_kind(graph, kind, disjoints, superclasses)

    def _process_kind(self, graph, key, tree, superclasses):
        # this key was already processed
        if key not in superclasses:
            return
        # print("working item is", key)
        for role in ['Phase', 'SubKind']:
            if role in tree[key]:
                for r in tree[key][role]:
                    if r in superclasses:
                        self._process_kind(graph, r, tree, superclasses)
                        print("removing from superclasses", r)
                        # superclasses.remove(r)
                    for predicate in [RDFS.domain, RDFS.range]:
                        for (relation, _, _) in graph.data.triples((None, predicate, r)):
                            print("move from ", r, " to ", key)
                            self._move_relation(graph, relation, r, key)
                print("create enumeration to ", key, " namely ", tree[key][role])
                enumeration = URIRef(str(key) + "Enumeration")
                graph.data.add((enumeration, RDF.type, RDF.List))
                prev = RDF.nil
                for alt in tree[key][role]:
                    listName = BNode()
                    graph.data.add((listName, RDF.first, Literal(str(alt))))
                    graph.data.remove((alt, None, None))
                    graph.data.add((listName, RDF.rest, prev))
                    prev = listName
                # c = Collection(graph.data, prev)
                graph.data.add((enumeration, OWL.equivalentClass, prev))
                connection = URIRef(str(key) + "EnumConn")
                graph.data.add((connection, RDF.type, OWL.ObjectProperty))
                graph.data.add((connection, RDFS.domain, key))
                graph.data.add((connection, RDFS.range, enumeration))
        print("removing ", key)
        superclasses.remove(key)
        # graph.data.remove((key, None, None))



