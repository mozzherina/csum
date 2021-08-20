from rdflib import URIRef, Namespace, Graph as RDFGraph

graph:Graph

query = """
    SELECT DISTINCT ?relator ?endurant WHERE {
        ?relator rdfs:subClassOf gufo:Relator.
        ?relator (rdfs:subClassOf/owl:onProperty
                 |rdfs:subClassOf/owl:onProperty/owl:inverseOf) gufo:mediates.
        ?relator rdfs:subClassOf/owl:onClass ?endurant.
    }
"""
qres = graph.data.query(query)
for row in qres:
    print(f"{row.relator} {row.endurant}")