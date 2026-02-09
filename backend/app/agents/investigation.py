"""Investigation Agent for deep-dive analysis.

This agent specializes in:
- Investigating specific flagged entries
- Tracing transaction flows
- Identifying related transactions
- Building investigation narratives
"""

from typing import Any

from langchain_core.messages import ToolMessage
from langgraph.graph import END, StateGraph

from app.agents.base import AgentConfig, AgentState, AgentType, BaseAgent
from app.agents.tools import INVESTIGATION_TOOLS

INVESTIGATION_SYSTEM_PROMPT = """あなたはJAIA (Journal entry AI Analyzer) の調査エージェントです。
フラグが立てられた仕訳を深掘り調査し、問題の根本原因を特定します。

## あなたの役割
1. 特定の高リスク仕訳の詳細調査
2. 関連取引の追跡
3. ユーザー行動パターンの分析
4. 勘定科目間の関連性分析
5. 調査所見のまとめ

## 調査の進め方
1. 対象仕訳の詳細を確認
2. 関連する取引を検索
3. 作成者/承認者の活動を確認
4. パターンや異常を特定
5. 所見と推奨事項をまとめる

## 調査観点
- 職務分離違反の有無
- 承認プロセスの適切性
- 金額の妥当性
- タイミングの不自然さ
- 摘要内容の整合性

## 出力形式
調査結果は以下の形式で提供してください：

### 調査対象
- 対象仕訳の概要

### 調査所見
- 発見された問題点

### 関連取引
- 関連する他の取引

### リスク評価
- リスクレベルと根拠

### 推奨アクション
- 次のステップ

日本語で回答してください。
"""


class InvestigationAgent(BaseAgent):
    """Agent for investigating specific flagged entries."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        """Initialize investigation agent.

        Args:
            config: Agent configuration.
        """
        super().__init__(config)
        self.register_tools(INVESTIGATION_TOOLS)

    @property
    def agent_type(self) -> AgentType:
        return AgentType.INVESTIGATION

    @property
    def system_prompt(self) -> str:
        return INVESTIGATION_SYSTEM_PROMPT

    def _build_graph(self) -> StateGraph:
        """Build the investigation agent graph.

        Returns:
            Configured StateGraph.
        """
        graph = StateGraph(AgentState)

        graph.add_node("think", self._think_node)
        graph.add_node("tools", self._tool_node)
        graph.add_node("conclude", self._conclude_node)

        graph.set_entry_point("think")

        graph.add_conditional_edges(
            "think",
            self._should_continue,
            {
                "tools": "tools",
                "end": "conclude",
            },
        )
        graph.add_edge("tools", "think")
        graph.add_edge("conclude", END)

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

    def _conclude_node(self, state: AgentState) -> AgentState:
        """Conclude investigation with findings."""
        return {
            **state,
            "completed_at": state.get("completed_at"),
        }

    async def investigate_entry(
        self,
        gl_detail_id: str,
    ) -> dict[str, Any]:
        """Investigate a specific journal entry.

        Args:
            gl_detail_id: GL detail ID to investigate.

        Returns:
            Investigation result.
        """
        task = f"""
仕訳ID「{gl_detail_id}」について詳細調査を行ってください。

以下の観点で調査してください：
1. 当該仕訳の詳細（金額、勘定科目、摘要など）
2. 作成者と承認者の確認
3. 関連する他の取引
4. 異常性の評価
5. 推奨されるフォローアップ
"""
        result = await self.execute(task, {"gl_detail_id": gl_detail_id})
        return result.to_dict()

    async def investigate_user(
        self,
        user_id: str,
        fiscal_year: int | None = None,
    ) -> dict[str, Any]:
        """Investigate a specific user's activity.

        Args:
            user_id: User ID to investigate.
            fiscal_year: Optional fiscal year filter.

        Returns:
            Investigation result.
        """
        fy_desc = f"{fiscal_year}年度における" if fiscal_year else ""
        task = f"""
ユーザー「{user_id}」の{fy_desc}活動を調査してください。

以下の観点で調査してください：
1. 入力仕訳の件数と金額の傾向
2. 高リスク仕訳の有無
3. 自己承認の有無
4. 使用している勘定科目のパターン
5. 異常な行動パターンの有無
"""
        result = await self.execute(
            task,
            {
                "user_id": user_id,
                "fiscal_year": fiscal_year,
            },
        )
        return result.to_dict()

    async def investigate_rule_violation(
        self,
        rule_id: str,
        fiscal_year: int | None = None,
    ) -> dict[str, Any]:
        """Investigate violations of a specific rule.

        Args:
            rule_id: Rule ID to investigate.
            fiscal_year: Optional fiscal year filter.

        Returns:
            Investigation result.
        """
        fy_desc = f"{fiscal_year}年度の" if fiscal_year else ""
        task = f"""
ルール「{rule_id}」の{fy_desc}違反について調査してください。

以下の観点で調査してください：
1. 違反件数と重大度
2. 違反の傾向とパターン
3. 主な違反者（ユーザー/部門）
4. 共通する特徴
5. 改善のための推奨事項
"""
        result = await self.execute(
            task,
            {
                "rule_id": rule_id,
                "fiscal_year": fiscal_year,
            },
        )
        return result.to_dict()

    async def trace_transaction_flow(
        self,
        journal_id: str,
    ) -> dict[str, Any]:
        """Trace the flow of a transaction.

        Args:
            journal_id: Journal ID to trace.

        Returns:
            Investigation result.
        """
        task = f"""
仕訳「{journal_id}」の取引フローを追跡してください。

以下の観点で調査してください：
1. 当該仕訳の全明細
2. 借方・貸方の対応
3. 関連する前後の取引
4. 資金の流れ
5. 異常な点の有無
"""
        result = await self.execute(task, {"journal_id": journal_id})
        return result.to_dict()
