from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()


class GraphValidator:

    def __init__(self,uri,user,password):
        
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()
    def validate_location(self, user_id: str, location: str):
        query = """
        MATCH (u:User)-[:CREATED]->(m:Mission)
        WHERE u.id = $user_id OR u.id = toInteger($user_id)

        MATCH (w:Waypoint)
        WHERE toLower(w.location) CONTAINS toLower($location)
        AND w.mission = toString(m.id)
        AND w.sequence = 1

        OPTIONAL MATCH (m)-[:HAS_ROUTE_CONFIG]->(rc:RouteConfig)
        OPTIONAL MATCH (m)-[:HAS_ACTION]->(a:Action)

        RETURN m, rc, collect(a) as actions
        ORDER BY toInteger(m.id) DESC
        limit 5
        """

        with self.driver.session() as session:
            records = session.run(query, user_id=user_id, location=location).data()

        if not records:
            print("No matching location found in graph DB")
            return None

        return [
            {
                "mission_id": r["m"]["id"],
                "speed": r["rc"]["speed"] if r["rc"] else None,
                "altitude": r["rc"]["altitude"] if r["rc"] else None,
                "altitude_mode": r["rc"]["altitude_mode"] if r["rc"] else None,
                "actions": [dict(a) for a in r["actions"]] if r["actions"] else []
            }
            for r in records
        ]


# if __name__ == "__main__":
#     validator = GraphValidator(
#         uri="bolt://localhost:7687",
#         user="neo4j",
#         password=os.getenv("NEO4J_PASSWORD")
#     )

#     result = validator.validate_location(user_id="1", location="Main Entrance Checkpoint")
#     print("\n===== RESULT =====\n")
#     print(result)

#     validator.close()