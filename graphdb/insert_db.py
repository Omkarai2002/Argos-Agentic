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

        mid = d["db_record_id"]
        waypoints = d["model_for_extraction_json_output"]["waypoints"]

        for wp in waypoints:

            tx.run("""
            MERGE (w:Waypoint {sequence:$seq, mission:$mid})
            SET w.location=$loc,
                w.speed=$speed

            WITH w
            MATCH (m:Mission {id:$mid})
            MERGE (m)-[:HAS_WAYPOINT]->(w)
            """, {
                "seq": wp["sequence"],
                "mid": mid,
                "loc": wp["location"],
                "speed": wp["speed"]
            })

            for act in wp["actions"]:
                tx.run("""
                MATCH (w:Waypoint {sequence:$seq, mission:$mid})
                CREATE (a:Action {type:$type, duration:$dur})
                MERGE (w)-[:HAS_ACTION]->(a)
                """, {
                    "seq": wp["sequence"],
                    "mid": mid,
                    "type": act["type"],
                    "dur": act["params"]["duration"]
                })

    # ---------- Config Nodes ----------

    @staticmethod
    def _insert_configs(tx, d):

        mid = d["db_record_id"]
        cfg = d["model_for_extraction_json_output"]

        # TakeoffConfig
        t = cfg.get("takeoff_config", {})
        tx.run("""
        MATCH (m:Mission {id:$mid})
        MERGE (t:TakeoffConfig {mission:$mid})
        SET t.altitude=$alt, t.altitude_mode=$mode, t.speed=$speed
        MERGE (m)-[:HAS_TAKEOFF_CONFIG]->(t)
        """, {
            "mid": mid,
            "alt": t.get("altitude"),
            "mode": t.get("altitude_mode"),
            "speed": t.get("speed")
        })

        # RouteConfig
        r = cfg.get("route_config", {})
        tx.run("""
        MATCH (m:Mission {id:$mid})
        MERGE (r:RouteConfig {mission:$mid})
        SET r.altitude=$alt,
            r.altitude_mode=$mode,
            r.speed=$speed,
            r.radius=$radius
        MERGE (m)-[:HAS_ROUTE_CONFIG]->(r)
        """, {
            "mid": mid,
            "alt": r.get("altitude"),
            "mode": r.get("altitude_mode"),
            "speed": r.get("speed"),
            "radius": r.get("radius")
        })

        # MissionConfig
        mc = cfg.get("mission_config", {})
        limits = mc.get("limits", {})

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
            "base_path": mc.get("base_path"),
            "yaw": mc.get("yaw_step"),
            "mvs": limits.get("max_vertical_speed"),
            "ls": limits.get("layer_spacing")
        })
        # Base path points
        for p in mc.get("base_path", []):
            tx.run("""
            MATCH (mc:MissionConfig {mission:$mid})
            CREATE (pnt:Point {lon:$lon, lat:$lat})
            MERGE (mc)-[:HAS_BASE_POINT]->(pnt)
            """, {
                "mid": mid,
                "lon": p[0],
                "lat": p[1]
            })


        # Layers
        for layer in mc.get("layers", []):
            tx.run("""
            MATCH (mc:MissionConfig {mission:$mid})
            CREATE (l:Layer {altitude:$alt, altitude_mode:$mode})
            MERGE (mc)-[:HAS_LAYER]->(l)
            """, {
                "mid": mid,
                "alt": layer.get("altitude"),
                "mode": layer.get("altitude_mode")
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

        poi = cam.get("poi")
        if poi:
            tx.run("""
            MATCH (c:CameraConfig {mission:$mid})
            CREATE (p:Point {lon:$lon, lat:$lat})
            MERGE (c)-[:HAS_POI]->(p)
            """, {
                "mid": mid,
                "lon": poi[0],
                "lat": poi[1]
            })



# # ---------------- RUN ----------------

# db = Neo4jMissionDB()
# db.initialize() 
# db.insert_mission(json)

# db.close()
