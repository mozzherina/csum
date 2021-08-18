from rdflib import URIRef, BNode, Literal, Graph as RDFGraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_digraph
from networkx.readwrite import json_graph
from colour import Color

from csum import LANGUAGE, EXCLUDED_PREFIX, SUBCLASS_STROKE, \
    RDFTYPE_STROKE, LABEL_NAME, ANCESTOR_NAME, PROPERTY_NAME


class Graph:
    def __init__(self, logger):
        self.logger = logger
        self._bind = None
        self._data = None
        self._relators = None
        self._endurants = None

    @property
    def data(self):
        return self._data

    def load_data(self, graph_data) -> bool:
        try:
            self._data = RDFGraph().parse(graph_data, format="turtle")
        except:
            self.logger.error("Not able to parse the graph")
            return False
        else:
            self.logger.info("Loaded graph has {} statements".format(len(self._data)))
            # set up bindings of the rdf graph
            self._bind = {}
            for prefix, namespace in self._data.namespaces():
                ns = str(namespace)
                if ns[-1] == '#':
                    ns = ns[:-1]
                self._bind[ns] = prefix
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
        results = set()
        for endurant_name in ['Kind', 'SubKind', 'Role', 'Phase',
                              'RoleMixin', 'PhaseMixin', 'Mixin', 'Category']:
            for subj in self._data.transitive_subjects(
                    URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'),
                    URIRef('http://purl.org/nemo/gufo#' + endurant_name)):
                results.add(subj)
        results.difference_update(self._relators)
        return results

    def visualize(self):
        try:
            g = rdflib_to_networkx_digraph(self._data)
        except:
            self.logger.error("Not able to convert the graph")
            return None
        else:
            self.logger.info("Graph converted to networkx with length {}".format(len(g)))
            data = json_graph.node_link_data(g)
            del data['directed']
            del data['multigraph']
            del data['graph']
            # making dictionary out of nodes
            nodes_dict = {}
            for node in data['nodes']:
                nodes_dict[node['id']] = node
                nodes_dict[node['id']]['links'] = 0
            # links processing, removing redundant
            data['links'] = self._links_postprocessing(data['links'], nodes_dict)
            # nodes processing, adding additional links
            data['nodes'] = self._nodes_postprocessing(data['nodes'], nodes_dict, data['links'])
            return data

    def _links_postprocessing(self, links: list, nodes: dict) -> list:
        """
        Updates links, removes redundant
        :param links: original list of links
        :param nodes: original dictionary of nodes id -> node content
        :return: list of links, changes list of nodes!
        """
        result = []
        for link in links:
            link['label'] = self._reduce_prefix(str(link['triples'][0][1]))
            # rdfs:comment: add as property
            if link['label'] == 'rdfs:comment':
                nodes[link['source']]['comment'] = str(link['target'])
            # rdfs:label: if basic language, then use; otherwise add as property
            elif link['label'] == 'rdfs:label':
                if link['target'].language == LANGUAGE:
                    nodes[link['source']]['label'] = str(link['target'])
                else:
                    self._add_property(nodes[link['source']], LABEL_NAME,
                                       str(link['target']) + '@' + link['target'].language)
            # rdfs:subclass or subproperty:
            # if target is URI, then save link
            # if target is BNode, then include in properties
            elif (link['label'] == 'rdfs:subClassOf') or (link['label'] == 'rdfs:subPropertyOf'):
                if type(link['target']) is URIRef: # type(link['source']) is URIRef and
                    result.append(self._update_link(link, nodes[link['source']],
                                                    nodes[link['target']], SUBCLASS_STROKE))
                else: # elif type(link['target']) is BNode:
                    self._add_property(nodes[link['source']], link['label'], link['target'])
            # rdf:type: if target is excluded, then save as property; otherwise save link
            elif link['label'] == 'rdf:type':
                if any('/' + s + '#' in str(link['target']) for s in EXCLUDED_PREFIX):
                    self._add_property(nodes[link['source']], ANCESTOR_NAME,
                                       self._reduce_prefix(str(link['target'])))
                else:
                    result.append(self._update_link(link, nodes[link['source']],
                                                    nodes[link['target']], RDFTYPE_STROKE))
            # rdfs:domain and range: include as property
            elif (link['label'] == 'rdfs:domain') or (link['label'] == 'rdfs:range'):
                self._add_property(nodes[link['source']], link['label'], link['target'], as_list=False)
            # otherwise include as property
            else:
                self._add_property(nodes[link['source']], link['label'], link['target'])
        return result

    def _reduce_prefix(self, name: str) -> str:
        label = name.split('#')
        prefix = self._bind[label[0]]
        return prefix + ':' + label[-1] if prefix else label[-1]

    def _add_property(self, node, name: str, value: str, as_list = True):
        if as_list:
            if name not in node:
                node[name] = []
            node[name].append(value)
        else:
            node[name] = value

    def _update_link(self, link, source, target, stroke=0):
        del link['triples']
        link['strokeDasharray'] = stroke
        source['links'] += 1
        target['links'] += 1
        return link

    def _create_link(self, nodes_dict, source, target, label, stroke=0, **kwargs):
        link = {"weight": 1, "source": source, "target": target,
                "label": label, "strokeDasharray": stroke}
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
                node['label'] = node['id'].split('#')[-1]
            if 'rdfs:domain' in node:
                if 'rdfs:range' in node:
                    # convert this into link between nodes
                    links.append(self._create_link(nodes_dict, node['rdfs:domain'],
                                                   node['rdfs:range'], node['label']))
                    links.append(self._create_link(nodes_dict, node['rdfs:range'],
                                                   node['rdfs:domain'], node['label']))
                else:
                    # if it is domain only, then convert this into property
                    self._add_property(nodes_dict[node['rdfs:domain']], PROPERTY_NAME,
                                       self._reduce_prefix(str(node['id']))) # node or node['label']
                    node['domain'] = self._reduce_prefix(str(node['rdfs:domain']))
                    del node['rdfs:domain']
            if 'rdfs:subClassOf' in node:
                # could be to the BNode only, since others are already converted to links
                for n in node['rdfs:subClassOf']:
                    bnode = nodes_dict[n]
                    prop = bnode['owl:onProperty'][0]
                    label = prop if type(prop) is URIRef else nodes_dict[prop]['owl:inverseOf'][0]
                    label = self._reduce_prefix(label)
                    target = bnode['owl:onClass'][0] if 'owl:onClass' in bnode else bnode['owl:someValuesFrom'][0]
                    additional = {}
                    if 'owl:qualifiedCardinality' in bnode:
                        additional['cardinality'] = bnode['owl:qualifiedCardinality'][0]
                    if 'owl:minQualifiedCardinality' in bnode:
                        additional['minCardinality'] = bnode['owl:minQualifiedCardinality'][0]
                    links.append(self._create_link(nodes_dict, node['id'], target, label, **additional))
                del node['rdfs:subClassOf']
            if node['links'] > 0:
                #del node['links']
                if node['id'] in self._endurants:
                    node['isEndurant'] = True
                    node['color'] = 'red'
                if node['id'] in self._relators:
                    node['isRelator'] = True
                    node['color'] = 'green'
                result.append(node)
        return result
