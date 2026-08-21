import time
from pathlib import Path
from typing import TypedDict
from httpx import HTTPStatusError

try:
    from openrouter.errors import TooManyRequestsResponseError as OpenRouterRateLimitError
except ImportError:
    OpenRouterRateLimitError = None

from langgraph.graph import StateGraph, START, END
from reader import build_recruiting_agent
from sender import build_sender_agent

# Initialize sub-agents
recruiting_agent = build_recruiting_agent()
sender_agent = build_sender_agent()

# Define graph state
class State(TypedDict):
    messages: list

# Graph Construction & Execution Notes:
# 1. 'recruiting' processes candidate resumes and writes eligible candidates to interns.txt.
# 2. 'sender' reads interns.txt and dispatches offer emails via SendCorex.
# 3. Execution flows sequentially: START -> recruiting -> sender -> END.

builder = StateGraph(State)

builder.add_node("recruiting", recruiting_agent)
builder.add_node("sender", sender_agent)

builder.add_edge(START, "recruiting")
builder.add_edge("recruiting", "sender")
builder.add_edge("sender", END)

graph = builder.compile()

TASK = "Screen candidate resumes against job_description.txt, write matches to interns.txt, and send offer emails."

if __name__ == "__main__":
    result = None
    max_retries = 5

    for attempt in range(1, max_retries + 1):
        try:
            result = graph.invoke({"messages": [("user", TASK)]})
            break
        except Exception as e:
            is_rate_limit = (
                (isinstance(e, HTTPStatusError) and e.response.status_code == 429)
                or "429" in str(e)
                or (OpenRouterRateLimitError and isinstance(e, OpenRouterRateLimitError))
            )
            if is_rate_limit:
                wait = 10 * (2 ** (attempt - 1))
                print(f"Rate limited. Retrying in {wait}s... ({attempt}/{max_retries})")
                time.sleep(wait)
            else:
                raise

    if result is None:
        raise RuntimeError("Gave up after max attempts due to rate limits")

    for m in result["messages"][-3:]:
        print(f"[{m.type}] {str(m.content)[:300]}")
    
    p = Path(__file__).parent / "interns.txt"
    print("interns.txt generated:", p.exists())