from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()


class Neo4jMissionDB:

    def __init__(self):
        self.uri = "bolt://localhost:7687"
        self.username = "neo4j"
        self.password = os.getenv("NEO4J_PASSWORD")

        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.username, self.password)
        )

    def close(self):
        self.driver.close()

    # ---------------- PUBLIC ----------------

    def initialize(self):
        """Run ONCE at startup"""
        with self.driver.session() as session:
            session.execute_write(self._create_constraints)

    def insert_mission(self, data: dict):
        with self.driver.session() as session:
            session.execute_write(self._insert_core, data)
            session.execute_write(self._insert_waypoints_actions, data)
            session.execute_write(self._insert_configs, data)

    # ---------------- INTERNAL ----------------

    @staticmethod
    def _create_constraints(tx):

        tx.run("""
        CREATE CONSTRAINT mission_id IF NOT EXISTS
        FOR (m:Mission) REQUIRE m.id IS UNIQUE
        """)

        tx.run("""
        CREATE CONSTRAINT user_id IF NOT EXISTS
        FOR (u:User) REQUIRE u.id IS UNIQUE
        """)

        tx.run("""
        CREATE CONSTRAINT model_name IF NOT EXISTS
        FOR (m:Model) REQUIRE m.name IS UNIQUE
        """)

    # ---------- Core Mission ----------

    @staticmethod
    def _insert_core(tx, d):

        tx.run("""
        MERGE (u:User {id:$user_id})

        MERGE (m:Mission {id:$mid})
        SET m.prompt=$prompt,
            m.class=$class,
            m.reason=$reason,
            m.complexity=$complexity

        MERGE (model:Model {name:$model})

        MERGE (u)-[:CREATED]->(m)
        MERGE (m)-[:USED_MODEL]->(model)
        """, {
            "user_id": d["user_id"],
            "mid": d["db_record_id"],
            "prompt": d["prompt"],
            "class": d["class"],
            "reason": d["reason"],
            "complexity": d["complexity"],
            "model": d["model_for_extraction"]
        })

    # ---------- Waypoints + Actions ----------

    @staticmethod
    def _insert_waypoints_actions(tx, d):

        tx.run("""
        MATCH (m:Mission {id:$mid})

        UNWIND $wps AS wp
        MERGE (w:Waypoint {sequence: wp.sequence, mission:$mid})
        SET w.location = wp.location,
            w.speed = wp.speed
        MERGE (m)-[:HAS_WAYPOINT]->(w)

        WITH w, wp
        UNWIND wp.actions AS act
        CREATE (a:Action {
            type: act.type,
            duration: act.params.duration
        })
        MERGE (w)-[:HAS_ACTION]->(a)
        """, {
            "mid": d["db_record_id"],
            "wps": d["model_for_extraction_json_output"]["waypoints"]
        })

    # ---------- Config Nodes ----------

    @staticmethod
    def _insert_configs(tx, d):

        mid = d["db_record_id"]
        cfg = d["model_for_extraction_json_output"]
        mc = cfg.get("mission_config", {})
        limits = mc.get("limits", {})

        # TakeoffConfig
        tx.run("""
        MATCH (m:Mission {id:$mid})
        MERGE (t:TakeoffConfig {mission:$mid})
        SET t += $takeoff
        MERGE (m)-[:HAS_TAKEOFF_CONFIG]->(t)
        """, {
            "mid": mid,
            "takeoff": cfg.get("takeoff_config", {})
        })

        # RouteConfig
        tx.run("""
        MATCH (m:Mission {id:$mid})
        MERGE (r:RouteConfig {mission:$mid})
        SET r += $route
        MERGE (m)-[:HAS_ROUTE_CONFIG]->(r)
        """, {
            "mid": mid,
            "route": cfg.get("route_config", {})
        })

        # MissionConfig
        tx.run("""
        MATCH (m:Mission {id:$mid})
        MERGE (mc:MissionConfig {mission:$mid})
        SET mc.mode=$mode,
            mc.yaw_step=$yaw,
            mc.max_vertical_speed=$mvs,
            mc.layer_spacing=$ls
        MERGE (m)-[:HAS_MISSION_CONFIG]->(mc)
        """, {
            "mid": mid,
            "mode": mc.get("mode"),
            "yaw": mc.get("yaw_step"),
            "mvs": limits.get("max_vertical_speed"),
            "ls": limits.get("layer_spacing")
        })

        # Base path (UNWIND)
        tx.run("""
        MATCH (mc:MissionConfig {mission:$mid})
        UNWIND $base AS p
        CREATE (pt:Point {lon:p[0], lat:p[1]})
        MERGE (mc)-[:HAS_BASE_POINT]->(pt)
        """, {
            "mid": mid,
            "base": mc.get("base_path", [])
        })

        # Layers (UNWIND)
        tx.run("""
        MATCH (mc:MissionConfig {mission:$mid})
        UNWIND $layers AS layer
        CREATE (l:Layer {
            altitude: layer.altitude,
            altitude_mode: layer.altitude_mode
        })
        MERGE (mc)-[:HAS_LAYER]->(l)
        """, {
            "mid": mid,
            "layers": mc.get("layers", [])
        })

        # CameraConfig
        cam = mc.get("camera_profile", {})

        tx.run("""
        MATCH (m:Mission {id:$mid})
        MERGE (c:CameraConfig {mission:$mid})
        SET c.pitch=$pitch,
            c.yaw_mode=$yaw
        MERGE (m)-[:HAS_CAMERA_CONFIG]->(c)
        """, {
            "mid": mid,
            "pitch": cam.get("pitch"),
            "yaw": cam.get("yaw_mode")
        })

        if cam.get("poi"):
            tx.run("""
            MATCH (c:CameraConfig {mission:$mid})
            CREATE (p:Point {lon:$lon, lat:$lat})
            MERGE (c)-[:HAS_POI]->(p)
            """, {
                "mid": mid,
                "lon": cam["poi"][0],
                "lat": cam["poi"][1]
            })




# # ---------------- RUN ----------------

# db = Neo4jMissionDB()
# db.initialize() 
# db.insert_mission(json)

# db.close()
