# annotations_calculation.py

from typing import Dict, List


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
        geom = row["geometry"]
        altitude = row.get("height") or 0

        # Shapes that already store center
        if shape in {"circle", "ellipse", "cylinder", "box"}:
            return GeometryCenterCalculator._with_alt(geom["center"], altitude)

        # Point
        if shape == "point":
            return GeometryCenterCalculator._with_alt(geom["position"], altitude)

        # Rectangle
        if shape == "rectangle":
            lon = (geom["west"] + geom["east"]) / 2
            lat = (geom["south"] + geom["north"]) / 2
            return [lon, lat, altitude]

        # Polygon
        if shape == "polygon":
            return GeometryCenterCalculator._average_points(
                geom["hierarchy"], altitude
            )

        # Polyline
        if shape == "polyline":
            return GeometryCenterCalculator._average_points(
                geom["positions"], altitude
            )

        raise ValueError(f"Unsupported shape: {shape}")

    @staticmethod
    def _average_points(points: List[List[float]], altitude: float) -> List[float]:
        lon = sum(p[0] for p in points) / len(points)
        lat = sum(p[1] for p in points) / len(points)

        # If altitude provided per point
        if len(points[0]) == 3:
            alt = sum(p[2] for p in points) / len(points)
        else:
            alt = altitude

        return [lon, lat, alt]

    @staticmethod
    def _with_alt(center: List[float], altitude: float) -> List[float]:
        if len(center) == 3:
            return center
        return [center[0], center[1], altitude]
