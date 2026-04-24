# annotations_calculation.py

from typing import Dict, List
import json


class GeometryCenterCalculator:

    @staticmethod
    def calculate(row: Dict) -> List[float]:
        """
        row:
        {
          "shape": str,
          "geometry": dict,
          "height": float | None
        }

        returns: [lon, lat, alt]
        """

        shape = row["shape"].lower()
        geom = json.loads(row["geometry"]) if isinstance(row["geometry"], str) else row["geometry"]
        print('geometry_type:', type(row["geometry"]))
        altitude = row.get("height") or 0
        print('geometry:', shape, geom, altitude)
        # Shapes that already store center
        if shape in {"circle", "ellipse", "cylinder", "box"}:
            print('geometry center:', geom["center"])
            return GeometryCenterCalculator._with_alt(geom["center"])

        # Point
        if shape == "point":
            return GeometryCenterCalculator._with_alt(geom["position"])

        # Rectangle
        if shape == "rectangle":
            lon = (geom["west"] + geom["east"]) / 2
            lat = (geom["south"] + geom["north"]) / 2
            return [lon, lat, altitude]

        # Polygon
        if shape == "polygon":
            return GeometryCenterCalculator._average_points(
                geom["hierarchy"]
            )

        # Polyline
        if shape == "polyline":
            return GeometryCenterCalculator._average_points(
                geom["positions"]
            )

        raise ValueError(f"Unsupported shape: {shape}")

    @staticmethod
    def _average_points(points: List[List[float]]) -> List[float]:
        lon = sum(p[0] for p in points) / len(points)
        lat = sum(p[1] for p in points) / len(points)

        # If altitude provided per point
        if len(points[0]) == 3:
            alt = sum(p[2] for p in points) / len(points)
        
        print("polygon_coord:",[lon, lat])
        return [lon, lat]

    @staticmethod
    def _with_alt(center: List[float]) -> List[float]:
        print("center_normal:", center)
        if len(center) == 3:
            print("center 3:",center)
            return center
        return [center[0], center[1]]
