class QueriesGenerator:
    @staticmethod
    def get_relators() -> str:
        query = """
                SELECT ?relator ?bnode ?endurant WHERE {
                    ?relator rdfs:subClassOf ?bnode.
                    { ?bnode owl:onClass ?endurant }
                    UNION
                    { ?bnode owl:someValuesFrom ?endurant }
                }
                """
        return query

    @staticmethod
    def generate_update(from_node, old_to_node, new_to_node) -> dict:
        # graph.update(**QG.generate_update(bnode1, relator, endurant2))
        # graph.update(**QG.generate_update(bnode2, relator, endurant1))
        query = """
                DELETE { ?from_node owl:onClass ?old_to_node } 
                INSERT { ?from_node owl:onClass ?new_to_node } 
                WHERE { ?from_node owl:onClass ?old_to_node }
                """
        kwargs = {
            'update_object': query,
            'initBindings': {
                'from_node': from_node,
                'old_to_node': old_to_node,
                'new_to_node': new_to_node
            }
        }
        return kwargs
