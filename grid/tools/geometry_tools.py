import json

from langchain.tools import tool


DB_DATA = []


def set_db_data(data):

    global DB_DATA
    DB_DATA = data


def find_location(location_name: str):

    for row in DB_DATA:

        name, geo_type, geo_json = row

        if name.lower() == location_name.lower():

            return {
                "name": name,
                "type": geo_type,
                "geometry": json.loads(geo_json)
            }

    return None


@tool
def get_all_locations(dummy: str = ""):
    """
    Get all locations.
    """

    return [row[0] for row in DB_DATA]


@tool
def get_location_details(location_name: str):
    """
    Get details of location.
    """

    location = find_location(location_name)

    if not location:
        return "Location not found"

    return location


@tool
def get_point_location(location_name: str):
    """
    Get point coordinates.
    """

    location = find_location(location_name)

    if not location:
        return "Location not found"

    if location["type"] != "point":
        return "Location is not a point"

    return location["geometry"]["position"]