from colour import Color
from rdflib import URIRef, Graph as RDFGraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_digraph
from networkx.readwrite import json_graph

from csum import LANGUAGE, \
    LABEL_NAME, ANCESTOR_NAME, PROPERTY_NAME, \
    STROKE_SUBCLASS, STROKE_OTHER, \
    COLOUR_BASIC, COLOUR_RELATOR, COLOUR_ENDURANT1, \
    COLOUR_ENDURANT2, COLOUR_PREFIX1, COLOUR_PREFIX2


class Graph:
    SUBCLASS_LABELS = ['rdfs:subClassOf', 'rdfs:subPropertyOf', 'rdf:type']

    def __init__(self, logger):
        self.logger = logger
        self._data = None
        self._description = self._get_config_basics()
        self._bind = dict()
        self._relators = set()
        self._sortals = dict()
        self._nonsortals = dict()

    @property
    def data(self):
        return self._data

    @property
    def relators(self):
        return self._relators

    @property
    def sortals(self):
        return self._sortals.keys()

    @property
    def nonsortals(self):
        return self._nonsortals.keys()

    @property
    def endurants(self):
        endurants = set(self._sortals.keys())
        endurants.update(self._nonsortals.keys())
        return endurants

    def clear_nonsortals(self):
        self._nonsortals = dict()

    @staticmethod
    def _get_config_basics() -> dict:
        result = dict()
        result['color_endurants'] = COLOUR_ENDURANT1
        result['color_relators'] = COLOUR_RELATOR
        result['color_prefixes'] = COLOUR_PREFIX1
        return result

    ##############################################
    # Data Loading
    ##############################################
    def load_data(self, graph_data) -> bool:
        try:
            self._data = RDFGraph().parse(graph_data, format="turtle")
        except:
            self.logger.error("Not able to parse the graph")
            return False
        else:
            n_statements = len(self._data)
            self.logger.info("Loaded graph has {} statements".format(n_statements))
            self._description['origin_statements'] = n_statements
            # set up bindings of the rdf graph
            self._bind = self._set_binds()
            # set up of gufo's properties of the graph
            self._relators = self._get_relators()
            self._description['num_relators'] = len(self._relators)
            self._sortals, self._nonsortals = self._get_endurants()
            self._description['num_endurants'] = len(self._sortals) + len(self._nonsortals)
            return True

    def _set_binds(self) -> dict:
        result = dict()
        # self._data.namespaces() is a generator
        namespaces = list(self._data.namespaces())
        n = len(namespaces)
        colors = list(Color(COLOUR_PREFIX1).range_to(Color(COLOUR_PREFIX2), n))
        for (prefix, namespace), color in zip(namespaces, colors):
            ns = str(namespace)
            if ns[-1] == '#':
                ns = ns[:-1]
            result[ns] = (prefix, str(color))
        return result

    def _get_relators(self) -> set:
        results = set()
        for subj in self._data.transitive_subjects(
                URIRef('http://www.w3.org/2000/01/rdf-schema#subClassOf'),
                URIRef('http://purl.org/nemo/gufo#Relator')):
            results.add(subj)
        return results

    def _get_endurants(self) -> (dict, dict):
        sortals = dict()
        nonsortals = dict()
        colors = list(Color(COLOUR_ENDURANT1).range_to(Color(COLOUR_ENDURANT2), 3))
        for sortal_name, n in zip(['Kind', 'SubKind', 'Role', 'Phase'],
                                    [0, 1, 1, 1]):
            for subj in self._data.transitive_subjects(
                    URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'),
                    URIRef('http://purl.org/nemo/gufo#' + sortal_name)):
                if subj not in self._relators:
                    sortals[subj] = str(colors[n])
            for nonsortal_name in ['Category', 'RoleMixin', 'PhaseMixin', 'Mixin']:
                for subj in self._data.transitive_subjects(
                        URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'),
                        URIRef('http://purl.org/nemo/gufo#' + nonsortal_name)):
                    if subj not in self._relators:
                        nonsortals[subj] = str(colors[2])
        return sortals, nonsortals

    ##############################################
    # Data Visualizing
    ##############################################
    def visualize(self, original: bool, excluded: list):
        """
        Reduces graph for a proper visualization
        :param original: if True show original graph
        :param excluded: list of excluded prefixes, that should be collapsed
        :return: json-like graph structure
        """
        try:
            g = rdflib_to_networkx_digraph(self._data)
        except:
            self.logger.error("Not able to convert the graph")
            return None
        else:
            n_statements = len(g)
            self.logger.info("Graph converted to networkx with length {}".format(n_statements))
            data = json_graph.node_link_data(g)
            del data['directed']
            del data['multigraph']
            del data['graph']
            # making dictionary out of nodes
            nodes_dict = {}
            for node in data['nodes']:
                nodes_dict[node['id']] = node
                nodes_dict[node['id']]['links'] = 0
            # links and nodes processing
            data['links'] = self._links_postprocessing(original, data['links'], nodes_dict, excluded)
            data['nodes'] = self._nodes_postprocessing(original, data['nodes'], nodes_dict, data['links'])
            data['graph'] = self._make_description(self._description.copy(),
                                                   n_statements, len(data['nodes']), len(data['links']))
            return data

    ##############################################
    # PART 1: Links processing
    def _links_postprocessing(self, original: bool, links: list, nodes: dict, excluded: list) -> list:
        """
        Updates links, removes redundant
        :param original: if True show original graph
        :param links: original list of links
        :param nodes: original dictionary of nodes id -> node content
        :param excluded: list of excluded prefixes
        :return: list of links, changes in the list of nodes!
        """
        result = []
        for link in links:
            link['label'], _ = self.reduce_prefix(str(link['triples'][0][1]))
            if original:
                result.append(self._basic_link_processing(link, nodes))
            else:
                label = link['label']
                # rdfs:comment: add as property
                if label == 'rdfs:comment':
                    nodes[link['source']]['comment'] = str(link['target'])
                # rdfs:label: if basic language, then use; otherwise add as property
                elif (label == 'rdfs:label') or (label == 'rdf:label'):
                    target_lang = link['target'].language
                    if target_lang == LANGUAGE:
                        nodes[link['source']]['label'] = str(link['target'])
                    else:
                        language = '@' + target_lang if target_lang else ''
                        self._add_property(
                            nodes[link['source']], LABEL_NAME, str(link['target']) + language
                        )
                # rdfs:domain and range: include as property
                elif (label == 'rdfs:domain') or (label == 'rdfs:range'):
                    self._add_property(nodes[link['source']], label, link['target'], as_list=False)
                # if one of subclasses, more complicated logic
                elif label in self.SUBCLASS_LABELS:
                    result.extend(self._subclass_link_processing(excluded, link, nodes))
                # otherwise include as property
                else:
                    self._add_property(nodes[link['source']], label, link['target'])
        return result

    def reduce_prefix(self, name: str) -> (str, str):
        """
        From <http://purl.org/nemo/gufo#Kind> makes gufo:Kind
        :param name: full name with prefix
        :return: name with reduced prefix, colour
        """
        label = name.split('#')
        if label[0] in self._bind.keys():
            prefix = self._bind[label[0]][0]
            if len(prefix) > 0:
                prefix += ':'
            prefix += label[-1]
            return prefix, self._bind[label[0]][1]
        return label[-1], COLOUR_BASIC

    def _basic_link_processing(self, link, nodes):
        """
        Processes link for an original graph
        :param link: current link for processing
        :param nodes: dictionary of all nodes
        :return: updated link
        """
        if link['label'] in self.SUBCLASS_LABELS:
            self._update_link(
                link, nodes[link['source']], nodes[link['target']], STROKE_SUBCLASS
            )
        else:
            self._update_link(link, nodes[link['source']], nodes[link['target']])
        return link

    def _subclass_link_processing(self, excluded, link, nodes):
        """
        Processes subclass links
        :param excluded: list of excluded prefixes
        :param link: current link for processing
        :param nodes: dictionary of all nodes
        :return: list of links to be saved further
        """
        result = []
        if any('/' + s + '#' in str(link['target']) for s in excluded):
            # target node must be excluded, keep it as a property
            target, _ = self.reduce_prefix(str(link['target']))
            self._add_property(nodes[link['source']], ANCESTOR_NAME, target)
        elif (type(link['source']) is URIRef) and (type(link['target']) is URIRef):
            # keep this link, but update its properties
            self._update_link(
                link, nodes[link['source']], nodes[link['target']], STROKE_SUBCLASS
            )
            result.append(link)
        else:
            self._add_property(nodes[link['source']], link['label'], link['target'])
        return result

    @staticmethod
    def _update_link(link, source, target, stroke=STROKE_OTHER):
        """
        Modifies existing link
        :param link: object of
        :param source: from-node
        :param target: to-node
        :param stroke: stroke pattern for link
        """
        del link['triples']
        link['strokeDasharray'] = stroke
        source['links'] += 1
        target['links'] += 1

    @staticmethod
    def _add_property(node, name: str, value: str, as_list=True):
        """
        Add new property to the node as a list or an atomic value
        :param node: node to which the property will be added
        :param name: name of the property
        :param value: value of the property
        :param as_list: if true, added as [value]
        """
        if as_list:
            if name not in node:
                node[name] = []
            node[name].append(value)
        else:
            node[name] = value

    ##############################################
    # PART 2: Nodes processing
    def _nodes_postprocessing(self, original: bool, nodes: list, nodes_dict: dict, links: list) -> list:
        """
        Updates nodes, removes redundant
        :param original: if True show original graph
        :param nodes: original list of nodes
        :param nodes_dict: original dictionary of nodes id -> node content
        :param links: processed list of links
        :return: list of nodes
        """
        result = []
        for node in nodes:
            if 'label' not in node:
                node['label'], node['color'] = self.reduce_prefix(str(node['id']))
            if not original:
                if 'rdfs:domain' in node:
                    if 'rdfs:range' in node:
                        # convert this into link between nodes
                        self._domain_range(nodes_dict, links, node)
                    else:
                        # if it is domain only, then convert this into property
                        self._add_property(
                            nodes_dict[node['rdfs:domain']], PROPERTY_NAME, node['label']
                        )
                        node['domain'], _ = self.reduce_prefix(str(node['rdfs:domain']))
                        del node['rdfs:domain']
                if 'rdfs:subClassOf' in node:
                    # could be BNodes only, since others are already converted to links
                    self._bnodes_propagation(nodes_dict, node, links)
            if original or (node['links'] > 0):
                # del node['links']
                self._colour_nodes(node)
                result.append(node)
        return result

    def _domain_range(self, nodes_dict, links, node):
        """
        Creates links between range and domain
        Saves all properties
        :param nodes_dict: dictionary of nodes
        :param links: list of links
        :param node: node for processing
        :return:
        """
        props = self._other_properties(node)
        node['label'], _ = self.reduce_prefix(node['label'])
        links.append(self._create_link(
            nodes_dict, node['rdfs:domain'], node['rdfs:range'], node['label'], **props
        ))
        """
        links.append(self._create_link(
            nodes_dict, node['rdfs:range'], node['rdfs:domain'], node['label'], **props
        ))
        """

    @staticmethod
    def _other_properties(node) -> dict:
        """
        Form a dictionary of other properties of node
        :param node: node for processing
        :return: dictionary with properties
        """
        result = {}
        for key in node.keys():
            if key not in ['rdf:type', 'rdfs:domain', 'rdfs:range', 'id', 'label',
                           'links', 'owl:onProperty', 'owl:onClass', 'owl:someValuesFrom']:
                result[key] = node[key]
        return result

    def _colour_nodes(self, node):
        """
        Creates a color property for node
        :param node: node for processing
        """
        if node['id'] in self._sortals:
            node['isSortal'] = True
            node['color'] = self._sortals[node['id']]
        elif node['id'] in self._nonsortals:
            node['isNonSortal'] = True
            node['color'] = self._nonsortals[node['id']]
        elif node['id'] in self._relators:
            node['isRelator'] = True
            node['color'] = COLOUR_RELATOR
        elif 'color' not in node:
            node['color'] = COLOUR_BASIC

    @staticmethod
    def _create_link(nodes_dict, source, target, label, stroke=STROKE_OTHER, **kwargs):
        """
        Crates new link which didn't exist before
        :param nodes_dict: dictionary of all nodes
        :param source: from-node
        :param target: to-node
        :param label: label for the link
        :param stroke: stroke pattern for link
        :param kwargs: dictionary of other link's properties
        :return: link object
        """
        link = {
            'weight': 1,
            'source': source,
            'target': target,
            'label': label,
            'strokeDasharray': stroke
        }
        link.update(kwargs)
        nodes_dict[source]['links'] += 1
        nodes_dict[target]['links'] += 1
        return link

    def _bnodes_propagation(self, nodes_dict, node, links):
        """
        Propagates BNodes properties to the current node
        :param nodes_dict: dictionary of all nodes
        :param node: node for processing
        :param links: processed list of links
        """
        for n in node['rdfs:subClassOf']:
            bnode = nodes_dict[n]
            if self._is_restriction(bnode):
                prop = bnode['owl:onProperty'][0]
                label = prop if type(prop) is URIRef else nodes_dict[prop]['owl:inverseOf'][0]
                label, _ = self.reduce_prefix(label)
                target = bnode['owl:onClass'][0] if 'owl:onClass' in bnode else bnode['owl:someValuesFrom'][0]
                links.append(self._create_link(
                    nodes_dict, node['id'], target, label, **self._other_properties(bnode)
                ))
            else:
                links.append(self._create_link(
                    nodes_dict, node['id'], bnode['id'], 'rdfs:subClassOf', STROKE_SUBCLASS
                ))
        del node['rdfs:subClassOf']

    def _is_restriction(self, node) -> bool:
        """
        Checks if node is an owl:Restriction type
        :param node: bnode for checking
        :return: True is in ancestors is owl:Restriction
        """
        if 'rdf:type' in node:
            for ancestor in node['rdf:type']:
                if self.reduce_prefix(ancestor)[0] == 'owl:Restriction':
                    if (('owl:onClass' in node) or ('owl:someValuesFrom' in node)) and \
                            ('owl:onProperty' in node):
                        return True
        if ANCESTOR_NAME in node:
            for ancestor in node[ANCESTOR_NAME]:
                if ancestor == 'owl:Restriction':
                    if (('owl:onClass' in node) or ('owl:someValuesFrom' in node)) and \
                            ('owl:onProperty' in node):
                        return True
        return False

    ##############################################
    # PART 3: Graph's description generation
    @staticmethod
    def _make_description(description, n_statements, n_nodes, n_links):
        description['networkx_statements'] = n_statements
        description['num_nodes'] = n_nodes
        description['num_links'] = n_links
        return description
