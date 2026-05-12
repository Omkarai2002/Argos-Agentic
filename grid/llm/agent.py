from langchain.agents import initialize_agent
from langchain.agents import AgentType

from grid.tools.geometry_tools import (
    get_all_locations,
    get_location_details,
    get_point_location
)

from grid.tools.area_tools import (
    calculate_polygon_area
)

from grid.tools.grid_tools import (
    generate_grid
)


def build_agent(llm):

    tools = [
        get_all_locations,
        get_location_details,
        get_point_location,
        calculate_polygon_area,
        generate_grid
    ]

    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True
    )

    return agent