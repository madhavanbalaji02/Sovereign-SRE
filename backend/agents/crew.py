"""
SRE CrewAI Crew
===============
CrewAI crew with Senior SRE and System Researcher agents.
"""

import os
from typing import Optional

from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from langchain_groq import ChatGroq

from backend.rag.query_engine import query_codebase, create_query_engine

# =============================================================================
# CONFIGURATION
# =============================================================================

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


def _get_llm() -> ChatGroq:
    return ChatGroq(
        model=GROQ_MODEL,
        api_key=GROQ_API_KEY,
        temperature=0.1,
    )


# =============================================================================
# RAG TOOL FOR AGENTS
# =============================================================================

@tool("query_codebase")
def codebase_query_tool(query: str) -> str:
    """
    Query the indexed codebase to find relevant code and documentation.
    Use this to understand how specific features are implemented,
    find error handling patterns, or locate configuration files.
    
    Args:
        query: Natural language question about the codebase
        
    Returns:
        Relevant code snippets and explanations
    """
    import asyncio
    
    try:
        engine = create_query_engine()
        result = asyncio.run(query_codebase(query, engine))
        
        response = f"Answer: {result['response']}\n\nSources:\n"
        for src in result['sources'][:3]:
            response += f"- {src['file_path']}: {src['text_snippet'][:100]}...\n"
        
        return response
    except Exception as e:
        return f"Error querying codebase: {str(e)}"


# =============================================================================
# AGENT DEFINITIONS
# =============================================================================

def create_senior_sre_agent() -> Agent:
    """
    Senior SRE Agent - Expert in system operations and incident response.
    """
    return Agent(
        role="Senior Site Reliability Engineer",
        goal="Diagnose system issues quickly and accurately, proposing effective fixes",
        backstory="""You are a seasoned SRE with 10+ years of experience managing 
        large-scale distributed systems. You've seen every type of failure mode 
        and have developed intuition for quickly identifying root causes. You 
        communicate clearly and prioritize solutions by impact and urgency.""",
        verbose=True,
        allow_delegation=True,
        llm=_get_llm(),
    )


def create_system_researcher_agent() -> Agent:
    """
    System Researcher Agent - Expert in codebase analysis and documentation.
    Has access to the RAG tool for querying the codebase.
    """
    return Agent(
        role="System Researcher",
        goal="Analyze the codebase to find relevant code patterns and understand implementation details",
        backstory="""You are a meticulous researcher who excels at understanding 
        complex codebases. You use the codebase query tool to find relevant 
        implementations, error handling patterns, and configuration details. 
        You provide detailed, accurate information to support the SRE's diagnosis.""",
        verbose=True,
        allow_delegation=False,
        tools=[codebase_query_tool],
        llm=_get_llm(),
    )


# =============================================================================
# TASK DEFINITIONS
# =============================================================================

def create_analysis_task(issues: list[str], logs: list[dict]) -> Task:
    """Create the root cause analysis task"""
    return Task(
        description=f"""Analyze the following system issues and determine the root cause:

Issues Detected:
{chr(10).join(f'- {issue}' for issue in issues)}

Recent Logs:
{chr(10).join(f"[{log.get('level', 'INFO')}] {log.get('message', 'No message')}" for log in logs[-5:])}

Your analysis should include:
1. The most likely root cause
2. Affected components and files
3. Confidence level (0-100%)
4. Recommended fix approach

Use the codebase query tool to find relevant implementation details.""",
        expected_output="""A structured root cause analysis including:
- Summary of the root cause
- List of affected files
- Error type classification
- Confidence percentage
- Recommended fix with specific code changes""",
    )


def create_research_task(issues: list[str]) -> Task:
    """Create the codebase research task"""
    return Task(
        description=f"""Research the codebase to understand how the following areas are implemented:

Issues to research:
{chr(10).join(f'- {issue}' for issue in issues)}

Use the codebase query tool to:
1. Find the relevant file(s) where the error originates
2. Understand the current error handling implementation
3. Identify similar patterns in the codebase
4. Find any related configuration or environment variables""",
        expected_output="""A detailed research report including:
- Relevant file paths and code snippets
- Current implementation patterns
- Configuration details
- Suggestions for where fixes should be applied""",
    )


# =============================================================================
# CREW FACTORY
# =============================================================================

def create_sre_crew(
    issues: Optional[list[str]] = None,
    logs: Optional[list[dict]] = None,
) -> Crew:
    """
    Create the SRE crew with Senior SRE and System Researcher agents.
    
    Args:
        issues: List of detected issues to analyze
        logs: Recent log entries for context
        
    Returns:
        Configured CrewAI crew
    """
    issues = issues or ["Unknown error detected"]
    logs = logs or []
    
    # Create agents
    senior_sre = create_senior_sre_agent()
    researcher = create_system_researcher_agent()
    
    # Create tasks
    research_task = create_research_task(issues)
    analysis_task = create_analysis_task(issues, logs)
    
    # Assign agents to tasks
    research_task.agent = researcher
    analysis_task.agent = senior_sre
    
    # Create crew
    crew = Crew(
        agents=[senior_sre, researcher],
        tasks=[research_task, analysis_task],
        process=Process.sequential,  # Research first, then analysis
        verbose=True,
    )
    
    return crew


async def run_sre_crew(issues: list[str], logs: list[dict]) -> dict:
    """
    Run the SRE crew and return the analysis result.
    
    Args:
        issues: List of detected issues
        logs: Recent log entries
        
    Returns:
        Crew execution result
    """
    crew = create_sre_crew(issues, logs)
    
    try:
        result = await crew.kickoff_async()
        return {
            "success": True,
            "result": str(result),
            "tasks_completed": len(crew.tasks),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "tasks_completed": 0,
        }
