"""Review Agent for audit finding review.

This agent specializes in:
- Reviewing and validating audit findings
- Assessing risk levels
- Prioritizing findings
- Suggesting remediation actions
"""

from typing import Any

from langchain_core.messages import ToolMessage
from langgraph.graph import END, StateGraph

from app.agents.base import AgentConfig, AgentState, AgentType, BaseAgent
from app.agents.tools import REVIEW_TOOLS

REVIEW_SYSTEM_PROMPT = """あなたはJAIA (Journal entry AI Analyzer) のレビューエージェントです。
監査発見事項のレビューと評価を行います。

## あなたの役割
1. 発見事項の妥当性検証
2. リスクレベルの評価
3. 発見事項の優先順位付け
4. 是正措置の提案
5. 経営陣への報告内容のレビュー

## レビューの観点
- 発見事項は事実に基づいているか
- リスク評価は適切か
- 根本原因は正しく特定されているか
- 推奨事項は実行可能か
- 報告内容は明確か

## リスク評価基準
- Critical: 即座に対応が必要、重大な財務影響
- High: 早急な対応が必要、重要な内部統制の欠陥
- Medium: 計画的な対応が必要、改善の余地あり
- Low: 認識すべき事項、軽微な問題

日本語で回答してください。
"""


class ReviewAgent(BaseAgent):
    """Agent for reviewing and validating audit findings."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        """Initialize review agent.

        Args:
            config: Agent configuration.
        """
        super().__init__(config)
        self.register_tools(REVIEW_TOOLS)

    @property
    def agent_type(self) -> AgentType:
        return AgentType.REVIEW

    @property
    def system_prompt(self) -> str:
        return REVIEW_SYSTEM_PROMPT

    def _build_graph(self) -> StateGraph:
        """Build the review agent graph."""
        graph = StateGraph(AgentState)

        graph.add_node("think", self._think_node)
        graph.add_node("tools", self._tool_node)
        graph.add_node("evaluate", self._evaluate_node)

        graph.set_entry_point("think")

        graph.add_conditional_edges(
            "think",
            self._should_continue,
            {
                "tools": "tools",
                "end": "evaluate",
            },
        )
        graph.add_edge("tools", "think")
        graph.add_edge("evaluate", END)

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

    def _evaluate_node(self, state: AgentState) -> AgentState:
        """Finalize evaluation."""
        return {
            **state,
            "completed_at": state.get("completed_at"),
        }

    async def review_findings(
        self,
        fiscal_year: int,
    ) -> dict[str, Any]:
        """Review all findings for a fiscal year.

        Args:
            fiscal_year: Fiscal year to review.

        Returns:
            Review results.
        """
        task = f"""
{fiscal_year}年度の監査発見事項をレビューしてください。

以下の観点でレビューを行ってください：
1. 発見事項の概要把握
2. リスクレベルの妥当性評価
3. 優先順位の設定
4. 経営陣への報告推奨事項
"""
        result = await self.execute(task, {"fiscal_year": fiscal_year})
        return result.to_dict()

    async def prioritize_findings(
        self,
        fiscal_year: int,
    ) -> dict[str, Any]:
        """Prioritize findings by importance.

        Args:
            fiscal_year: Fiscal year.

        Returns:
            Prioritized list of findings.
        """
        task = f"""
{fiscal_year}年度の発見事項を優先順位付けしてください。

以下の基準で優先順位を設定してください：
1. 財務的影響の大きさ
2. 内部統制への影響
3. コンプライアンスリスク
4. 再発可能性

上位10件の発見事項と、その優先順位の根拠を説明してください。
"""
        result = await self.execute(task, {"fiscal_year": fiscal_year})
        return result.to_dict()

    async def suggest_remediation(
        self,
        finding_type: str,
    ) -> dict[str, Any]:
        """Suggest remediation actions for a finding type.

        Args:
            finding_type: Type of finding.

        Returns:
            Remediation suggestions.
        """
        task = f"""
「{finding_type}」タイプの発見事項に対する是正措置を提案してください。

以下の項目を含めてください：
1. 短期的な対応（即時対応）
2. 中期的な対応（3-6ヶ月）
3. 長期的な対応（システム・プロセス改善）
4. 予防措置
5. モニタリング方法
"""
        result = await self.execute(task, {"finding_type": finding_type})
        return result.to_dict()

    async def validate_risk_assessment(
        self,
        findings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Validate risk assessment of findings.

        Args:
            findings: List of findings with risk assessments.

        Returns:
            Validation results.
        """
        findings_summary = "\n".join(
            [
                f"- {f.get('id', 'N/A')}: {f.get('description', '')} [Risk: {f.get('risk_level', 'Unknown')}]"
                for f in findings
            ]
        )

        task = f"""
以下の発見事項のリスク評価を検証してください：

{findings_summary}

各発見事項について：
1. 現在のリスク評価は適切か
2. 評価を変更すべき場合、その理由
3. 追加で考慮すべきリスク要因
"""
        result = await self.execute(task, {"findings": findings})
        return result.to_dict()
