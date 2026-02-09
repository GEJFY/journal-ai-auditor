"""Analysis Agent for anomaly pattern analysis.

This agent specializes in:
- Identifying anomaly patterns in journal data
- Analyzing risk distributions
- Discovering correlations between anomalies
- Generating analytical insights
"""

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph

from app.agents.base import AgentConfig, AgentState, AgentType, BaseAgent
from app.agents.tools import ANALYSIS_TOOLS

ANALYSIS_SYSTEM_PROMPT = """あなたはJAIA (Journal entry AI Analyzer) の分析エージェントです。
仕訳データの異常パターンを分析し、監査に役立つ洞察を提供します。

## あなたの役割
1. 高リスク仕訳の特定と分析
2. 異常パターンの発見と説明
3. リスク分布の分析
4. 会計期間間の比較分析
5. ベンフォードの法則に基づく分析

## 分析の進め方
1. まずダッシュボードKPIで全体像を把握
2. 高リスク仕訳を確認
3. 特定のパターンを深掘り
4. 洞察をまとめる

## 出力形式
分析結果は以下の形式で提供してください：

### 発見事項 (Findings)
- 具体的な数値とともに発見事項を記載

### 洞察 (Insights)
- データから得られた重要な洞察

### 推奨事項 (Recommendations)
- 監査チームへの推奨アクション

日本語で回答してください。
"""


class AnalysisAgent(BaseAgent):
    """Agent for analyzing anomaly patterns in journal data."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        """Initialize analysis agent.

        Args:
            config: Agent configuration.
        """
        super().__init__(config)
        self.register_tools(ANALYSIS_TOOLS)

    @property
    def agent_type(self) -> AgentType:
        return AgentType.ANALYSIS

    @property
    def system_prompt(self) -> str:
        return ANALYSIS_SYSTEM_PROMPT

    def _build_graph(self) -> StateGraph:
        """Build the analysis agent graph.

        Returns:
            Configured StateGraph.
        """
        # Create graph
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("think", self._think_node)
        graph.add_node("tools", self._tool_node)
        graph.add_node("summarize", self._summarize_node)

        # Set entry point
        graph.set_entry_point("think")

        # Add edges
        graph.add_conditional_edges(
            "think",
            self._should_continue,
            {
                "tools": "tools",
                "end": "summarize",
            }
        )
        graph.add_edge("tools", "think")
        graph.add_edge("summarize", END)

        return graph

    def _tool_node(self, state: AgentState) -> AgentState:
        """Execute tool calls from the last message.

        Args:
            state: Current state.

        Returns:
            Updated state with tool results.
        """
        last_message = state["messages"][-1]
        new_messages = list(state["messages"])

        if hasattr(last_message, "tool_calls"):
            for tool_call in last_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                # Find and execute tool
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

                # Add tool message
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

    def _summarize_node(self, state: AgentState) -> AgentState:
        """Summarize findings and generate final structured output.

        Uses the LLM to extract structured findings from the conversation.

        Args:
            state: Current state.

        Returns:
            Updated state with structured findings, insights, recommendations.
        """
        from datetime import datetime

        # Collect all AI messages as analysis context
        ai_contents = []
        for msg in state["messages"]:
            if isinstance(msg, AIMessage) and msg.content:
                ai_contents.append(msg.content)

        combined_analysis = "\n---\n".join(ai_contents)

        # Use LLM to extract structured output from the analysis
        extraction_prompt = f"""以下の分析結果から、構造化された監査所見を抽出してください。

分析結果:
{combined_analysis}

以下のJSON形式で回答してください（JSON以外は出力しないでください）：
{{
  "findings": [
    {{"id": "F-001", "title": "タイトル", "description": "説明", "severity": "high/medium/low", "affected_amount": 0, "affected_count": 0}}
  ],
  "insights": ["洞察1", "洞察2"],
  "recommendations": ["推奨事項1", "推奨事項2"]
}}"""

        try:
            response = self.llm.invoke([
                SystemMessage(content="あなたは監査所見を構造化するアシスタントです。必ず有効なJSONで回答してください。"),
                HumanMessage(content=extraction_prompt),
            ])

            import json
            content = response.content.strip()
            # Extract JSON from markdown code block if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            parsed = json.loads(content)
            findings = parsed.get("findings", [])
            insights = parsed.get("insights", [])
            recommendations = parsed.get("recommendations", [])
        except Exception:
            # Fallback: extract sections from text using simple parsing
            findings = state.get("findings", [])
            insights = state.get("insights", [])
            recommendations = state.get("recommendations", [])

            for content in ai_contents:
                lines = content.split("\n")
                current_section = None
                for line in lines:
                    stripped = line.strip()
                    if "発見事項" in stripped or "Findings" in stripped:
                        current_section = "findings"
                    elif "洞察" in stripped or "Insights" in stripped:
                        current_section = "insights"
                    elif "推奨事項" in stripped or "Recommendations" in stripped:
                        current_section = "recommendations"
                    elif stripped.startswith("- ") and current_section:
                        item = stripped[2:].strip()
                        if current_section == "findings":
                            findings.append({"title": item, "description": item, "severity": "medium"})
                        elif current_section == "insights":
                            insights.append(item)
                        elif current_section == "recommendations":
                            recommendations.append(item)

        return {
            **state,
            "findings": findings,
            "insights": insights,
            "recommendations": recommendations,
            "completed_at": datetime.now().isoformat(),
        }

    async def analyze_risk_distribution(
        self,
        fiscal_year: int,
    ) -> dict[str, Any]:
        """Analyze risk score distribution.

        Args:
            fiscal_year: Fiscal year to analyze.

        Returns:
            Analysis result.
        """
        task = f"""
{fiscal_year}年度の仕訳データについて、リスクスコアの分布を分析してください。

以下の観点で分析を行ってください：
1. 高リスク仕訳の件数と金額
2. リスクカテゴリ別の分布
3. 異常なパターンの特定
4. 改善が必要な領域の特定
"""
        result = await self.execute(task, {"fiscal_year": fiscal_year})
        return result.to_dict()

    async def analyze_benford_compliance(
        self,
        fiscal_year: int,
    ) -> dict[str, Any]:
        """Analyze Benford's Law compliance.

        Args:
            fiscal_year: Fiscal year to analyze.

        Returns:
            Analysis result.
        """
        task = f"""
{fiscal_year}年度の仕訳データについて、ベンフォードの法則への準拠状況を分析してください。

以下の観点で分析を行ってください：
1. 第1桁の分布と期待値との比較
2. 乖離が大きい桁の特定
3. 不正の可能性がある領域の示唆
4. 追加調査が必要な取引の特定
"""
        result = await self.execute(task, {"fiscal_year": fiscal_year})
        return result.to_dict()

    async def compare_periods(
        self,
        fiscal_year: int,
        account_prefix: str | None = None,
    ) -> dict[str, Any]:
        """Compare metrics across accounting periods.

        Args:
            fiscal_year: Fiscal year to analyze.
            account_prefix: Optional account filter.

        Returns:
            Analysis result.
        """
        account_desc = f"勘定科目{account_prefix}xxx" if account_prefix else "全勘定科目"
        task = f"""
{fiscal_year}年度の{account_desc}について、会計期間ごとの比較分析を行ってください。

以下の観点で分析を行ってください：
1. 期間ごとの取引量と金額の推移
2. リスクスコアの期間変動
3. 期末集中の有無
4. 異常な期間の特定
"""
        result = await self.execute(task, {
            "fiscal_year": fiscal_year,
            "account_prefix": account_prefix,
        })
        return result.to_dict()
