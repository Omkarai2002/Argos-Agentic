from typing import TypedDict, Optional
from .schemas import MissionResponse
from .validation_intent import validate_waypoints
from .llm_setup import prompt, structured_llm
import traceback

# -----------------------------
# State Definition
# -----------------------------

class State(TypedDict):
    input: str
    result: Optional[MissionResponse]
    error: Optional[str]
    retries: int


# -----------------------------
# Generate Node
# -----------------------------
def generate(state: State) -> State:
    chain = prompt | structured_llm

    try:
        result = chain.invoke({"input": state["input"]})
        print("RAW LLM OUTPUT:", result)

        print("STEP 1: Before validation")

        # Print every waypoint field before validation
        for i, wp in enumerate(result.waypoints):
            print(f"wp[{i}] type={repr(wp.type)} angle={repr(wp.angle_degrees)} dist={repr(wp.distance_meters)} loc={repr(wp.location)}")

        try:
            validate_waypoints(result)
            print("STEP 2: Validation passed")
        except Exception as e:
            print("FULL TRACEBACK:")
            traceback.print_exc()
            raise e

        print("STEP 3: After validation")

        state["result"] = result
        state["error"] = None

    except Exception as e:
        print("FINAL ERROR:", e)
        state["error"] = str(e)

    return state


# -----------------------------
# Retry Node
# -----------------------------

MAX_RETRIES = 3

def retry(state: State) -> State:
    if state["retries"] >= MAX_RETRIES:
        return state

    state["retries"] += 1

    state["input"] = (
        f"{state['input']}\n"
        f"Previous error: {state['error']}. "
        f"Fix output strictly."
    )

    return state


# -----------------------------
# Decision Function
# -----------------------------
def decide(state: State):
    if state.get("error") is None:
        return "success"

    if "Waypoint" in str(state["error"]):
        return "fail"

    if state["retries"] >= MAX_RETRIES:
        return "fail"

    return "retry"