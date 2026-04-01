from typing import TypedDict, Optional
from .schemas import MissionResponse
from .validation import validate_waypoints
from .llm_setup import prompt, structured_llm

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
        validate_waypoints(result)

        state["result"] = result
        state["error"] = None

    except Exception as e:
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
    elif state["retries"] >= MAX_RETRIES:
        return "fail"
    else:
        return "retry"