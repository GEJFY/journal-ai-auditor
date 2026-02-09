"""AI Agent package for JAIA.

This package provides LangGraph-based AI agents for:
- Analysis: Anomaly pattern analysis and insights
- Investigation: Deep-dive into flagged entries
- Documentation: Audit documentation generation
- QA: Question answering about journal data
- Review: Audit finding review and recommendations

Architecture:
- Agents use LangGraph for state management and orchestration
- Each agent has specialized tools for its domain
- Orchestrator coordinates multi-agent workflows
"""

from app.agents.analysis import AnalysisAgent
from app.agents.base import AgentConfig, AgentState, BaseAgent
from app.agents.documentation import DocumentationAgent
from app.agents.investigation import InvestigationAgent
from app.agents.orchestrator import AgentOrchestrator
from app.agents.qa import QAAgent
from app.agents.review import ReviewAgent

__all__ = [
    # Base
    "AgentState",
    "BaseAgent",
    "AgentConfig",
    # Orchestrator
    "AgentOrchestrator",
    # Agents
    "AnalysisAgent",
    "InvestigationAgent",
    "DocumentationAgent",
    "QAAgent",
    "ReviewAgent",
]
