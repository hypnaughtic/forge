"""
Example tools for the LangGraph agent.

Tools are pure functions with clear docstrings that the LLM reads to
decide when and how to use each tool. Keep tools focused, well-documented,
and side-effect-free where possible.
"""

from datetime import datetime
from typing import List

from langchain_core.tools import tool


@tool
def get_current_time() -> str:
    """Get the current date and time in ISO 8601 format.

    Use this tool when the user asks about the current time or date.
    """
    return datetime.now().isoformat()


@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression and return the result.

    Use this tool for arithmetic calculations. The expression should be
    a valid Python math expression (e.g., "2 + 3 * 4", "100 / 7").

    Args:
        expression: A mathematical expression to evaluate.
    """
    # Safety: only allow basic math operations
    allowed_chars = set("0123456789+-*/.() ")
    if not all(c in allowed_chars for c in expression):
        return "Error: expression contains invalid characters. Only numbers and basic operators (+, -, *, /, .) are allowed."

    try:
        result = eval(expression)  # Safe due to character restriction above
        return str(result)
    except Exception as e:
        return f"Error evaluating expression: {e}"


@tool
def search_knowledge_base(query: str) -> str:
    """Search the internal knowledge base for information.

    Use this tool when the user asks a question that might be answered
    by internal documentation or knowledge base articles.

    Args:
        query: The search query to look up.
    """
    # Placeholder — replace with actual knowledge base integration
    return f"No results found for: '{query}'. (This is a placeholder tool — connect your knowledge base here.)"


def get_tools() -> List:
    """Return the list of tools available to the agent."""
    return [get_current_time, calculate, search_knowledge_base]
