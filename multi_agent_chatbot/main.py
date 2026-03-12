import os
from typing import TypedDict, List, Dict, Optional, Literal
from pydantic import BaseModel
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from openai import OpenAI
from dotenv import load_dotenv
from utils.logger import get_logger
from multi_agent_chatbot.tools_current_weather import get_current_weather

_logs = get_logger(__name__)

load_dotenv(".env")
load_dotenv(".secrets")

API_GATEWAY_KEY = os.getenv("API_GATEWAY_KEY", "")

if not API_GATEWAY_KEY:
    raise RuntimeError("Please set API_GATEWAY_KEY")

client = OpenAI(base_url='https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1', 
                api_key='any value',
                default_headers={"x-api-key": os.getenv('API_GATEWAY_KEY')})

# -----------------------------
# LLM SETUP
# -----------------------------
llm_router = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_math = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_code = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_general = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# -----------------------------
# STATE & SCHEMA
# -----------------------------
class AgentState(TypedDict, total=False):
    user_input: str
    route: Optional[Literal["math", "code", "general", "plan_chain"]]

    math_answer: Optional[str]
    code_answer: Optional[str]
    general_answer: Optional[str]
    final_answer: Optional[str]

    plan: Optional[str]
    work_draft: Optional[str]
    review_notes: Optional[str]

    history: List[Dict[str, str]]
    turn: int
    context: Dict[str, str]

    active_persona: Optional[str]


class RouteDecision(BaseModel):
    route: Literal["math", "code", "general", "plan_chain", "weather"]


# -----------------------------
# PERSONAS
# -----------------------------
PERSONAS = {
    "math": """
                You are **Dr. Ada**, a brilliant but warm mathematician.
                Your style:
                - precise, structured reasoning
                - gentle teaching tone
                - uses short proofs, diagrams-in-words, and analogies
                - avoids unnecessary jargon
            """,
    "code": """
                You are **Rex**, a senior software engineer with a calm, confident vibe.
                Your style:
                - clean, production-ready code
                - explains tradeoffs
                - uses short code blocks and crisp comments
                - never over-engineers
            """,
    "general": """
                    You are **Nova**, an insightful generalist with a friendly, conversational tone.
                    Your style:
                    - empathetic
                    - clear, direct explanations
                    - uses examples and metaphors
                    - keeps things human and approachable
                """,
    "planner": """
                    You are **Orion**, a strategic planner.
                    You break down complex tasks into clear, numbered steps and assumptions.
                """,
    "worker": """
                    You are **Rex**, an execution-focused implementer.
                    You follow the plan exactly and produce concrete output.
                """,
    "reviewer": """
                    You are **Vega**, a critical but fair reviewer.
                    You check the work against the plan and suggest improvements.
                """
}

# -----------------------------
# HELPERS
# -----------------------------
def _history_text(state: AgentState, include_assistant=True):
    lines = []
    for h in state.get("history", []):
        if include_assistant:
            lines.append(
                f"Turn {h['turn']} — User: {h['user']}\nAssistant: {h['assistant']}"
            )
        else:
            lines.append(f"Turn {h['turn']} — User: {h['user']}")
    return "\n\n".join(lines)


# -----------------------------
# ROUTER NODE
# -----------------------------
def router_node(state: AgentState) -> AgentState:
    RouterLLM = llm_router.with_structured_output(RouteDecision)
    history_text = _history_text(state, include_assistant=False)

    prompt = f"""
                    You are a routing controller.

                    Routes:
                    - math
                    - code
                    - general
                    - plan_chain
                    - weather

                    Conversation so far:
                    {history_text}

                    User request:
                    {state["user_input"]}

                    Choose the best route.
                """
    result: RouteDecision = RouterLLM.invoke(prompt)
    return {"route": result.route}


# -----------------------------
# SPECIALIST AGENTS
# -----------------------------
def math_agent(state: AgentState) -> AgentState:
    prompt = f"""
                {PERSONAS['math']}

                Conversation so far:
                {_history_text(state)}

                Current user message:
                {state["user_input"]}
            """
    resp = llm_math.invoke(prompt)
    return {"math_answer": resp.content, "final_answer": resp.content, "active_persona": "Dr. Ada"}


def code_agent(state: AgentState) -> AgentState:
    prompt = f"""
                {PERSONAS['code']}

                Conversation so far:
                {_history_text(state)}

                Current user message:
                {state["user_input"]}
            """
    resp = llm_code.invoke(prompt)
    return {"code_answer": resp.content, "final_answer": resp.content, "active_persona": "Rex"}


def general_agent(state: AgentState) -> AgentState:
    prompt = f"""
                {PERSONAS['general']}

                Conversation so far:
                {_history_text(state)}

                Current user message:
                {state["user_input"]}
            """
    resp = llm_general.invoke(prompt)
    return {"general_answer": resp.content, "final_answer": resp.content, "active_persona": "Nova"}


# -----------------------------
# PLANNER → WORKER → REVIEWER
# -----------------------------
def planner_agent(state: AgentState) -> AgentState:
    prompt = f"""
                {PERSONAS['planner']}

                Conversation so far:
                {_history_text(state)}

                User request:
                {state["user_input"]}

                Produce a numbered plan.
            """
    resp = llm_general.invoke(prompt)
    return {"plan": resp.content, "active_persona": "Orion"}


def worker_agent(state: AgentState) -> AgentState:
    prompt = f"""
                {PERSONAS['worker']}

                User request:
                {state["user_input"]}

                Plan:
                {state.get("plan", "")}

                Execute the plan.
            """
    resp = llm_code.invoke(prompt)
    return {"work_draft": resp.content, "active_persona": "Rex"}


def reviewer_agent(state: AgentState) -> AgentState:
    prompt = f"""
                {PERSONAS['reviewer']}

                User request:
                {state["user_input"]}

                Plan:
                {state.get("plan", "")}

                Draft:
                {state.get("work_draft", "")}

                Review and improve.
            """
    resp = llm_general.invoke(prompt)
    return {"review_notes": "Reviewed", "final_answer": resp.content, "active_persona": "Vega"}


# -----------------------------
# WEATHER NODE
# -----------------------------
def weather_agent(state: AgentState) -> AgentState:
    user_msg = state["user_input"]

    # Extract location from user message 
    location = "Toronto"

    prompt = f"""
            Find the location in user message, and only return location.
            Return "No location found" in case location is not found.

            Current user message:
            {user_msg}
        """
    resp = llm_general.invoke(prompt)
    if resp.content != "" and not resp.content.lower().__contains__("location"):
        location = resp.content.title()
        
    _logs.info(f"Location: {location}")

    try:
        weather_info = get_current_weather.run({"location": location})
    except Exception as e:
        weather_info = f"Sorry, I couldn't fetch weather data: {e}"
        _logs.info(f"Sorry, I couldn't fetch weather data: {e}")

    final = f"Weather for **{location}**:\n\n{weather_info}"
    _logs.info(f"final - Weather for **{location}**:\n\n{weather_info}")

    return {
        "final_answer": final,
        "active_persona": "WeatherBot"
    }


# -----------------------------
# MEMORY NODE
# -----------------------------
def memory_update_node(state: AgentState) -> AgentState:
    history = state.get("history", [])
    turn = state.get("turn", 0) + 1

    history.append({
        "turn": turn,
        "user": state["user_input"],
        "assistant": state["final_answer"]
    })

    return {"history": history, "turn": turn}


# -----------------------------
# GRAPH BUILD
# -----------------------------
graph = StateGraph(AgentState)

graph.add_node("router", router_node)
graph.add_node("math_agent", math_agent)
graph.add_node("code_agent", code_agent)
graph.add_node("general_agent", general_agent)
graph.add_node("planner_agent", planner_agent)
graph.add_node("worker_agent", worker_agent)
graph.add_node("reviewer_agent", reviewer_agent)
graph.add_node("weather_agent", weather_agent)
graph.add_node("memory_update", memory_update_node)

graph.set_entry_point("router")


def route_decider(state: AgentState):
    return state["route"]


graph.add_conditional_edges(
    "router",
    route_decider,
    {
        "math": "math_agent",
        "code": "code_agent",
        "general": "general_agent",
        "plan_chain": "planner_agent",
        "weather": "weather_agent",
    },
)

# -----------------------------
# SINGLE AGENT
# -----------------------------
graph.add_edge("math_agent", "memory_update")
graph.add_edge("code_agent", "memory_update")
graph.add_edge("general_agent", "memory_update")
graph.add_edge("weather_agent", "memory_update")
# -----------------------------
# PLAN-CHAIN
# -----------------------------
graph.add_edge("planner_agent", "worker_agent")
graph.add_edge("worker_agent", "reviewer_agent")
graph.add_edge("reviewer_agent", "memory_update")

graph.add_edge("memory_update", END)

app = graph.compile()

# -----------------------------
# EXPORTS FOR UI
# -----------------------------
def init_state():
    return {"history": [], "turn": 0, "context": {}}


def run_turn(state, user_message):
    state["user_input"] = user_message
    result = app.invoke(state)
    return result["final_answer"], result


def extract_trace(state):
    trace = f"""### Agent Trace\n- **Route:** {state.get('route')}\n- **Persona:** {state.get('active_persona')}\n\n"""
    if state.get("plan"):
        trace += f"#### Planner Output\n{state['plan']}\n\n"
    if state.get("work_draft"):
        trace += f"#### Worker Draft\n{state['work_draft']}\n\n"
    if state.get("review_notes"):
        trace += f"#### Reviewer Notes\n{state['review_notes']}\n\n"
    return trace


def extract_plan(state):
    if not state.get("plan"):
        return "No plan for this turn."
    return f"### Plan\n\n{state['plan']}"


AVATARS = {
    "Dr. Ada": "multi_agent_chatbot/assets/ada.jpg",
    "Rex": "multi_agent_chatbot/assets/rex.jpg",
    "Nova": "multi_agent_chatbot/assets/nova.jpg",
    "Orion": "multi_agent_chatbot/assets/orion.jpg",
    "Vega": "multi_agent_chatbot/assets/vega.jpg",
    "user": "multi_agent_chatbot/assets/user.jpg"
}


def get_persona_avatar(name):
    return AVATARS.get(name, AVATARS["Nova"])