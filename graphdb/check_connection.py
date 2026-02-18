from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
load_dotenv()

class CheckConnectionForNeo4j:
    def __init__(self):
        self.URI = "bolt://localhost:7687"
        self.USER = "neo4j"
        self.PASSWORD = os.getenv("NEO4J_PASSWORD")
    def is_connection(self):
        driver=GraphDatabase.driver(self.URI, auth=(self.USER, self.PASSWORD))
        if driver:
            return True
        return False

c=CheckConnectionForNeo4j()
print(c.is_connection())