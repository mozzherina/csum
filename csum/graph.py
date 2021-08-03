from rdflib import URIRef, BNode, Literal, Graph as RDFGraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from networkx.readwrite import json_graph


class Graph:
    # should be set while in props file
    LINKS_TO_DELETE = [] # ['rdfs:label', 'rdf:label']

    def __init__(self, logger):
        self.logger = logger
        self._bind = None
        self._data = None
        self._relators = None
        self._endurants = None

    @property
    def data(self):
        return self._data

    def load_data(self, graph_data):
        self._data = RDFGraph().parse(graph_data, format="turtle")
        self.logger.info("Loaded graph has {} statements".format(len(self._data)))

        # set up bindings of the rdf graph
        self._bind = {}
        for prefix, namespace in self._data.namespaces():
            ns = str(namespace)
            if ns[-1] == '#':
                ns = ns[:-1]
            self._bind[ns] = prefix

        # set up gufo properties of the graph
        self._relators = self._get_relators()
        self._endurants = self._get_endurants()

    def _get_relators(self):
        results = set()
        for subj in self._data.transitive_subjects(
                URIRef('http://www.w3.org/2000/01/rdf-schema#subClassOf'),
                URIRef('http://purl.org/nemo/gufo#Relator')):
            results.add(subj)
        return results

    def _get_endurants(self):
        results = set()
        for endurant_name in ['Role', 'Kind', 'SubKind', 'Phase', 'RoleMixin']: # ???
            for subj in self._data.transitive_subjects(
                    URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'),
                    URIRef('http://purl.org/nemo/gufo#' + endurant_name)):
                results.add(subj)
        results.difference_update(self._relators)
        return results

    def get_core(self, base_only: bool):
        g = rdflib_to_networkx_graph(self._data)
        self.logger.info("Graph converted to networkx with length {}".format(len(g)))
        data = json_graph.node_link_data(g)
        del data['directed']
        del data['multigraph']
        del data['graph']
        # nodes processing, nodes is a dict of nodes' ids
        data['nodes'], nodes = self._nodes_postprocessing(data['nodes'], base_only)
        # links processing, nodes will contain nodes' ids with the sum of in/out links
        data['links'], nodes = self._links_postprocessing(data['links'], nodes)
        # remove nodes without links
        # data['nodes'] = self._remove_redundant_nodes(data['nodes'], nodes)
        return data

    def _nodes_postprocessing(self, nodes: list, base_only: bool) -> (list, dict):
        """
        Updates nodes, removes redundant
        :param nodes: original list of nodes
        :param base_only: if True, leave only base nodes
        :return: list of nodes, dict with the same nodes' ids
        """
        result = []
        nodes_dict = {}
        for node in nodes:
            node_id = node['id'].split('#')
            node['name'] = node_id[-1]
            # if there is a prefix, add corresponding property
            if len(node_id) > 1:
                # if prefix is empty, then it's a base prefix
                if not self._bind[node_id[0]]:
                    node['isBase'] = True
                else:
                    node['is' + self._bind[node_id[0]].capitalize()] = True
            if (base_only and ('isBase' in node)) or (not base_only):
                # the node should be kept
                nodes_dict[node['id']] = 0
                if type(node['id']) is URIRef:
                    node['isURI'] = True
                    node['symbolType'] = 'circle'
                elif type(node['id']) is BNode:
                    node['isBNode'] = True
                    del node['name']
                elif type(node['id']) is Literal:
                    node['isLiteral'] = True
                    node['symbolType'] = 'square'
                if node['id'] in self._endurants:
                    node['isEndurant'] = True
                    node['color'] = 'red'
                if node['id'] in self._relators:
                    node['isRelator'] = True
                    node['color'] = 'green'
                result.append(node)
        return result, nodes_dict

    def _links_postprocessing(self, links: list, nodes: dict) -> (list, dict):
        """
        Updates links, removes redundant
        :param links: original list of links
        :param nodes: dict of nodes, who would be kept
        :return: list of links, dict of nodes with num of in/out edges
        """
        result = []
        for link in links:
            label = (str(link['triples'][0][1])).split('#')
            if self._bind[label[0]]:
                link['label'] = self._bind[label[0]] + ':' + label[-1]
            else:
                link['label'] = label[-1]
            if link['label'] not in self.LINKS_TO_DELETE:
                del link['triples']
                if (link['source'] in nodes) and (link['target'] in nodes):
                    result.append(link)
                    nodes[link['source']] += 1
                    nodes[link['target']] += 1
        return result, nodes

    """
    def _remove_redundant_nodes(self, data: list, nodes: dict) -> list:
        result = []
        for node in data:
            if nodes[node['id']] > 0:
                result.append(node)
        return result
    """
