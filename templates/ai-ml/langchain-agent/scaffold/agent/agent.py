"""
LangGraph agent that uses GatewayLLM for all LLM calls.

This agent routes every LLM call through llm-gateway via the GatewayLLM
class. It NEVER calls LLM providers directly.
"""

from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from agent.gateway_llm import GatewayLLM
from agent.tools import get_tools
from agent.config import settings


class AgentState(TypedDict):
    """Typed state for the agent graph."""
    messages: Annotated[Sequence[BaseMessage], add_messages]


def create_agent() -> StateGraph:
    """Create and return the LangGraph agent.

    The agent uses GatewayLLM (NOT ChatOpenAI or ChatAnthropic) to ensure
    all LLM calls are routed through llm-gateway.
    """
    # Initialize LLM through gateway — this is the ONLY correct way
    llm = GatewayLLM(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
    )

    # Bind tools to the LLM
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)

    # Define the agent node
    def call_model(state: AgentState) -> dict:
        """Invoke the LLM with the current message history."""
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    # Define the routing function
    def should_continue(state: AgentState) -> str:
        """Determine whether to call tools or end the conversation."""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    # Build the graph
    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(tools))

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()


def run_agent(user_input: str) -> str:
    """Run the agent with a user message and return the final response."""
    agent = create_agent()
    result = agent.invoke({
        "messages": [HumanMessage(content=user_input)],
    })
    return result["messages"][-1].content


if __name__ == "__main__":
    # Simple interactive loop for testing
    print("Agent ready. Type 'quit' to exit.")
    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ("quit", "exit"):
            break
        response = run_agent(user_input)
        print(f"\nAgent: {response}")
