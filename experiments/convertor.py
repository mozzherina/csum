import io
import pydotplus

import rdflib
from rdflib import Graph as RDFGraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from rdflib.tools.rdf2dot import rdf2dot

import networkx as nx
from networkx import Graph as NXGraph


url = "data/gufo.ttl"
# url = "https://raw.githubusercontent.com/nemo-ufes/gufo/master/gufo.ttl"
# url = 'https://www.w3.org/TeamSubmission/turtle/tests/test-30.ttl'

rg = RDFGraph()
result = rg.parse(url, format="turtle")
print("graph has {} statements.".format(len(rg)))

comments = []
for s, p, o in rg:
    if p == rdflib.URIRef("http://www.w3.org/2000/01/rdf-schema#comment"):
        comments.append((s, p, o))
print("number of comments is {}.".format(len(comments)))

for t in comments:
    rg.remove(t)
print("graph without comments has {} statements.".format(len(rg)))

def visualize(g):
    stream = io.StringIO()
    rdf2dot(g, stream)
    dg = pydotplus.graph_from_dot_data(stream.getvalue())
    dg.write_pdf("data/g.pdf")

# visualize(rg)


# Conversion of rdflib.Graph to networkx.Graph
ng = rdflib_to_networkx_graph(rg)
print("networkx Graph loaded successfully with length {}".format(len(ng)))

n = 0
for edge in ng.edges:
    if n < 10:
        print(edge)
    else:
        n += 1


from node2vec import Node2Vec

node2vec = Node2Vec(ng, dimensions=20, walk_length=16, num_walks=100, workers=1)

# Learn embeddings
model = node2vec.fit(window=10, min_count=1, batch_words=4)

# Look for most similar nodes
for node, _ in model.wv.most_similar('http://purl.org/nemo/gufo#RoleMixin'):
    print(node)
# model.wv.most_similar()