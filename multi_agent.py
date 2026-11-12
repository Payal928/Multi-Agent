import os
os.environ["OTEL_SDK_DISABLED"] = "true"
from google.genai import types
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv
from typing import TypedDict, Literal
from pydantic import BaseModel
from guardrails import Guard
from google import genai

from guardrails_ai.detect_pii import DetectPII
from guardrails_ai.prompt_injection_detector import PromptInjectionDetector
import os


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)


# --------------------------------------------------
# 1. STRUCTURED RESPONSE FOR SUPERVISOR
# --------------------------------------------------

class SupervisorResponse(BaseModel):
    agent: Literal["researcher", "analyst", "writer", "general"]


# --------------------------------------------------
# 2. LANGGRAPH STATE
# --------------------------------------------------

class State(TypedDict):
    user_query: str
    clean_query: str | None
    is_blocked: bool
    selected_agent: str | None
    final_response: str | None

    # Frontend guardrail information
    pii_detected: bool
    guardrail_events: list[str]
    blocked_reason: str | None

# --------------------------------------------------
# 3. INPUT GUARDRAILS
# --------------------------------------------------

# PII detection and anonymization
pii_guard = Guard().use(
    DetectPII(
        pii_entities=[
            "EMAIL_ADDRESS",
            "PHONE_NUMBER",
            "PERSON",
            "CREDIT_CARD"
        ],
        on_fail="fix",
        use_local=True
    )
)

# Prompt injection detection

injection_guard = Guard().use(
    PromptInjectionDetector(
        llm_callable="gemini/gemini-3.6-flash",
        threshold=0.8,
        on_fail="noop"
    )
)

def validate_user_input(user_query):

    print("\nInput Guardrails Running...")

    events = []

    try:
        # --------------------------------
        # 1. PII DETECTION
        # --------------------------------

        pii_result = pii_guard.validate(user_query)

        clean_query = pii_result.validated_output or user_query

        pii_detected = clean_query != user_query

        if pii_detected:
            events.append("PII detected and redacted.")
            print("PII Detected and Redacted")
        else:
            events.append("PII check passed. No PII detected.")
            print("No PII Detected")

        # --------------------------------
        # 2. PROMPT INJECTION DETECTION
        # --------------------------------

        injection_result = injection_guard.parse(clean_query)

        if not injection_result.validation_passed:

            events.append("Prompt injection detected. Request blocked.")

            return {
                "allowed": False,
                "clean_query": None,
                "pii_detected": pii_detected,
                "events": events,
                "message": "Prompt injection detected. Your query was blocked."
            }

        events.append("Prompt injection check passed.")

        print("Prompt Injection Check Passed")

        return {
            "allowed": True,
            "clean_query": clean_query,
            "pii_detected": pii_detected,
            "events": events,
            "message": "Input passed guardrails."
        }

    except Exception as e:

        print("Guardrail Error:", str(e))

        events.append("Input validation failed. Request blocked.")

        return {
            "allowed": False,
            "clean_query": None,
            "pii_detected": False,
            "events": events,
            "message": "Input validation could not be completed. Please try again."
        }


# --------------------------------------------------
# 4. INPUT GUARDRAILS NODE
# --------------------------------------------------

def input_guardrails_node(state: State):

    print("\nInput Guardrails Stage")

    result = validate_user_input(state["user_query"])

    if not result["allowed"]:

        return {
            "is_blocked": True,
            "final_response": result["message"],
            "pii_detected": result["pii_detected"],
            "guardrail_events": result["events"],
            "blocked_reason": result["message"]
        }

    return {
        "is_blocked": False,
        "clean_query": result["clean_query"],
        "pii_detected": result["pii_detected"],
        "guardrail_events": result["events"],
        "blocked_reason": None
    }


def route_after_guardrails(state: State):

    if state["is_blocked"]:
        return "blocked"

    return "supervisor"


def blocked_response(state: State):

    print("\n Query Blocked")

    return {
        "final_response": state["final_response"]
    }


# --------------------------------------------------
# 5. SUPERVISOR NODE
# --------------------------------------------------

def supervisor(state: State):

    print("\n Supervisor: Selecting Agent")

    user_query = state["clean_query"]

    SYSTEM_PROMPT = """
    You are a supervisor AI.

    Your job is to understand the user's query and select
    the most suitable agent.

    Available agents:

    1. researcher:
       For research questions, technical topics, and
       information gathering.

    2. analyst:
       For calculations, mathematical problems,
       data analysis, and logical reasoning.

    3. writer:
       For writing emails, reports, documentation,
       summaries, and professional content.

    4. general:
       For normal conversations and general questions.

    Select exactly one agent.
    """

    response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents=user_query,
    config=types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=SupervisorResponse
    )
)

    selected_agent = response.parsed.agent

    print("Selected Agent:", selected_agent)

    return {
        "selected_agent": selected_agent
    }


def route_agent(state: State) -> Literal[
    "researcher", "analyst", "writer", "general"
]:

    return state["selected_agent"]


# --------------------------------------------------
# 6. COMMON FUNCTION TO CALL AN AGENT
# --------------------------------------------------

def run_agent(user_query, system_prompt):
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=user_query,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt
        ))

    return response.text


# --------------------------------------------------
# 7. RESEARCHER AGENT
# --------------------------------------------------

def researcher_agent(state: State):

    print("\n Researcher Agent Running")

    SYSTEM_PROMPT = """
    You are a Researcher AI Agent.

    Your job is to explain topics clearly, provide
    detailed information, and organize findings.

    Use reliable knowledge and explain the answer
    in a structured, easy-to-understand way.

    Do not claim that you performed a live web search.
    """

    result = run_agent(state["clean_query"], SYSTEM_PROMPT)

    return {
        "final_response": result
    }


# --------------------------------------------------
# 8. ANALYST AGENT
# --------------------------------------------------

def analyst_agent(state: State):

    print("\n Analyst Agent Running")

    SYSTEM_PROMPT = """
    You are an Analyst AI Agent.

    Your job is to solve mathematical problems,
    calculations, logical problems, and data-related
    questions.

    Explain your reasoning step by step.
    Include the final answer clearly.
    """

    result = run_agent(state["clean_query"], SYSTEM_PROMPT)

    return {
        "final_response": result
    }


# --------------------------------------------------
# 9. WRITER AGENT
# --------------------------------------------------

def writer_agent(state: State):

    print("\n Writer Agent Running")

    SYSTEM_PROMPT = """
    You are a Professional Writing AI Agent.

    Your job is to write emails, reports, documentation,
    summaries, and professional content.

    Follow the user's requested tone and format.
    Return ready-to-use content.
    """

    result = run_agent(state["clean_query"], SYSTEM_PROMPT)

    return {
        "final_response": result
    }


# --------------------------------------------------
# 10. GENERAL AGENT
# --------------------------------------------------

def general_agent(state: State):

    print("\n General Agent Running")

    SYSTEM_PROMPT = """
    You are a helpful General AI Assistant.

    Answer normal user questions in a clear,
    simple, and friendly manner.
    """

    result = run_agent(state["clean_query"], SYSTEM_PROMPT)

    return {
        "final_response": result
    }


# --------------------------------------------------
# 11. BUILD LANGGRAPH WORKFLOW
# --------------------------------------------------

graph_builder = StateGraph(State)


# Add nodes
graph_builder.add_node("input_guardrails", input_guardrails_node)
graph_builder.add_node("blocked_response", blocked_response)
graph_builder.add_node("supervisor", supervisor)

graph_builder.add_node("researcher", researcher_agent)
graph_builder.add_node("analyst", analyst_agent)
graph_builder.add_node("writer", writer_agent)
graph_builder.add_node("general", general_agent)


# Add edges
graph_builder.add_edge(START, "input_guardrails")


# After guardrails: block or continue
graph_builder.add_conditional_edges(
    "input_guardrails",
    route_after_guardrails,
    {
        "blocked": "blocked_response",
        "supervisor": "supervisor"
    }
)


# Blocked query goes directly to END
graph_builder.add_edge("blocked_response", END)


# Supervisor selects an agent
graph_builder.add_conditional_edges(
    "supervisor",
    route_agent,
    {
        "researcher": "researcher",
        "analyst": "analyst",
        "writer": "writer",
        "general": "general"
    }
)


# Every agent returns the response
graph_builder.add_edge("researcher", END)
graph_builder.add_edge("analyst", END)
graph_builder.add_edge("writer", END)
graph_builder.add_edge("general", END)


# Compile graph
graph = graph_builder.compile()


# --------------------------------------------------
# 12. MAIN FUNCTION
# --------------------------------------------------

def main():

    user_input = input("\nEnter your query: ")

    initial_state: State = {
    "user_query": user_input,
    "clean_query": None,
    "is_blocked": False,
    "selected_agent": None,
    "final_response": None,
    "pii_detected": False,
    "guardrail_events": [],
    "blocked_reason": None
}

    result = graph.invoke(initial_state)

    print("\n" + "=" * 50)
    print("FINAL RESPONSE")
    print("=" * 50)

    print(result["final_response"])


if __name__ == "__main__":
    main()

