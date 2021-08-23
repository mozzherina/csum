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
