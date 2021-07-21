import networkx as nx
import matplotlib.pyplot as plt

from rdflib import URIRef, Graph as RDFGraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from networkx.readwrite import json_graph
from csum import DATA_DIR


class Graph():
    def __init__(self, logger):
        self.logger = logger
        self._data = None
        self._bind = {}
        self._relators = None
        self._endurants = None

    @property
    def data(self):
        return self._data

    def load_data(self, graph_data):
        rg = RDFGraph()
        rg = rg.parse(graph_data, format="turtle")
        self.logger.info("Loaded graph has {} statements".format(len(rg)))
        self._data = rg
        for prefix, namespace in rg.namespaces():
            ns = str(namespace)
            if ns[-1] == '#':
                ns = ns[:-1]
            self._bind[ns] = prefix
        self._relators = self.get_relators()
        self._endurants = self.get_endurants()

    def get_relators(self):
        results = set()
        for subj in self._data.transitive_subjects(
                URIRef('http://www.w3.org/2000/01/rdf-schema#subClassOf'),
                URIRef('http://purl.org/nemo/gufo#Relator')):
            results.add(subj)
        return results

    def get_endurants(self):
        results = set()
        for endur_name in ['Role', 'Kind', 'SubKind', 'Phase', 'RoleMixin']:
            for subj in self._data.transitive_subjects(
                    URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'),
                    URIRef('http://purl.org/nemo/gufo#'+endur_name)):
                results.add(subj)
        results.difference_update(self._relators)
        return results

    def visualize(self) -> str:
        g = rdflib_to_networkx_graph(self._data)
        print("networkx Graph converted successfully with length {}".format(len(g)))
        file_name = DATA_DIR + '/g.png'
        nx.draw(g, node_size=10)
        plt.savefig(file_name)
        return file_name

    def to_json(self):
        # json-ld
        # turtle
        # return str(self._data.serialize(format='xml'))
        g = rdflib_to_networkx_graph(self._data)
        print("networkx Graph converted successfully with length {}".format(len(g)))
        data = json_graph.node_link_data(g)
        del data['directed']
        del data['multigraph']
        del data['graph']
        for node in data['nodes']:
            node_id = node['id'].split('#')
            node['name'] = node_id[-1]
            if len(node_id) > 1:
                if not self._bind[node_id[0]]:
                    node['isBase'] = True
                else:
                    node['is' + self._bind[node_id[0]].capitalize()] = True
            if node['id'] in self._endurants:
                node['isEndurant'] = True
            if node['id'] in self._relators:
                node['isRelator'] = True

        for link in data['links']:
            label = (str(link['triples'][0][1])).split('#')
            if self._bind[label[0]]:
                link['label'] = self._bind[label[0]] + ':' + label[-1]
            else:
                link['label'] = label[-1]
            del link['triples']

        return data
