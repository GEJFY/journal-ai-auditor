"""自律型監査エージェント用分析ツールパッケージ。

13種類の分析ツールをAuditToolRegistryに登録する。
"""

from app.agents.autonomous.tool_registry import AuditToolRegistry
from app.agents.autonomous_tools.account_balance import ACCOUNT_BALANCE_TOOL
from app.agents.autonomous_tools.correlation_analysis import CORRELATION_TOOL
from app.agents.autonomous_tools.duplicate_detection import DUPLICATE_TOOL
from app.agents.autonomous_tools.financial_ratios import FINANCIAL_RATIOS_TOOL
from app.agents.autonomous_tools.journal_entry_testing import JOURNAL_ENTRY_TESTING_TOOL
from app.agents.autonomous_tools.ml_anomaly_wrapper import ML_ANOMALY_TOOL
from app.agents.autonomous_tools.population_analysis import POPULATION_TOOL
from app.agents.autonomous_tools.round_amount import ROUND_AMOUNT_TOOL
from app.agents.autonomous_tools.rule_risk_wrapper import RULE_RISK_TOOL
from app.agents.autonomous_tools.sankey_data import SANKEY_TOOL
from app.agents.autonomous_tools.stratification import STRATIFICATION_TOOL
from app.agents.autonomous_tools.t_account_analysis import T_ACCOUNT_TOOL
from app.agents.autonomous_tools.time_series_analysis import TIME_SERIES_TOOL

ALL_TOOLS = [
    POPULATION_TOOL,
    ACCOUNT_BALANCE_TOOL,
    FINANCIAL_RATIOS_TOOL,
    T_ACCOUNT_TOOL,
    SANKEY_TOOL,
    TIME_SERIES_TOOL,
    STRATIFICATION_TOOL,
    DUPLICATE_TOOL,
    ROUND_AMOUNT_TOOL,
    JOURNAL_ENTRY_TESTING_TOOL,
    CORRELATION_TOOL,
    RULE_RISK_TOOL,
    ML_ANOMALY_TOOL,
]


def create_default_registry() -> AuditToolRegistry:
    """全13ツールを登録したデフォルトレジストリを生成。"""
    registry = AuditToolRegistry()
    for tool in ALL_TOOLS:
        registry.register(tool)
    return registry
