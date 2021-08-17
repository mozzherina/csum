from rdflib import URIRef, BNode, Literal, Graph as RDFGraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_digraph
from networkx.readwrite import json_graph
from colour import Color

from csum import LANGUAGE, EXCLUDED_PREFIX, SUBCLASS_STROKE, \
    RDFTYPE_STROKE, LABEL_NAME, ANCESTOR_NAME


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
            # nodes processing, nodes is a dict of nodes' ids
            data['nodes'] = self._nodes_postprocessing(data['nodes'])
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
            # label = ['http://www.w3.org/2002/07/owl', 'onProperty']
            label = (str(link['triples'][0][1])).split('#')
            prefix = self._bind[label[0]]
            link['label'] = prefix + ':' + label[-1] if prefix else label[-1]
            # comment
            if link['label'] == 'rdfs:comment':
                nodes[link['source']]['comment'] = str(link['target'])
            # label
            elif link['label'] == 'rdfs:label':
                if link['target'].language == LANGUAGE:
                    nodes[link['source']]['label'] = str(link['target'])
                else:
                    self._add_property(nodes[link['source']], LABEL_NAME,
                                       str(link['target']) + '@' + link['target'].language)
            # subclass
            elif link['label'] == 'rdfs:subClassOf':
                if type(link['source']) is URIRef and type(link['target']) is URIRef:
                    result.append(self._add_link(link, SUBCLASS_STROKE, nodes[link['source']],
                                                 nodes[link['target']]))
                else:
                    print("subclass of bnode")
            # type
            elif link['label'] == 'rdf:type':
                if any('/' + s + '#' in str(link['target']) for s in EXCLUDED_PREFIX):
                    self._add_property(nodes[link['source']], ANCESTOR_NAME, str(link['target']))
                else:
                    result.append(self._add_link(link, RDFTYPE_STROKE, nodes[link['source']],
                                                 nodes[link['target']]))
            else:
                print(link['label'])
        return result

    def _add_property(self, node, name: str, value: str):
        if name not in node:
            node[name] = []
        node[name].append(value)

    def _add_link(self, link, stroke, source, target):
        del link['triples']
        link['strokeDasharray'] = stroke
        source['links'] += 1
        target['links'] += 1
        return link

    def _nodes_postprocessing(self, nodes: list) -> list:
        """
        Updates nodes, removes redundant
        :param nodes: original list of nodes
        :return: list of nodes
        """
        result = []
        for node in nodes:
            if node['links'] > 0:
                del node['links']
                node_id = node['id'].split('#')
                if 'label' not in node:
                    node['label'] = node_id[-1]
                if ANCESTOR_NAME in node:
                    anc_list = []
                    for ancestor in node[ANCESTOR_NAME]:
                        label = ancestor.split('#')
                        prefix = self._bind[label[0]]
                        anc_list.append(prefix + ':' + label[-1] if prefix else label[-1])
                    node[ANCESTOR_NAME] = anc_list
                # if there is a prefix, add corresponding property
                if len(node_id) > 1:
                    # if prefix is empty, then it's a base prefix
                    if not self._bind[node_id[0]]:
                        node['isBase'] = True
                    else:
                        node['is' + self._bind[node_id[0]].capitalize()] = True
                if node['id'] in self._endurants:
                    node['isEndurant'] = True
                    node['color'] = 'red'
                if node['id'] in self._relators:
                    node['isRelator'] = True
                    node['color'] = 'green'
                result.append(node)
        return result

