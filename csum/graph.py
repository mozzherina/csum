from rdflib import URIRef, BNode, Literal, Graph as RDFGraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_digraph
from networkx.readwrite import json_graph
from colour import Color

from csum import LANGUAGE, \
    LABEL_NAME, ANCESTOR_NAME, PROPERTY_NAME, \
    STROKE_SUBCLASS, STROKE_RDFTYPE, \
    COLOUR_BASIC, COLOUR_RELATOR, COLOUR_ENDURANT1, \
    COLOUR_ENDURANT2, COLOUR_PREFIX1, COLOUR_PREFIX2


class Graph:
    def __init__(self, logger):
        self.logger = logger
        self._data = None
        self._description = self._get_config_basics()
        self._bind = dict()
        self._relators = set()
        self._endurants = dict()

    @property
    def data(self):
        return self._data

    @staticmethod
    def _get_config_basics() -> dict:
        result = dict()
        result['color_endurants'] = COLOUR_ENDURANT1
        result['color_relators'] = COLOUR_RELATOR
        result['color_prefixes'] = COLOUR_PREFIX1
        return result

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
            self._bind = dict()
            namespaces = list(self._data.namespaces())
            n = len(namespaces)
            colors = list(Color(COLOUR_PREFIX1).range_to(Color(COLOUR_PREFIX2), n))
            for (prefix, namespace), color in zip(namespaces, colors):
                ns = str(namespace)
                if ns[-1] == '#':
                    ns = ns[:-1]
                self._bind[ns] = (prefix, str(color))
            # set up of gufo's properties of the graph
            self._relators = self._get_relators()
            self._endurants = self._get_endurants()
            return True

    def _get_relators(self):
        results = set()
        for subj in self._data.transitive_subjects(
                URIRef('http://www.w3.org/2000/01/rdf-schema#subClassOf'),
                URIRef('http://purl.org/nemo/gufo#Relator')):
            results.add(subj)
        return results

    def _get_endurants(self):
        results = dict()
        colors = list(Color(COLOUR_ENDURANT1).range_to(Color(COLOUR_ENDURANT2), 3))
        for endurant_name, n in zip(['Kind', 'SubKind', 'Role', 'Phase', 'Category',
                                     'RoleMixin', 'PhaseMixin', 'Mixin'],
                                    [0, 1, 1, 1, 1, 2, 2, 2]):
            for subj in self._data.transitive_subjects(
                    URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'),
                    URIRef('http://purl.org/nemo/gufo#' + endurant_name)):
                if subj not in self._relators:
                    results[subj] = str(colors[n])
        return results

    def visualize(self, original: bool, excluded: list):
        """
        Reduces graph for a proper visualization
        :param original: show original graph
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
            self._description['networkx_statements'] = n_statements
            data = json_graph.node_link_data(g)
            del data['directed']
            del data['multigraph']
            del data['graph']
            if not original:
                # making dictionary out of nodes
                nodes_dict = {}
                for node in data['nodes']:
                    nodes_dict[node['id']] = node
                    nodes_dict[node['id']]['links'] = 0
                data['links'] = self._links_postprocessing(data['links'], nodes_dict, excluded)
                data['nodes'] = self._nodes_postprocessing(data['nodes'], nodes_dict, data['links'])
            # data['graph'] = self._make_description()
            return data

    def _links_postprocessing(self, links: list, nodes: dict, excluded: list) -> list:
        """
        Updates links, removes redundant
        :param links: original list of links
        :param nodes: original dictionary of nodes id -> node content
        :param excluded: list of excluded prefixes
        :return: list of links, changes in the list of nodes!
        """
        result = []
        for link in links:
            label, link['color'] = self._reduce_prefix(str(link['triples'][0][1]))
            link['label'] = label
            # rdfs:comment: add as property
            if label == 'rdfs:comment':
                nodes[link['source']]['comment'] = str(link['target'])
            # rdfs:label: if basic language, then use; otherwise add as property
            elif (label == 'rdfs:label') or (label == 'rdf:label'):
                if hasattr(link['target'], 'language'):
                    if link['target'].language == LANGUAGE:
                        nodes[link['source']]['label'] = str(link['target'])
                else:
                    other_label = str(link['target']) + '@' + link['target'].language
                    self._add_property(nodes[link['source']], LABEL_NAME, other_label)
            # rdfs:subclass or subproperty or type:
            elif (label == 'rdfs:subClassOf') or (label == 'rdfs:subPropertyOf') or \
                    (label == 'rdf:type'):
                if any('/' + s + '#' in str(link['target']) for s in excluded):
                    # target node should be excluded, keep it as a property
                    self._add_property(
                        nodes[link['source']], ANCESTOR_NAME, self._reduce_prefix(str(link['target']))[0]
                    )
                elif (type(link['source']) is URIRef) and (type(link['target']) is URIRef):
                    # keep this link, but update its properties
                    result.append(self._update_link(
                        link, nodes[link['source']], nodes[link['target']], STROKE_SUBCLASS
                    ))
                elif type(link['target']) is BNode:
                    self._add_property(nodes[link['source']], label, link['target'])
                elif type(link['source']) is BNode:
                    self._add_property(
                        nodes[link['source']], ANCESTOR_NAME, self._reduce_prefix(str(link['target']))[0]
                    )
                else:
                    result.append(self._update_link(
                        link, nodes[link['source']], nodes[link['target']], STROKE_RDFTYPE
                    ))
            # rdfs:domain and range: include as property
            elif (label == 'rdfs:domain') or (label == 'rdfs:range'):
                self._add_property(nodes[link['source']], label, link['target'], as_list=False)
            # otherwise include as property
            else:
                self._add_property(nodes[link['source']], label, link['target'])
        return result

    def _reduce_prefix(self, name: str) -> (str, str):
        """
        From <http://purl.org/nemo/gufo#Kind> makes gufo:Kind
        :param name: full name with prefix
        :return: name with reduced prefix, colour
        """
        label = name.split('#')
        if label[0] in self._bind.keys():
            prefix = self._bind[label[0]][0] + ':' + label[-1]
            return prefix, self._bind[label[0]][1]
        return label[-1], COLOUR_BASIC

    @staticmethod
    def _add_property(node, name: str, value: str, as_list=True):
        """
        Add new property to the node as a list or an atomic value
        :param node: node to which the property will be added
        :param name: name of the property
        :param value: value of the property
        :param as_list: if true, added as [value]
        :return: updated node
        """
        if as_list:
            if name not in node:
                node[name] = []
            node[name].append(value)
        else:
            node[name] = value

    @staticmethod
    def _update_link(link, source, target, stroke=0):
        """
        Updates existing link
        :param link: object of
        :param source: from-node
        :param target: to-node
        :param stroke: stroke pattern for link
        :return: updated link
        """
        del link['triples']
        link['strokeDasharray'] = stroke
        source['links'] += 1
        target['links'] += 1
        return link

    @staticmethod
    def _create_link(nodes_dict, source, target, label, stroke=0, **kwargs):
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

    def _nodes_postprocessing(self, nodes: list, nodes_dict: dict, links: list) -> list:
        """
        Updates nodes, removes redundant
        :param nodes: original list of nodes
        :param nodes_dict: original dictionary of nodes id -> node content
        :param links: processed list of links
        :return: list of nodes
        """
        result = []
        for node in nodes:
            if 'label' not in node:
                node['label'], node['color'] = self._reduce_prefix(str(node['id']))
            if 'rdfs:domain' in node:
                if 'rdfs:range' in node:
                    # convert this into link between nodes
                    links.append(self._create_link(
                        nodes_dict, node['rdfs:domain'], node['rdfs:range'], node['label']
                    ))
                    links.append(self._create_link(
                        nodes_dict, node['rdfs:range'], node['rdfs:domain'], node['label']
                    ))
                else:
                    # if it is domain only, then convert this into property
                    self._add_property(
                        nodes_dict[node['rdfs:domain']], PROPERTY_NAME, node['label']
                    )
                    node['domain'] = self._reduce_prefix(str(node['rdfs:domain']))[0]
                    del node['rdfs:domain']
            if 'rdfs:subClassOf' in node:
                # could be BNode only, since others are already converted to links
                for n in node['rdfs:subClassOf']:
                    bnode = nodes_dict[n]
                    prop = bnode['owl:onProperty'][0]
                    label = prop if type(prop) is URIRef else nodes_dict[prop]['owl:inverseOf'][0]
                    label, color = self._reduce_prefix(label)
                    target = bnode['owl:onClass'][0] if 'owl:onClass' in bnode else bnode['owl:someValuesFrom'][0]
                    additional = {'color': color}
                    additional.update(self._get_cardinality(bnode))
                    links.append(self._create_link(
                        nodes_dict, node['id'], target, label, **additional
                    ))
                del node['rdfs:subClassOf']
            if node['links'] > 0: # (type(node['id']) is URIRef) and
                # del node['links']
                self._colour_nodes(node)
                result.append(node)
        return result

    @staticmethod
    def _get_cardinality(node) -> dict:
        result = {}
        if 'owl:qualifiedCardinality' in node:
            result['cardinality'] = node['owl:qualifiedCardinality'][0]
        if 'owl:minQualifiedCardinality' in node:
            result['minCardinality'] = node['owl:minQualifiedCardinality'][0]
        return result

    def _colour_nodes(self, node):
        if 'color' not in node:
            if node['id'] in self._endurants:
                node['isEndurant'] = True
                node['color'] = self._endurants[node['id']]
            if node['id'] in self._relators:
                node['isRelator'] = True
                node['color'] = COLOUR_RELATOR
