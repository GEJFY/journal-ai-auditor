"""Agent Orchestrator for multi-agent workflows.

Coordinates the execution of multiple agents for complex audit tasks:
- Full audit workflow (analysis -> investigation -> documentation)
- Interactive Q&A sessions
- Automated finding review
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from app.agents.base import AgentConfig, AgentState, AgentType, BaseAgent
from app.agents.analysis import AnalysisAgent
from app.agents.investigation import InvestigationAgent
from app.agents.documentation import DocumentationAgent
from app.agents.qa import QAAgent
from app.agents.review import ReviewAgent


ORCHESTRATOR_SYSTEM_PROMPT = """あなたはJAIA (Journal entry AI Analyzer) のオーケストレーターです。
複数の専門エージェントを調整して、複雑な監査タスクを実行します。

## 利用可能なエージェント
1. 分析エージェント (AnalysisAgent): 異常パターンの分析
2. 調査エージェント (InvestigationAgent): 特定項目の深掘り調査
3. 文書化エージェント (DocumentationAgent): 報告書作成
4. 質問応答エージェント (QAAgent): 対話的な質問対応
5. レビューエージェント (ReviewAgent): 発見事項のレビュー

## ワークフロー
タスクに応じて適切なエージェントを選択し、順次または並列で実行します。

日本語で回答してください。
"""


@dataclass
class WorkflowResult:
    """Result of a multi-agent workflow."""

    workflow_id: str
    workflow_type: str
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    agent_results: dict[str, Any] = field(default_factory=dict)
    final_output: Optional[str] = None
    success: bool = False
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "agent_results": self.agent_results,
            "final_output": self.final_output,
            "success": self.success,
            "error": self.error,
        }


class AgentOrchestrator:
    """Orchestrates multi-agent workflows."""

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
    ) -> None:
        """Initialize orchestrator.

        Args:
            config: Base agent configuration.
        """
        self.config = config or AgentConfig(agent_type=AgentType.ORCHESTRATOR)

        # Initialize agents
        self.analysis_agent = AnalysisAgent(config)
        self.investigation_agent = InvestigationAgent(config)
        self.documentation_agent = DocumentationAgent(config)
        self.qa_agent = QAAgent(config)
        self.review_agent = ReviewAgent(config)

    async def run_full_audit_workflow(
        self,
        fiscal_year: int,
    ) -> WorkflowResult:
        """Run a complete audit workflow.

        Sequence:
        1. Analysis: Identify high-risk areas
        2. Investigation: Deep-dive into findings
        3. Review: Validate and prioritize findings
        4. Documentation: Generate reports

        Args:
            fiscal_year: Fiscal year to audit.

        Returns:
            Workflow result with all agent outputs.
        """
        import uuid
        result = WorkflowResult(
            workflow_id=str(uuid.uuid4()),
            workflow_type="full_audit",
        )

        try:
            # Step 1: Analysis
            analysis_result = await self.analysis_agent.analyze_risk_distribution(
                fiscal_year
            )
            result.agent_results["analysis"] = analysis_result

            # Step 2: Investigation of high-risk findings
            investigation_result = await self.investigation_agent.execute(
                f"{fiscal_year}年度の高リスク仕訳上位10件を調査してください",
                {"fiscal_year": fiscal_year}
            )
            result.agent_results["investigation"] = investigation_result.to_dict()

            # Step 3: Review findings
            review_result = await self.review_agent.review_findings(fiscal_year)
            result.agent_results["review"] = review_result

            # Step 4: Generate documentation
            doc_result = await self.documentation_agent.generate_summary_report(
                fiscal_year
            )
            result.agent_results["documentation"] = doc_result

            result.success = True
            result.final_output = "監査ワークフローが正常に完了しました"

        except Exception as e:
            result.error = str(e)
            result.success = False

        result.completed_at = datetime.now()
        return result

    async def run_investigation_workflow(
        self,
        target_type: str,
        target_id: str,
        fiscal_year: Optional[int] = None,
    ) -> WorkflowResult:
        """Run an investigation workflow.

        Args:
            target_type: Type of target (entry, user, rule).
            target_id: ID of the target.
            fiscal_year: Optional fiscal year filter.

        Returns:
            Workflow result.
        """
        import uuid
        result = WorkflowResult(
            workflow_id=str(uuid.uuid4()),
            workflow_type="investigation",
        )

        try:
            if target_type == "entry":
                inv_result = await self.investigation_agent.investigate_entry(target_id)
            elif target_type == "user":
                inv_result = await self.investigation_agent.investigate_user(
                    target_id, fiscal_year
                )
            elif target_type == "rule":
                inv_result = await self.investigation_agent.investigate_rule_violation(
                    target_id, fiscal_year
                )
            else:
                raise ValueError(f"Unknown target type: {target_type}")

            result.agent_results["investigation"] = inv_result
            result.success = True
            result.final_output = "調査が完了しました"

        except Exception as e:
            result.error = str(e)
            result.success = False

        result.completed_at = datetime.now()
        return result

    async def run_qa_session(
        self,
        question: str,
        context: Optional[dict[str, Any]] = None,
    ) -> WorkflowResult:
        """Run an interactive Q&A session.

        Args:
            question: User's question.
            context: Optional context.

        Returns:
            Workflow result with answer.
        """
        import uuid
        result = WorkflowResult(
            workflow_id=str(uuid.uuid4()),
            workflow_type="qa",
        )

        try:
            qa_result = await self.qa_agent.ask(question, context)
            result.agent_results["qa"] = qa_result
            result.success = True

            # Extract the answer from the last message
            if qa_result.get("messages"):
                last_msg = qa_result["messages"][-1]
                if last_msg.get("role") == "assistant":
                    result.final_output = last_msg.get("content", "")

        except Exception as e:
            result.error = str(e)
            result.success = False

        result.completed_at = datetime.now()
        return result

    async def run_documentation_workflow(
        self,
        fiscal_year: int,
        doc_type: str = "summary",
        findings: Optional[list[dict[str, Any]]] = None,
    ) -> WorkflowResult:
        """Run a documentation workflow.

        Args:
            fiscal_year: Fiscal year.
            doc_type: Type of document (summary, finding, management_letter).
            findings: Optional list of findings for management letter.

        Returns:
            Workflow result with generated document.
        """
        import uuid
        result = WorkflowResult(
            workflow_id=str(uuid.uuid4()),
            workflow_type="documentation",
        )

        try:
            if doc_type == "summary":
                doc_result = await self.documentation_agent.generate_summary_report(
                    fiscal_year
                )
            elif doc_type == "finding":
                doc_result = await self.documentation_agent.generate_finding_report(
                    fiscal_year
                )
            elif doc_type == "management_letter":
                doc_result = await self.documentation_agent.draft_management_letter(
                    fiscal_year, findings or []
                )
            else:
                raise ValueError(f"Unknown document type: {doc_type}")

            result.agent_results["documentation"] = doc_result
            result.success = True
            result.final_output = "文書が生成されました"

        except Exception as e:
            result.error = str(e)
            result.success = False

        result.completed_at = datetime.now()
        return result

    async def route_request(
        self,
        request: str,
        context: Optional[dict[str, Any]] = None,
    ) -> WorkflowResult:
        """Route a natural language request to the appropriate agent.

        Args:
            request: User's request in natural language.
            context: Optional context.

        Returns:
            Workflow result.
        """
        import uuid
        result = WorkflowResult(
            workflow_id=str(uuid.uuid4()),
            workflow_type="routed",
        )

        request_lower = request.lower()

        try:
            # Route based on keywords
            if any(kw in request_lower for kw in ["分析", "リスク", "傾向", "パターン"]):
                agent_result = await self.analysis_agent.execute(request, context)
                result.agent_results["analysis"] = agent_result.to_dict()

            elif any(kw in request_lower for kw in ["調査", "深掘り", "追跡", "確認"]):
                agent_result = await self.investigation_agent.execute(request, context)
                result.agent_results["investigation"] = agent_result.to_dict()

            elif any(kw in request_lower for kw in ["レポート", "報告書", "文書", "作成"]):
                agent_result = await self.documentation_agent.execute(request, context)
                result.agent_results["documentation"] = agent_result.to_dict()

            elif any(kw in request_lower for kw in ["レビュー", "評価", "優先", "是正"]):
                agent_result = await self.review_agent.execute(request, context)
                result.agent_results["review"] = agent_result.to_dict()

            else:
                # Default to QA agent
                agent_result = await self.qa_agent.execute(request, context)
                result.agent_results["qa"] = agent_result.to_dict()

            result.success = True

            # Extract final output
            if agent_result.messages:
                last_msg = agent_result.messages[-1]
                if isinstance(last_msg, dict):
                    result.final_output = last_msg.get("content", "")

        except Exception as e:
            result.error = str(e)
            result.success = False

        result.completed_at = datetime.now()
        return result

    def get_available_workflows(self) -> list[dict[str, str]]:
        """Get list of available workflows.

        Returns:
            List of workflow descriptions.
        """
        return [
            {
                "id": "full_audit",
                "name": "完全監査ワークフロー",
                "description": "分析→調査→レビュー→文書化の完全なワークフロー",
            },
            {
                "id": "investigation",
                "name": "調査ワークフロー",
                "description": "特定の仕訳、ユーザー、ルールの詳細調査",
            },
            {
                "id": "qa",
                "name": "質問応答",
                "description": "仕訳データに関する対話的な質問応答",
            },
            {
                "id": "documentation",
                "name": "文書化ワークフロー",
                "description": "監査報告書やマネジメントレターの作成",
            },
        ]
