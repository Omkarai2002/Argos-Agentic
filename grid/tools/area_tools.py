from shapely.geometry import Polygon

from langchain.tools import tool

from grid.tools.geometry_tools import find_location


@tool
def calculate_polygon_area(location_name: str):
    """
    Calculate polygon area.
    """

    location = find_location(location_name)

    if not location:
        return "Location not found"

    if location["type"] != "polygon":
        return "Location is not polygon"

    coordinates = location["geometry"]["hierarchy"]

    polygon = Polygon(coordinates)

    return {
        "location": location_name,
        "area": polygon.area
    }