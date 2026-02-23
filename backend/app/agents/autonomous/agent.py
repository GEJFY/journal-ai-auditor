"""自律型監査エージェント。

5フェーズ分析ループ (Observe→Hypothesize→Explore→Verify→Synthesize) で
仕訳データを自律的に探索・分析し、監査インサイトを生成する LangGraph エージェント。
"""

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from app.agents.autonomous.prompts import (
    EXPLORE_PROMPT,
    HYPOTHESIZE_PROMPT,
    OBSERVE_PROMPT,
    SYNTHESIZE_PROMPT,
    SYSTEM_PROMPT,
    VERIFY_PROMPT,
)
from app.agents.autonomous.state import (
    AuditInsight,
    AuditPhase,
    AutonomousAuditState,
    Hypothesis,
)
from app.agents.autonomous.tool_registry import AuditToolRegistry
from app.agents.base import AgentConfig, AgentType, create_llm
from app.db import duckdb_manager

logger = logging.getLogger(__name__)

# LLM レスポンスから JSON を抽出するヘルパー
_MAX_EXPLORE_ITERATIONS = 3
_MAX_VERIFY_FEEDBACK_LOOPS = 1


def _extract_json(text: str) -> dict[str, Any]:
    """LLM 応答テキストから JSON ブロックを抽出してパースする。"""
    content = text.strip()
    if "```json" in content:
        content = content.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in content:
        content = content.split("```", 1)[1].split("```", 1)[0].strip()
    return json.loads(content)


class AutonomousAuditAgent:
    """5フェーズ自律型監査エージェント。

    LangGraph StateGraph をベースに、以下のフェーズを自律的に実行する:
      1. Observe  — データ統計から注目パターンを抽出
      2. Hypothesize — 検証可能な仮説を生成
      3. Explore  — ツール選択・実行でエビデンス収集
      4. Verify   — 仮説の支持度を評価
      5. Synthesize — インサイト生成・エグゼクティブサマリー
    """

    def __init__(
        self,
        registry: AuditToolRegistry,
        config: AgentConfig | None = None,
    ) -> None:
        self.registry = registry
        self.config = config or AgentConfig(
            agent_type=AgentType.ANALYSIS,
            max_tokens=4096,
            temperature=0.0,
        )
        self.llm = create_llm(self.config)
        self._graph: StateGraph | None = None
        # SSE イベントバッファ (非同期ストリーミング用)
        self._event_queue: asyncio.Queue[dict[str, Any]] | None = None

    # ------------------------------------------------------------------
    # Graph 構築
    # ------------------------------------------------------------------

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(AutonomousAuditState)

        graph.add_node("observe", self._observe_node)
        graph.add_node("hypothesize", self._hypothesize_node)
        graph.add_node("explore", self._explore_node)
        graph.add_node("verify", self._verify_node)
        graph.add_node("synthesize", self._synthesize_node)
        graph.add_node("finalize", self._finalize_node)

        graph.set_entry_point("observe")

        graph.add_edge("observe", "hypothesize")
        graph.add_conditional_edges(
            "hypothesize",
            self._after_hypothesize,
            {"explore": "explore", "await": END},
        )
        graph.add_conditional_edges(
            "explore",
            self._after_explore,
            {"verify": "verify", "explore": "explore"},
        )
        graph.add_conditional_edges(
            "verify",
            self._after_verify,
            {"explore": "explore", "synthesize": "synthesize"},
        )
        graph.add_edge("synthesize", "finalize")
        graph.add_edge("finalize", END)

        return graph

    @property
    def graph(self) -> StateGraph:
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph

    # ------------------------------------------------------------------
    # SSE イベント送出
    # ------------------------------------------------------------------

    def _emit(self, event: dict[str, Any]) -> None:
        """SSE イベントをキューに追加 (ストリーミング実行時のみ)。"""
        if self._event_queue is not None:
            self._event_queue.put_nowait(event)

    # ------------------------------------------------------------------
    # LLM 呼び出しヘルパー
    # ------------------------------------------------------------------

    def _call_llm(self, user_prompt: str) -> str:
        """LLM をシステムプロンプト付きで呼び出し、応答テキストを返す。"""
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        response = self.llm.invoke(messages)
        return response.content

    # ------------------------------------------------------------------
    # Phase 1: Observe
    # ------------------------------------------------------------------

    def _observe_node(self, state: AutonomousAuditState) -> dict[str, Any]:
        logger.info("Phase: OBSERVE (session=%s)", state.get("session_id"))
        self._emit({"type": "phase_start", "phase": "observe"})

        fiscal_year = state["fiscal_year"]

        # 基本統計ツールを実行して観察データを収集
        stats_tools = [
            "population_statistics",
            "rule_risk_summary",
            "ml_anomaly_summary",
        ]
        observations: dict[str, Any] = {}

        for tool_name in stats_tools:
            if tool_name in self.registry:
                result = self.registry.execute(tool_name, fiscal_year=fiscal_year)
                observations[tool_name] = {
                    "summary": result.summary,
                    "key_findings": result.key_findings,
                    "data": result.data,
                }
                self._emit(
                    {
                        "type": "observation",
                        "tool": tool_name,
                        "summary": result.summary,
                    }
                )

        # LLM で注目パターンを抽出
        stats_text = json.dumps(observations, ensure_ascii=False, default=str)
        prompt = OBSERVE_PROMPT.format(statistics=stats_text)
        llm_response = self._call_llm(prompt)

        try:
            parsed = _extract_json(llm_response)
            notable_patterns = parsed.get("notable_patterns", [])
        except (json.JSONDecodeError, KeyError):
            logger.warning("Observe JSON parse failed, falling back to raw text")
            notable_patterns = [llm_response[:500]]

        self._emit(
            {
                "type": "observation",
                "tool": "llm_analysis",
                "summary": f"{len(notable_patterns)}個の注目パターンを特定",
            }
        )

        phase_entry = {
            "phase": AuditPhase.OBSERVE,
            "timestamp": datetime.now().isoformat(),
            "patterns_found": len(notable_patterns),
        }

        return {
            "current_phase": AuditPhase.OBSERVE,
            "observations": observations,
            "notable_patterns": notable_patterns,
            "phase_history": state.get("phase_history", []) + [phase_entry],
            "step_count": state.get("step_count", 0) + 1,
        }

    # ------------------------------------------------------------------
    # Phase 2: Hypothesize
    # ------------------------------------------------------------------

    def _hypothesize_node(self, state: AutonomousAuditState) -> dict[str, Any]:
        logger.info("Phase: HYPOTHESIZE (session=%s)", state.get("session_id"))
        self._emit({"type": "phase_start", "phase": "hypothesize"})

        tool_schemas = json.dumps(
            self.registry.get_all_schemas(), ensure_ascii=False, indent=2
        )
        observations_text = json.dumps(
            state.get("observations", {}), ensure_ascii=False, default=str
        )
        patterns_text = "\n".join(f"- {p}" for p in state.get("notable_patterns", []))

        prompt = HYPOTHESIZE_PROMPT.format(
            observations=observations_text,
            notable_patterns=patterns_text,
            tool_schemas=tool_schemas,
        )
        llm_response = self._call_llm(prompt)

        try:
            parsed = _extract_json(llm_response)
            raw_hypotheses = parsed.get("hypotheses", [])
        except (json.JSONDecodeError, KeyError):
            logger.warning("Hypothesize JSON parse failed")
            raw_hypotheses = []

        max_h = state.get("max_hypotheses", 5)
        hypotheses: list[dict[str, Any]] = []
        for h in raw_hypotheses[:max_h]:
            hyp = Hypothesis(
                id=h.get("id", f"H-{len(hypotheses) + 1:03d}"),
                title=h.get("title", ""),
                description=h.get("description", ""),
                rationale=h.get("rationale", ""),
                test_approach=h.get("test_approach", ""),
                tools_to_use=h.get("tools_to_use", []),
                priority=h.get("priority", len(hypotheses) + 1),
            )
            hypotheses.append(hyp.to_dict())
            self._emit(
                {
                    "type": "hypothesis",
                    "id": hyp.id,
                    "title": hyp.title,
                    "description": hyp.description,
                }
            )

        phase_entry = {
            "phase": AuditPhase.HYPOTHESIZE,
            "timestamp": datetime.now().isoformat(),
            "hypotheses_count": len(hypotheses),
        }

        return {
            "current_phase": AuditPhase.HYPOTHESIZE,
            "hypotheses": hypotheses,
            "phase_history": state.get("phase_history", []) + [phase_entry],
            "step_count": state.get("step_count", 0) + 1,
        }

    def _after_hypothesize(self, state: AutonomousAuditState) -> str:
        """HITL 分岐: awaiting_approval が True なら中断、そうでなければ探索へ。"""
        if state.get("awaiting_approval"):
            self._emit(
                {"type": "awaiting_approval", "hypotheses": state.get("hypotheses", [])}
            )
            return "await"
        return "explore"

    # ------------------------------------------------------------------
    # Phase 3: Explore
    # ------------------------------------------------------------------

    def _explore_node(self, state: AutonomousAuditState) -> dict[str, Any]:
        logger.info("Phase: EXPLORE (session=%s)", state.get("session_id"))
        self._emit({"type": "phase_start", "phase": "explore"})

        fiscal_year = state["fiscal_year"]
        hypotheses_text = json.dumps(state.get("hypotheses", []), ensure_ascii=False)
        tool_schemas = json.dumps(
            self.registry.get_all_schemas(), ensure_ascii=False, indent=2
        )
        prev_results = state.get("tool_results", [])
        prev_results_text = (
            json.dumps(
                [
                    {"tool_name": r["tool_name"], "summary": r["summary"]}
                    for r in prev_results
                ],
                ensure_ascii=False,
            )
            if prev_results
            else "なし"
        )

        prompt = EXPLORE_PROMPT.format(
            hypotheses=hypotheses_text,
            tool_schemas=tool_schemas,
            previous_results=prev_results_text,
            fiscal_year=fiscal_year,
        )
        llm_response = self._call_llm(prompt)

        try:
            parsed = _extract_json(llm_response)
            tool_calls = parsed.get("tool_calls", [])
        except (json.JSONDecodeError, KeyError):
            logger.warning("Explore JSON parse failed")
            tool_calls = []

        # ツール実行
        new_results: list[dict[str, Any]] = []
        exploration_log = list(state.get("exploration_log", []))

        max_per_h = state.get("max_tools_per_hypothesis", 3)
        # 仮説あたりの既実行ツール数をカウント
        h_tool_counts: dict[str, int] = {}
        for r in prev_results:
            for h in state.get("hypotheses", []):
                if r.get("tool_name") in h.get("tools_to_use", []):
                    h_tool_counts[h["id"]] = h_tool_counts.get(h["id"], 0) + 1

        for call in tool_calls:
            h_id = call.get("hypothesis_id", "")
            if h_tool_counts.get(h_id, 0) >= max_per_h:
                continue

            tool_name = call.get("tool_name", "")
            params = call.get("parameters", {})
            params.setdefault("fiscal_year", fiscal_year)

            self._emit(
                {
                    "type": "tool_start",
                    "tool": tool_name,
                    "hypothesis_id": h_id,
                }
            )

            result = self.registry.execute(tool_name, **params)
            result_dict = result.to_dict()
            new_results.append(result_dict)

            log_entry = {
                "hypothesis_id": h_id,
                "tool_name": tool_name,
                "reason": call.get("reason", ""),
                "success": result.success,
                "timestamp": datetime.now().isoformat(),
            }
            exploration_log.append(log_entry)
            h_tool_counts[h_id] = h_tool_counts.get(h_id, 0) + 1

            self._emit(
                {
                    "type": "tool_complete",
                    "tool": tool_name,
                    "hypothesis_id": h_id,
                    "success": result.success,
                    "summary": result.summary,
                }
            )

        all_results = prev_results + new_results

        phase_entry = {
            "phase": AuditPhase.EXPLORE,
            "timestamp": datetime.now().isoformat(),
            "tools_executed": len(new_results),
            "total_results": len(all_results),
        }

        return {
            "current_phase": AuditPhase.EXPLORE,
            "tool_results": all_results,
            "exploration_log": exploration_log,
            "phase_history": state.get("phase_history", []) + [phase_entry],
            "step_count": state.get("step_count", 0) + 1,
        }

    def _after_explore(self, state: AutonomousAuditState) -> str:
        """探索ループ判定: 探索回数上限チェック。"""
        explore_count = sum(
            1
            for p in state.get("phase_history", [])
            if p.get("phase") == AuditPhase.EXPLORE
        )
        if explore_count >= _MAX_EXPLORE_ITERATIONS:
            return "verify"
        # 新しいツール結果が得られたなら verify へ
        return "verify"

    # ------------------------------------------------------------------
    # Phase 4: Verify
    # ------------------------------------------------------------------

    def _verify_node(self, state: AutonomousAuditState) -> dict[str, Any]:
        logger.info("Phase: VERIFY (session=%s)", state.get("session_id"))
        self._emit({"type": "phase_start", "phase": "verify"})

        hypotheses_text = json.dumps(state.get("hypotheses", []), ensure_ascii=False)
        tool_results_text = json.dumps(
            [
                {
                    "tool_name": r["tool_name"],
                    "summary": r["summary"],
                    "key_findings": r.get("key_findings", []),
                }
                for r in state.get("tool_results", [])
            ],
            ensure_ascii=False,
        )

        prompt = VERIFY_PROMPT.format(
            hypotheses=hypotheses_text,
            tool_results=tool_results_text,
        )
        llm_response = self._call_llm(prompt)

        try:
            parsed = _extract_json(llm_response)
            verifications = parsed.get("verifications", [])
        except (json.JSONDecodeError, KeyError):
            logger.warning("Verify JSON parse failed")
            verifications = []

        # 仮説を更新
        hypotheses = list(state.get("hypotheses", []))
        needs_more = False

        for v in verifications:
            h_id = v.get("hypothesis_id", "")
            for h in hypotheses:
                if h["id"] == h_id:
                    h["grounding_score"] = v.get("grounding_score", 0.0)
                    h["status"] = v.get("verdict", "inconclusive")
                    h["evidence_for"] = v.get("evidence_for", [])
                    h["evidence_against"] = v.get("evidence_against", [])
                    if v.get("needs_more_exploration"):
                        needs_more = True
                    break

            self._emit(
                {
                    "type": "verification",
                    "hypothesis_id": h_id,
                    "verdict": v.get("verdict", "inconclusive"),
                    "grounding_score": v.get("grounding_score", 0.0),
                }
            )

        phase_entry = {
            "phase": AuditPhase.VERIFY,
            "timestamp": datetime.now().isoformat(),
            "verified_count": len(verifications),
            "needs_more": needs_more,
        }

        return {
            "current_phase": AuditPhase.VERIFY,
            "hypotheses": hypotheses,
            "verified_hypotheses": hypotheses,
            "phase_history": state.get("phase_history", []) + [phase_entry],
            "step_count": state.get("step_count", 0) + 1,
        }

    def _after_verify(self, state: AutonomousAuditState) -> str:
        """検証後の分岐: エビデンス不足で追加探索が必要か判定。"""
        verify_count = sum(
            1
            for p in state.get("phase_history", [])
            if p.get("phase") == AuditPhase.VERIFY
        )
        if verify_count > _MAX_VERIFY_FEEDBACK_LOOPS:
            return "synthesize"

        last_verify = None
        for p in reversed(state.get("phase_history", [])):
            if p.get("phase") == AuditPhase.VERIFY:
                last_verify = p
                break

        if last_verify and last_verify.get("needs_more"):
            return "explore"
        return "synthesize"

    # ------------------------------------------------------------------
    # Phase 5: Synthesize
    # ------------------------------------------------------------------

    def _synthesize_node(self, state: AutonomousAuditState) -> dict[str, Any]:
        logger.info("Phase: SYNTHESIZE (session=%s)", state.get("session_id"))
        self._emit({"type": "phase_start", "phase": "synthesize"})

        verified = state.get("verified_hypotheses", state.get("hypotheses", []))
        verified_text = json.dumps(verified, ensure_ascii=False)

        tool_summaries = json.dumps(
            [
                {
                    "tool_name": r["tool_name"],
                    "summary": r["summary"],
                    "key_findings": r.get("key_findings", []),
                }
                for r in state.get("tool_results", [])
            ],
            ensure_ascii=False,
        )

        prompt = SYNTHESIZE_PROMPT.format(
            verified_hypotheses=verified_text,
            tool_summaries=tool_summaries,
        )
        llm_response = self._call_llm(prompt)

        try:
            parsed = _extract_json(llm_response)
            raw_insights = parsed.get("insights", [])
            executive_summary = parsed.get("executive_summary", "")
        except (json.JSONDecodeError, KeyError):
            logger.warning("Synthesize JSON parse failed")
            raw_insights = []
            executive_summary = llm_response[:1000]

        insights: list[dict[str, Any]] = []
        for i, raw in enumerate(raw_insights):
            ins = AuditInsight(
                id=raw.get("id", f"INS-{i + 1:03d}"),
                title=raw.get("title", ""),
                description=raw.get("description", ""),
                category=raw.get("category", "risk"),
                severity=raw.get("severity", "MEDIUM"),
                affected_amount=raw.get("affected_amount", 0),
                affected_count=raw.get("affected_count", 0),
                recommendations=raw.get("recommendations", []),
                related_hypotheses=raw.get("related_hypotheses", []),
                grounding_score=raw.get("grounding_score", 0.0),
            )
            insights.append(ins.to_dict())
            self._emit(
                {
                    "type": "insight",
                    "id": ins.id,
                    "title": ins.title,
                    "severity": ins.severity,
                }
            )

        self._emit(
            {
                "type": "summary",
                "executive_summary": executive_summary[:500],
            }
        )

        phase_entry = {
            "phase": AuditPhase.SYNTHESIZE,
            "timestamp": datetime.now().isoformat(),
            "insights_count": len(insights),
        }

        return {
            "current_phase": AuditPhase.SYNTHESIZE,
            "insights": insights,
            "executive_summary": executive_summary,
            "phase_history": state.get("phase_history", []) + [phase_entry],
            "step_count": state.get("step_count", 0) + 1,
        }

    # ------------------------------------------------------------------
    # Finalize: DB 永続化
    # ------------------------------------------------------------------

    def _finalize_node(self, state: AutonomousAuditState) -> dict[str, Any]:
        logger.info("Phase: FINALIZE (session=%s)", state.get("session_id"))
        self._emit({"type": "phase_start", "phase": "finalize"})

        session_id = state.get("session_id", "")
        now = datetime.now().isoformat()

        # セッション永続化
        try:
            db = duckdb_manager
            with db.connect() as conn:
                conn.execute(
                    """
                    INSERT INTO autonomous_audit_sessions (
                        session_id, fiscal_year, scope,
                        current_phase, status,
                        observations, hypotheses, tool_results,
                        executive_summary,
                        total_hypotheses, supported_hypotheses,
                        total_insights, critical_insights, high_insights,
                        total_tool_calls,
                        started_at, completed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        session_id,
                        state.get("fiscal_year", 0),
                        json.dumps(state.get("scope", {}), ensure_ascii=False),
                        AuditPhase.COMPLETE,
                        "completed",
                        json.dumps(
                            state.get("observations", {}),
                            ensure_ascii=False,
                            default=str,
                        ),
                        json.dumps(state.get("hypotheses", []), ensure_ascii=False),
                        json.dumps(
                            state.get("tool_results", []),
                            ensure_ascii=False,
                            default=str,
                        ),
                        state.get("executive_summary", ""),
                        len(state.get("hypotheses", [])),
                        sum(
                            1
                            for h in state.get("hypotheses", [])
                            if h.get("status") == "supported"
                        ),
                        len(state.get("insights", [])),
                        sum(
                            1
                            for i in state.get("insights", [])
                            if i.get("severity") == "CRITICAL"
                        ),
                        sum(
                            1
                            for i in state.get("insights", [])
                            if i.get("severity") == "HIGH"
                        ),
                        len(state.get("exploration_log", [])),
                        state.get("started_at", now),
                        now,
                    ],
                )

                # インサイト永続化
                for ins in state.get("insights", []):
                    conn.execute(
                        """
                        INSERT INTO audit_insights (
                            insight_id, session_id, fiscal_year,
                            title, description, category, severity,
                            evidence, grounding_score,
                            affected_amount, affected_count,
                            recommendations, status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            ins.get("id", str(uuid.uuid4())),
                            session_id,
                            state.get("fiscal_year", 0),
                            ins.get("title", ""),
                            ins.get("description", ""),
                            ins.get("category", "risk"),
                            ins.get("severity", "MEDIUM"),
                            json.dumps(ins.get("evidence", []), ensure_ascii=False),
                            ins.get("grounding_score", 0.0),
                            ins.get("affected_amount", 0),
                            ins.get("affected_count", 0),
                            json.dumps(
                                ins.get("recommendations", []), ensure_ascii=False
                            ),
                            "active",
                            now,
                        ],
                    )
            logger.info("Session %s persisted to DuckDB", session_id)
        except Exception as e:
            logger.error("Failed to persist session %s: %s", session_id, str(e))

        self._emit(
            {
                "type": "complete",
                "session_id": session_id,
                "insights_count": len(state.get("insights", [])),
                "hypotheses_count": len(state.get("hypotheses", [])),
            }
        )

        return {
            "current_phase": AuditPhase.COMPLETE,
            "completed_at": now,
        }

    # ------------------------------------------------------------------
    # 実行エントリポイント
    # ------------------------------------------------------------------

    def _create_initial_state(
        self,
        fiscal_year: int,
        scope: dict[str, Any] | None = None,
        auto_approve: bool = True,
    ) -> AutonomousAuditState:
        session_id = str(uuid.uuid4())
        return AutonomousAuditState(
            session_id=session_id,
            fiscal_year=fiscal_year,
            scope=scope or {},
            messages=[],
            current_phase=AuditPhase.OBSERVE,
            phase_history=[],
            observations={},
            notable_patterns=[],
            hypotheses=[],
            approved_hypotheses=[],
            tool_results=[],
            exploration_log=[],
            verified_hypotheses=[],
            insights=[],
            executive_summary="",
            step_count=0,
            max_steps=30,
            max_hypotheses=5,
            max_tools_per_hypothesis=3,
            awaiting_approval=not auto_approve,
            human_feedback=None,
            started_at=datetime.now().isoformat(),
            completed_at=None,
            error=None,
        )

    async def run(
        self,
        fiscal_year: int,
        scope: dict[str, Any] | None = None,
        auto_approve: bool = True,
    ) -> AutonomousAuditState:
        """自律型監査を実行し、最終状態を返す。

        Args:
            fiscal_year: 分析対象年度
            scope: 分析スコープ (期間・勘定フィルタ等)
            auto_approve: True なら仮説を自動承認して HITL をスキップ

        Returns:
            最終状態 (insights, executive_summary 等を含む)
        """
        state = self._create_initial_state(fiscal_year, scope, auto_approve)
        compiled = self.graph.compile()

        try:
            final_state = await asyncio.to_thread(compiled.invoke, state)
            return final_state
        except Exception as e:
            logger.error("Autonomous audit failed: %s", str(e))
            state["current_phase"] = AuditPhase.ERROR
            state["error"] = str(e)
            state["completed_at"] = datetime.now().isoformat()
            return state

    async def run_stream(
        self,
        fiscal_year: int,
        scope: dict[str, Any] | None = None,
        auto_approve: bool = True,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """SSE ストリーミング付きで自律型監査を実行。

        Yields:
            SSE イベント辞書 (type, data 等)
        """
        self._event_queue = asyncio.Queue()
        state = self._create_initial_state(fiscal_year, scope, auto_approve)
        compiled = self.graph.compile()

        async def _run_graph() -> None:
            try:
                await asyncio.to_thread(compiled.invoke, state)
            except Exception as e:
                self._event_queue.put_nowait({"type": "error", "message": str(e)})
            finally:
                self._event_queue.put_nowait({"type": "_done"})

        task = asyncio.create_task(_run_graph())

        try:
            while True:
                event = await self._event_queue.get()
                if event.get("type") == "_done":
                    break
                yield event
        finally:
            if not task.done():
                task.cancel()
            self._event_queue = None

    async def resume_after_approval(
        self,
        state: AutonomousAuditState,
        approved_hypothesis_ids: list[str] | None = None,
        feedback: str | None = None,
    ) -> AutonomousAuditState:
        """HITL 承認後にエージェントを再開する。

        Args:
            state: 中断時の状態
            approved_hypothesis_ids: 承認する仮説 ID リスト (None=全承認)
            feedback: 人間からのフィードバック

        Returns:
            再開後の最終状態
        """
        if approved_hypothesis_ids is not None:
            state["approved_hypotheses"] = approved_hypothesis_ids
            # 未承認の仮説を除外
            state["hypotheses"] = [
                h
                for h in state.get("hypotheses", [])
                if h["id"] in approved_hypothesis_ids
            ]
        else:
            state["approved_hypotheses"] = [
                h["id"] for h in state.get("hypotheses", [])
            ]

        state["awaiting_approval"] = False
        state["human_feedback"] = feedback

        # explore から再開するためグラフを再構築
        resume_graph = StateGraph(AutonomousAuditState)
        resume_graph.add_node("explore", self._explore_node)
        resume_graph.add_node("verify", self._verify_node)
        resume_graph.add_node("synthesize", self._synthesize_node)
        resume_graph.add_node("finalize", self._finalize_node)

        resume_graph.set_entry_point("explore")
        resume_graph.add_conditional_edges(
            "explore",
            self._after_explore,
            {"verify": "verify", "explore": "explore"},
        )
        resume_graph.add_conditional_edges(
            "verify",
            self._after_verify,
            {"explore": "explore", "synthesize": "synthesize"},
        )
        resume_graph.add_edge("synthesize", "finalize")
        resume_graph.add_edge("finalize", END)

        compiled = resume_graph.compile()

        try:
            final_state = await asyncio.to_thread(compiled.invoke, state)
            return final_state
        except Exception as e:
            logger.error("Resume failed: %s", str(e))
            state["current_phase"] = AuditPhase.ERROR
            state["error"] = str(e)
            return state
