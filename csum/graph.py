import io
import pydotplus

from rdflib import plugin, Graph as RDFGraph
from rdflib.serializer import Serializer
from rdflib.tools.rdf2dot import rdf2dot
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph

from csum import DATA_DIR

class Graph:
    def __init__(self, logger):
        self.logger = logger
        self._data = None

    @property
    def data(self):
        return self._data

    def load_data(self, graph_data):
        rg = RDFGraph()
        rg = rg.parse(graph_data, format="turtle")
        self.logger.info("Loaded graph has {} statements".format(len(rg)))
        self._data = rg

    def visualize(self) -> str:
        stream = io.StringIO()
        rdf2dot(self._data, stream)
        dg = pydotplus.graph_from_dot_data(stream.getvalue())
        file_name = DATA_DIR + '/g.pdf'
        dg.write_pdf(file_name)
        self.logger.info("Visualized graph is saved in {}".format(file_name))
        return file_name

    def to_json(self):
        return str(self._data.serialize(format='json-ld', indent=4))

