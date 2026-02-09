"""Documentation Agent for audit documentation generation.

This agent specializes in:
- Generating audit finding documentation
- Creating summary reports
- Drafting management letters
- Preparing working papers
"""

from typing import Any

from langchain_core.messages import ToolMessage
from langgraph.graph import END, StateGraph

from app.agents.base import AgentConfig, AgentState, AgentType, BaseAgent
from app.agents.tools import DOCUMENTATION_TOOLS

DOCUMENTATION_SYSTEM_PROMPT = """あなたはJAIA (Journal entry AI Analyzer) の文書化エージェントです。
監査調書や報告書の作成を支援します。

## あなたの役割
1. 監査発見事項の文書化
2. 要約レポートの作成
3. マネジメントレターの草案作成
4. 調書の整理と構造化

## 文書作成の原則
- 客観的で事実に基づく記述
- 明確で簡潔な表現
- 適切な根拠の提示
- 監査基準に準拠した形式

## 出力形式

### 監査発見事項
1. 発見事項の要約
2. 詳細な説明
3. 根拠となるデータ
4. リスク評価
5. 推奨事項

### 影響度評価
- 財務的影響
- 内部統制への影響
- コンプライアンスへの影響

日本語で回答してください。文書は正式な監査調書として使用可能な品質で作成してください。
"""


class DocumentationAgent(BaseAgent):
    """Agent for generating audit documentation."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        """Initialize documentation agent.

        Args:
            config: Agent configuration.
        """
        super().__init__(config)
        self.register_tools(DOCUMENTATION_TOOLS)

    @property
    def agent_type(self) -> AgentType:
        return AgentType.DOCUMENTATION

    @property
    def system_prompt(self) -> str:
        return DOCUMENTATION_SYSTEM_PROMPT

    def _build_graph(self) -> StateGraph:
        """Build the documentation agent graph."""
        graph = StateGraph(AgentState)

        graph.add_node("gather", self._gather_node)
        graph.add_node("think", self._think_node)
        graph.add_node("tools", self._tool_node)
        graph.add_node("document", self._document_node)

        graph.set_entry_point("gather")

        graph.add_edge("gather", "think")
        graph.add_conditional_edges(
            "think",
            self._should_continue,
            {
                "tools": "tools",
                "end": "document",
            },
        )
        graph.add_edge("tools", "think")
        graph.add_edge("document", END)

        return graph

    def _gather_node(self, state: AgentState) -> AgentState:
        """Gather context for documentation."""
        return state

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

    def _document_node(self, state: AgentState) -> AgentState:
        """Finalize documentation."""
        return {
            **state,
            "completed_at": state.get("completed_at"),
        }

    async def generate_finding_report(
        self,
        fiscal_year: int,
        finding_type: str = "high_risk",
    ) -> dict[str, Any]:
        """Generate a finding report.

        Args:
            fiscal_year: Fiscal year.
            finding_type: Type of finding (high_risk, self_approval, etc.).

        Returns:
            Generated report.
        """
        task = f"""
{fiscal_year}年度の{finding_type}に関する監査発見事項報告書を作成してください。

以下の項目を含めてください：
1. エグゼクティブサマリー
2. 発見事項の詳細
3. 影響度評価
4. 根本原因分析
5. 改善推奨事項
6. 経営陣への提言
"""
        result = await self.execute(
            task,
            {
                "fiscal_year": fiscal_year,
                "finding_type": finding_type,
            },
        )
        return result.to_dict()

    async def generate_summary_report(
        self,
        fiscal_year: int,
    ) -> dict[str, Any]:
        """Generate a summary report of all findings.

        Args:
            fiscal_year: Fiscal year.

        Returns:
            Summary report.
        """
        task = f"""
{fiscal_year}年度の仕訳検証結果サマリーレポートを作成してください。

以下の項目を含めてください：
1. 分析対象の概要（仕訳件数、金額等）
2. リスク分布の概要
3. 主要な発見事項のサマリー
4. カテゴリ別の分析結果
5. 総合評価
6. 次のステップ
"""
        result = await self.execute(task, {"fiscal_year": fiscal_year})
        return result.to_dict()

    async def draft_management_letter(
        self,
        fiscal_year: int,
        findings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Draft a management letter.

        Args:
            fiscal_year: Fiscal year.
            findings: List of findings to include.

        Returns:
            Draft management letter.
        """
        findings_summary = "\n".join(
            [
                f"- {f.get('title', 'Finding')}: {f.get('description', '')}"
                for f in findings
            ]
        )

        task = f"""
以下の発見事項に基づいて、{fiscal_year}年度のマネジメントレターの草案を作成してください。

発見事項：
{findings_summary}

以下の形式で作成してください：
1. 宛先と日付
2. 目的と範囲
3. 発見事項の要約
4. 詳細な発見事項と推奨事項
5. 経営陣の対応期限
6. 結語
"""
        result = await self.execute(
            task,
            {
                "fiscal_year": fiscal_year,
                "findings": findings,
            },
        )
        return result.to_dict()
