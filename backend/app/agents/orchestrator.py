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
        """Run a complete audit workflow with inter-agent context passing.

        Sequence:
        1. Analysis: Identify high-risk areas and extract findings
        2. Investigation: Deep-dive using analysis findings as context
        3. Review: Validate with all prior findings
        4. Documentation: Generate comprehensive report from all stages

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
            # Step 1: 分析 - リスク領域の特定
            analysis_result = await self.analysis_agent.analyze_risk_distribution(
                fiscal_year
            )
            result.agent_results["analysis"] = analysis_result

            # 分析結果から発見事項を構造化抽出
            analysis_findings = self._extract_findings_from_result(
                analysis_result, "analysis"
            )

            # Step 2: 調査 - 分析結果をコンテキストとして渡す
            investigation_prompt = self._build_investigation_prompt(
                fiscal_year, analysis_findings
            )
            investigation_result = await self.investigation_agent.execute(
                investigation_prompt,
                {"fiscal_year": fiscal_year},
            )
            result.agent_results["investigation"] = investigation_result.to_dict()

            # 調査結果から追加の発見事項を抽出
            investigation_findings = self._extract_findings_from_messages(
                investigation_result.messages, "investigation"
            )

            # Step 3: レビュー - 分析+調査の全発見事項を渡す
            all_findings = analysis_findings + investigation_findings
            review_prompt = self._build_review_prompt(fiscal_year, all_findings)
            review_result = await self.review_agent.execute(
                review_prompt,
                {"fiscal_year": fiscal_year},
            )
            result.agent_results["review"] = (
                review_result.to_dict()
                if hasattr(review_result, "to_dict")
                else review_result
            )

            # Step 4: 文書化 - 全エージェントの成果物を統合してレポート生成
            doc_context = self._build_documentation_context(
                fiscal_year, analysis_result, investigation_findings,
                all_findings, result.agent_results.get("review", {}),
            )
            doc_result = await self.documentation_agent.execute(
                doc_context,
                {"fiscal_year": fiscal_year},
            )
            result.agent_results["documentation"] = doc_result.to_dict()

            result.success = True
            result.final_output = (
                f"監査ワークフローが正常に完了しました "
                f"(発見事項: {len(all_findings)}件)"
            )

        except Exception as e:
            result.error = str(e)
            result.success = False

        result.completed_at = datetime.now()
        return result

    def _extract_findings_from_result(
        self, result: dict[str, Any], source: str
    ) -> list[dict[str, Any]]:
        """分析結果dictから発見事項を抽出する."""
        findings = []
        if isinstance(result, dict):
            # summaryキーがある場合（analysis agentの出力）
            summary = result.get("summary", {})
            if isinstance(summary, dict):
                for item in summary.get("findings", []):
                    findings.append({
                        "source": source,
                        "title": item if isinstance(item, str) else str(item),
                        "severity": "MEDIUM",
                    })
                for item in summary.get("insights", []):
                    findings.append({
                        "source": source,
                        "title": item if isinstance(item, str) else str(item),
                        "severity": "LOW",
                    })
            # messagesキーがある場合
            if "messages" in result:
                findings.extend(
                    self._extract_findings_from_messages(result["messages"], source)
                )
        return findings

    def _extract_findings_from_messages(
        self, messages: list[Any], source: str
    ) -> list[dict[str, Any]]:
        """メッセージリストからAIの発見事項テキストを抽出する."""
        findings = []
        if not messages:
            return findings
        for msg in messages:
            content = ""
            if isinstance(msg, dict):
                content = msg.get("content", "")
            elif hasattr(msg, "content"):
                content = msg.content or ""
            if not content:
                continue
            # 発見事項のパターンを探索
            for line in content.split("\n"):
                line = line.strip()
                if any(kw in line for kw in [
                    "リスク", "異常", "不正", "違反", "逸脱", "重要",
                    "発見", "懸念", "要注意", "高額",
                ]):
                    if len(line) > 10:
                        findings.append({
                            "source": source,
                            "title": line[:200],
                            "severity": "HIGH" if any(
                                k in line for k in ["不正", "重要", "高リスク"]
                            ) else "MEDIUM",
                        })
        return findings

    def _build_investigation_prompt(
        self, fiscal_year: int, analysis_findings: list[dict[str, Any]]
    ) -> str:
        """分析結果を踏まえた調査プロンプトを構築する."""
        findings_text = ""
        if analysis_findings:
            items = "\n".join(
                f"  - [{f['severity']}] {f['title']}" for f in analysis_findings[:15]
            )
            findings_text = f"""
## 分析エージェントからの引き継ぎ事項
以下の発見事項が分析フェーズで特定されました。これらを中心に深掘り調査してください。

{items}
"""
        return f"""{fiscal_year}年度の高リスク仕訳について詳細調査を実施してください。

{findings_text}

調査対象:
1. 高リスク仕訳上位10件の取引内容と背景
2. 異常パターンの裏付け調査
3. 関連する担当者や勘定科目の調査
4. 違反ルールの詳細確認
"""

    def _build_review_prompt(
        self, fiscal_year: int, all_findings: list[dict[str, Any]]
    ) -> str:
        """全発見事項を踏まえたレビュープロンプトを構築する."""
        grouped: dict[str, list[str]] = {"HIGH": [], "MEDIUM": [], "LOW": []}
        for f in all_findings:
            sev = f.get("severity", "MEDIUM")
            grouped.setdefault(sev, []).append(f["title"])

        sections = []
        for sev, label in [("HIGH", "高"), ("MEDIUM", "中"), ("LOW", "低")]:
            if grouped.get(sev):
                items = "\n".join(f"  - {t}" for t in grouped[sev][:10])
                sections.append(f"### {label}リスク ({len(grouped[sev])}件)\n{items}")

        findings_text = "\n\n".join(sections) if sections else "（発見事項なし）"

        return f"""{fiscal_year}年度の監査発見事項をレビューし、優先順位付けと改善提言を行ってください。

## 分析・調査フェーズの発見事項一覧（全{len(all_findings)}件）

{findings_text}

## レビュー依頼事項
1. 各発見事項の重要性と影響度の評価
2. 誤検知の可能性の判定
3. 優先順位付け（即時対応/短期対応/中長期対応）
4. 是正措置の提言
"""

    def _build_documentation_context(
        self,
        fiscal_year: int,
        analysis_result: dict[str, Any],
        investigation_findings: list[dict[str, Any]],
        all_findings: list[dict[str, Any]],
        review_result: dict[str, Any],
    ) -> str:
        """全エージェントの成果物を統合した文書化プロンプトを構築する."""
        high = [f for f in all_findings if f.get("severity") == "HIGH"]
        medium = [f for f in all_findings if f.get("severity") == "MEDIUM"]
        low = [f for f in all_findings if f.get("severity") == "LOW"]

        return f"""以下の監査結果に基づいて、{fiscal_year}年度の包括的な監査報告書を作成してください。

## 報告書テンプレート

### 1. エグゼクティブサマリー
- 監査対象期間: {fiscal_year}年度
- 発見事項合計: {len(all_findings)}件（高: {len(high)}, 中: {len(medium)}, 低: {len(low)}）
- 総合リスク評価を記載

### 2. 分析結果の概要
分析エージェントが特定した主要な異常パターンとリスク分布を要約してください。

### 3. 調査結果の詳細
調査エージェントが深掘りした{len(investigation_findings)}件の調査結果を文書化してください。

### 4. 発見事項一覧
{"".join(f"- [{f['severity']}] {f['title']}" + chr(10) for f in all_findings[:30])}

### 5. レビュー結果と優先順位
レビューエージェントの評価結果を反映した優先順位付けを記載してください。

### 6. 改善提言
具体的な是正措置と期限を含む改善提言を作成してください。

### 7. 結論
監査全体の総括と次年度への提言を記載してください。

---
必ずツールを使って最新データを確認し、正確な数値を報告書に反映してください。
"""

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
        """Route a natural language request to the appropriate agent using LLM.

        Uses LLM-based semantic routing with keyword fallback.

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

        try:
            # LLMベースのセマンティックルーティング
            agent_key = await self._classify_request(request)

            agent_map = {
                "analysis": self.analysis_agent,
                "investigation": self.investigation_agent,
                "documentation": self.documentation_agent,
                "review": self.review_agent,
                "qa": self.qa_agent,
            }

            agent = agent_map.get(agent_key, self.qa_agent)
            agent_result = await agent.execute(request, context)
            result.agent_results[agent_key] = agent_result.to_dict()

            result.success = True

            # 最終出力の抽出
            if agent_result.messages:
                last_msg = agent_result.messages[-1]
                if isinstance(last_msg, dict):
                    result.final_output = last_msg.get("content", "")
                elif hasattr(last_msg, "content"):
                    result.final_output = last_msg.content

        except Exception as e:
            result.error = str(e)
            result.success = False

        result.completed_at = datetime.now()
        return result

    async def _classify_request(self, request: str) -> str:
        """LLMを使ってリクエストを分類し、適切なエージェントを選択する."""
        from app.agents.base import create_llm

        classification_prompt = """以下のユーザーリクエストを分類してください。
回答は以下の5つのカテゴリのいずれか1つだけを返してください（カテゴリ名のみ）:

- analysis: データ分析、リスク評価、傾向分析、パターン検出、統計
- investigation: 特定仕訳の調査、深掘り、追跡、原因究明
- documentation: レポート作成、報告書、文書化、マネジメントレター
- review: 発見事項のレビュー、評価、優先順位付け、是正措置
- qa: 質問応答、説明、一般的な質問

リクエスト: """

        try:
            llm = create_llm(self.config)
            response = await llm.ainvoke([
                SystemMessage(content=classification_prompt),
                HumanMessage(content=request),
            ])
            category = response.content.strip().lower()
            valid = {"analysis", "investigation", "documentation", "review", "qa"}
            if category in valid:
                return category
        except Exception:
            pass

        # フォールバック: キーワードベースのルーティング
        return self._keyword_classify(request)

    @staticmethod
    def _keyword_classify(request: str) -> str:
        """キーワードベースのフォールバック分類."""
        request_lower = request.lower()
        rules = [
            ("analysis", ["分析", "リスク", "傾向", "パターン", "異常", "統計", "分布"]),
            ("investigation", ["調査", "深掘り", "追跡", "確認", "原因", "仕訳"]),
            ("documentation", ["レポート", "報告書", "文書", "作成", "マネジメントレター"]),
            ("review", ["レビュー", "評価", "優先", "是正", "改善"]),
        ]
        for category, keywords in rules:
            if any(kw in request_lower for kw in keywords):
                return category
        return "qa"

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
