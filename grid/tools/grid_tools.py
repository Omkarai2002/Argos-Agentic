from langchain.tools import tool

from grid.tools.geometry_tools import find_location


@tool
def generate_grid(location_name: str):
    """
    Generate grid from polygon.
    """

    location = find_location(location_name)

    if not location:
        return "Location not found"

    if location["type"] != "polygon":
        return "Grid can only be generated for polygons"

    coordinates = location["geometry"]["hierarchy"]

    return {
        "message": "Grid generated",
        "coordinates": coordinates
    }