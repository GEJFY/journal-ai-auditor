"""QA Agent for question answering about journal data.

This agent specializes in:
- Answering questions about journal entries
- Explaining analysis results
- Providing context on audit findings
- Interactive data exploration
"""

from typing import Any

from langchain_core.messages import ToolMessage
from langgraph.graph import END, StateGraph

from app.agents.base import AgentConfig, AgentState, AgentType, BaseAgent
from app.agents.tools import QA_TOOLS

QA_SYSTEM_PROMPT = """あなたはJAIA (Journal entry AI Analyzer) の質問応答エージェントです。
監査人からの仕訳データに関する質問に回答します。

## あなたの役割
1. 仕訳データに関する質問への回答
2. 分析結果の説明
3. 監査発見事項の解説
4. データの検索と要約

## 回答の原則
- 正確で事実に基づく回答
- 必要に応じてツールを使用してデータを取得
- 不明な点は明確に伝える
- 適切なコンテキストを提供

## 対応可能な質問例
- 「○○勘定の取引を見せて」
- 「高リスク仕訳はいくつある？」
- 「△△さんの入力した仕訳を確認したい」
- 「前期と今期を比較して」
- 「この異常の原因は何？」

日本語で簡潔かつ正確に回答してください。
"""


class QAAgent(BaseAgent):
    """Agent for answering questions about journal data."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        """Initialize QA agent.

        Args:
            config: Agent configuration.
        """
        super().__init__(config)
        self.register_tools(QA_TOOLS)

    @property
    def agent_type(self) -> AgentType:
        return AgentType.QA

    @property
    def system_prompt(self) -> str:
        return QA_SYSTEM_PROMPT

    def _build_graph(self) -> StateGraph:
        """Build the QA agent graph."""
        graph = StateGraph(AgentState)

        graph.add_node("think", self._think_node)
        graph.add_node("tools", self._tool_node)
        graph.add_node("respond", self._respond_node)

        graph.set_entry_point("think")

        graph.add_conditional_edges(
            "think",
            self._should_continue,
            {
                "tools": "tools",
                "end": "respond",
            }
        )
        graph.add_edge("tools", "think")
        graph.add_edge("respond", END)

        return graph

    def _tool_node(self, state: AgentState) -> AgentState:
        """Execute tool calls."""
        last_message = state["messages"][-1]
        new_messages = list(state["messages"])

        if hasattr(last_message, "tool_calls"):
            for tool_call in last_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                result = None
                for tool in self.tools:
                    if tool.name == tool_name:
                        try:
                            result = tool.invoke(tool_args)
                        except Exception as e:
                            result = f"Error: {str(e)}"
                        break

                if result is None:
                    result = f"Unknown tool: {tool_name}"

                new_messages.append(
                    ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call["id"],
                    )
                )

        return {
            **state,
            "messages": new_messages,
            "step_count": state["step_count"] + 1,
        }

    def _respond_node(self, state: AgentState) -> AgentState:
        """Prepare final response."""
        return {
            **state,
            "completed_at": state.get("completed_at"),
        }

    async def ask(
        self,
        question: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ask a question about journal data.

        Args:
            question: The question to answer.
            context: Optional context (e.g., fiscal_year).

        Returns:
            Answer with supporting data.
        """
        result = await self.execute(question, context)
        return result.to_dict()

    async def explain_finding(
        self,
        finding_id: str,
    ) -> dict[str, Any]:
        """Explain a specific audit finding.

        Args:
            finding_id: Finding or rule ID to explain.

        Returns:
            Explanation of the finding.
        """
        task = f"""
発見事項「{finding_id}」について説明してください。

以下の点を含めてください：
1. この発見事項の意味
2. なぜ問題なのか
3. どのような影響があるか
4. 一般的な原因
"""
        result = await self.execute(task, {"finding_id": finding_id})
        return result.to_dict()

    async def search_entries(
        self,
        search_criteria: str,
    ) -> dict[str, Any]:
        """Search for journal entries matching criteria.

        Args:
            search_criteria: Natural language search criteria.

        Returns:
            Matching entries with explanation.
        """
        task = f"""
以下の条件に合う仕訳を検索してください：
{search_criteria}

検索結果を分かりやすく整理して表示してください。
"""
        result = await self.execute(task)
        return result.to_dict()
