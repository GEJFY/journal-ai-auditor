"""Base classes for AI agents.

Provides common infrastructure for all JAIA agents using LangGraph.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph

from app.core.config import settings


class AgentType(StrEnum):
    """Types of agents available."""

    ANALYSIS = "analysis"
    INVESTIGATION = "investigation"
    DOCUMENTATION = "documentation"
    QA = "qa"
    REVIEW = "review"
    ORCHESTRATOR = "orchestrator"


class AgentState(TypedDict, total=False):
    """State shared across agent nodes.

    This TypedDict defines the state that flows through the agent graph.
    """

    # Input
    task: str
    context: dict[str, Any]

    # Conversation
    messages: list[BaseMessage]

    # Processing state
    current_agent: str
    step_count: int
    max_steps: int

    # Results
    findings: list[dict[str, Any]]
    recommendations: list[str]
    insights: list[str]

    # Metadata
    started_at: str
    completed_at: str | None
    error: str | None


@dataclass
class AgentConfig:
    """Configuration for an agent."""

    agent_type: AgentType
    model_provider: str = "anthropic"
    model_name: str = "claude-sonnet-4-5"
    temperature: float = 0.0
    max_tokens: int = 4096
    max_steps: int = 10
    verbose: bool = False

    # Custom prompt prefix
    system_prompt_prefix: str = ""

    # Tool configuration
    enable_tools: bool = True
    tool_timeout: int = 30


@dataclass
class AgentResult:
    """Result of agent execution."""

    agent_type: AgentType
    task: str
    success: bool
    findings: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)
    messages: list[dict[str, str]] = field(default_factory=list)
    execution_time_ms: float = 0.0
    step_count: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_type": self.agent_type.value,
            "task": self.task,
            "success": self.success,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "insights": self.insights,
            "messages": self.messages,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "step_count": self.step_count,
            "error": self.error,
        }


def create_llm(config: AgentConfig) -> BaseChatModel:
    """Create LLM instance based on configuration.

    Supports 8 providers: anthropic, openai, azure, azure_foundry,
    bedrock, vertex_ai, google, ollama.

    Args:
        config: Agent configuration.

    Returns:
        LLM instance.

    Raises:
        ValueError: If provider is unknown.
    """
    provider = config.model_provider

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=config.model_name,
            api_key=settings.anthropic_api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    elif provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=config.model_name,
            api_key=settings.openai_api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    elif provider == "azure":
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(
            azure_deployment=settings.azure_openai_deployment,
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    elif provider == "azure_foundry":
        # Azure AI Foundry (OpenAI互換エンドポイント経由)
        # LangChain公式Azure AI Foundryアダプター未提供のためAzureChatOpenAIを使用
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(
            azure_deployment=settings.azure_foundry_deployment or config.model_name,
            azure_endpoint=settings.azure_foundry_endpoint,
            api_key=settings.azure_foundry_api_key,
            api_version=settings.azure_foundry_api_version,
            temperature=config.temperature,
            max_completion_tokens=config.max_tokens,
        )

    elif provider == "bedrock":
        from langchain_aws import ChatBedrockConverse

        return ChatBedrockConverse(
            model=config.model_name,
            region_name=settings.aws_region,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    elif provider == "vertex_ai":
        from langchain_google_vertexai import ChatVertexAI

        return ChatVertexAI(
            model_name=config.model_name,
            project=settings.gcp_project_id,
            location=settings.gcp_location,
            temperature=config.temperature,
            max_output_tokens=config.max_tokens,
        )

    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=config.model_name,
            google_api_key=settings.google_api_key,
            temperature=config.temperature,
            max_output_tokens=config.max_tokens,
        )

    elif provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=config.model_name,
            base_url=settings.ollama_base_url,
            temperature=config.temperature,
            num_predict=config.max_tokens,
        )

    else:
        raise ValueError(
            f"Unknown LLM provider: {provider}. "
            f"Supported: anthropic, openai, azure, azure_foundry, "
            f"bedrock, vertex_ai, google, ollama"
        )


class BaseAgent(ABC):
    """Abstract base class for all agents.

    Provides common functionality for:
    - LLM initialization
    - State management
    - Tool registration
    - Graph building
    """

    def __init__(self, config: AgentConfig | None = None) -> None:
        """Initialize agent.

        Args:
            config: Agent configuration.
        """
        self.config = config or AgentConfig(agent_type=self.agent_type)
        self.llm = create_llm(self.config)
        self.tools: list[Any] = []
        self._graph: StateGraph | None = None

    @property
    @abstractmethod
    def agent_type(self) -> AgentType:
        """Agent type identifier."""
        pass

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt for the agent."""
        pass

    @property
    def full_system_prompt(self) -> str:
        """Complete system prompt with prefix."""
        prefix = self.config.system_prompt_prefix
        if prefix:
            return f"{prefix}\n\n{self.system_prompt}"
        return self.system_prompt

    def register_tool(self, tool: Any) -> None:
        """Register a tool for the agent.

        Args:
            tool: Tool to register.
        """
        self.tools.append(tool)

    def register_tools(self, tools: list[Any]) -> None:
        """Register multiple tools.

        Args:
            tools: List of tools to register.
        """
        self.tools.extend(tools)

    @abstractmethod
    def _build_graph(self) -> StateGraph:
        """Build the agent's LangGraph graph.

        Returns:
            Configured StateGraph.
        """
        pass

    @property
    def graph(self) -> StateGraph:
        """Get or build the agent graph."""
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph

    def _create_initial_state(
        self,
        task: str,
        context: dict[str, Any] | None = None,
    ) -> AgentState:
        """Create initial state for execution.

        Args:
            task: Task description.
            context: Additional context.

        Returns:
            Initial agent state.
        """
        return AgentState(
            task=task,
            context=context or {},
            messages=[
                SystemMessage(content=self.full_system_prompt),
                HumanMessage(content=task),
            ],
            current_agent=self.agent_type.value,
            step_count=0,
            max_steps=self.config.max_steps,
            findings=[],
            recommendations=[],
            insights=[],
            started_at=datetime.now().isoformat(),
            completed_at=None,
            error=None,
        )

    def _think_node(self, state: AgentState) -> AgentState:
        """Main thinking node that calls the LLM.

        Args:
            state: Current state.

        Returns:
            Updated state with LLM response.
        """
        # Bind tools if available
        if self.tools and self.config.enable_tools:
            llm_with_tools = self.llm.bind_tools(self.tools)
        else:
            llm_with_tools = self.llm

        # Call LLM
        response = llm_with_tools.invoke(state["messages"])

        # Update state
        new_messages = list(state["messages"])
        new_messages.append(response)

        return {
            **state,
            "messages": new_messages,
            "step_count": state["step_count"] + 1,
        }

    def _should_continue(self, state: AgentState) -> str:
        """Determine if agent should continue or end.

        Args:
            state: Current state.

        Returns:
            "continue" or "end".
        """
        # Check step limit
        if state["step_count"] >= state["max_steps"]:
            return "end"

        # Check for error
        if state.get("error"):
            return "end"

        # Check last message for tool calls
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"

        return "end"

    async def execute(
        self,
        task: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Execute the agent on a task.

        Args:
            task: Task description.
            context: Additional context.

        Returns:
            Agent execution result.
        """
        import time

        start_time = time.perf_counter()

        try:
            # Create initial state
            state = self._create_initial_state(task, context)

            # Compile and run graph
            compiled = self.graph.compile()
            final_state = await compiled.ainvoke(state)

            # Extract results
            result = AgentResult(
                agent_type=self.agent_type,
                task=task,
                success=True,
                findings=final_state.get("findings", []),
                recommendations=final_state.get("recommendations", []),
                insights=final_state.get("insights", []),
                messages=[
                    {
                        "role": "assistant" if isinstance(m, AIMessage) else "user",
                        "content": m.content,
                    }
                    for m in final_state.get("messages", [])
                    if not isinstance(m, SystemMessage)
                ],
                step_count=final_state.get("step_count", 0),
            )

        except Exception as e:
            result = AgentResult(
                agent_type=self.agent_type,
                task=task,
                success=False,
                error=str(e),
            )

        result.execution_time_ms = (time.perf_counter() - start_time) * 1000
        return result

    def execute_sync(
        self,
        task: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Synchronous execution wrapper.

        Args:
            task: Task description.
            context: Additional context.

        Returns:
            Agent execution result.
        """
        import asyncio

        return asyncio.run(self.execute(task, context))
