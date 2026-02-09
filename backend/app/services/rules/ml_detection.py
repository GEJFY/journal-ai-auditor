"""Machine Learning based anomaly detection.

5 methods for detecting anomalies using ML:
- ML-001: Isolation Forest
- ML-002: Local Outlier Factor (LOF)
- ML-003: One-Class SVM
- ML-004: Autoencoder
- ML-005: Ensemble (combined methods)
"""

from dataclasses import dataclass
from typing import Any

import numpy as np
import polars as pl
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

from app.services.rules.base import (
    AuditRule,
    RuleCategory,
    RuleResult,
    RuleSet,
    RuleSeverity,
)


@dataclass
class MLFeatures:
    """Features used for ML anomaly detection."""

    # Feature column names
    NUMERIC_FEATURES = [
        "amount",
        "amount_log",
        "day_of_month",
        "day_of_week",
        "is_weekend",
        "is_month_end",
        "hour_of_day",
        "entry_delay_days",
    ]

    # One-hot encoded categorical features
    CATEGORICAL_FEATURES = [
        "source",
        "debit_credit_indicator",
    ]


class FeatureExtractor:
    """Extract and preprocess features for ML models."""

    def __init__(self) -> None:
        self.scaler = StandardScaler()
        self._fitted = False

    def extract_features(self, df: pl.DataFrame) -> tuple[np.ndarray, pl.DataFrame]:
        """Extract features from journal entries.

        Args:
            df: Polars DataFrame with journal entries.

        Returns:
            Tuple of (feature matrix, original DataFrame with row alignment).
        """
        # Add derived features
        df = df.with_columns(
            [
                # Log of amount for better scaling
                (pl.col("amount").abs() + 1).log().alias("amount_log"),
                # Time features
                pl.col("effective_date").dt.day().alias("day_of_month"),
                pl.col("effective_date").dt.weekday().alias("day_of_week"),
                (pl.col("effective_date").dt.weekday() >= 5)
                .cast(pl.Int32)
                .alias("is_weekend"),
                (pl.col("effective_date").dt.day() >= 28)
                .cast(pl.Int32)
                .alias("is_month_end"),
            ]
        )

        # Hour of day (if available)
        if "entry_time" in df.columns:
            df = df.with_columns(
                [
                    pl.when(pl.col("entry_time").is_not_null())
                    .then(pl.col("entry_time").dt.hour())
                    .otherwise(12)
                    .alias("hour_of_day")
                ]
            )
        else:
            df = df.with_columns([pl.lit(12).alias("hour_of_day")])

        # Entry delay
        if "entry_date" in df.columns and "effective_date" in df.columns:
            df = df.with_columns(
                [
                    pl.when(
                        pl.col("entry_date").is_not_null()
                        & pl.col("effective_date").is_not_null()
                    )
                    .then(
                        (
                            pl.col("entry_date") - pl.col("effective_date")
                        ).dt.total_days()
                    )
                    .otherwise(0)
                    .alias("entry_delay_days")
                ]
            )
        else:
            df = df.with_columns([pl.lit(0).alias("entry_delay_days")])

        # Select numeric features
        feature_cols = [
            "amount_log",
            "day_of_month",
            "day_of_week",
            "is_weekend",
            "is_month_end",
            "hour_of_day",
            "entry_delay_days",
        ]

        # Add one-hot encoding for source
        if "source" in df.columns:
            source_dummies = df.select(pl.col("source").to_dummies(separator="_"))
            df = pl.concat([df, source_dummies], how="horizontal")
            feature_cols.extend(list(source_dummies.columns))

        # Add DC indicator
        if "debit_credit_indicator" in df.columns:
            df = df.with_columns(
                [
                    (pl.col("debit_credit_indicator") == "D")
                    .cast(pl.Int32)
                    .alias("is_debit")
                ]
            )
            feature_cols.append("is_debit")

        # Extract feature matrix
        feature_df = df.select(feature_cols).fill_null(0)
        X = feature_df.to_numpy().astype(np.float64)

        return X, df

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        """Fit scaler and transform features.

        Args:
            X: Feature matrix.

        Returns:
            Scaled feature matrix.
        """
        self._fitted = True
        return self.scaler.fit_transform(X)

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Transform features using fitted scaler.

        Args:
            X: Feature matrix.

        Returns:
            Scaled feature matrix.
        """
        if not self._fitted:
            return self.fit_transform(X)
        return self.scaler.transform(X)


class IsolationForestRule(AuditRule):
    """ML-001: Anomaly detection using Isolation Forest."""

    def __init__(
        self,
        contamination: float = 0.01,
        n_estimators: int = 100,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.feature_extractor = FeatureExtractor()
        self.model: IsolationForest | None = None

    @property
    def rule_id(self) -> str:
        return "ML-001"

    @property
    def rule_name(self) -> str:
        return "Isolation Forest異常検知"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ML

    @property
    def description(self) -> str:
        return "Isolation Forestアルゴリズムによる多変量異常検知を実行します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        if len(df) < 100:
            # Not enough data for ML
            return result

        try:
            # Extract features
            X, df_with_features = self.feature_extractor.extract_features(df)
            X_scaled = self.feature_extractor.fit_transform(X)

            # Train and predict
            self.model = IsolationForest(
                contamination=self.contamination,
                n_estimators=self.n_estimators,
                random_state=42,
                n_jobs=-1,
            )
            predictions = self.model.fit_predict(X_scaled)
            scores = self.model.score_samples(X_scaled)

            # Find anomalies (prediction == -1)
            anomaly_mask = predictions == -1
            anomaly_indices = np.where(anomaly_mask)[0]

            for idx in anomaly_indices:
                row = df_with_features.row(idx, named=True)
                anomaly_score = -scores[
                    idx
                ]  # Convert to positive (higher = more anomalous)

                violation = self._create_violation(
                    gl_detail_id=row["gl_detail_id"],
                    journal_id=row["journal_id"],
                    message=f"ML異常検知 (IF): score={anomaly_score:.3f}",
                    details={
                        "algorithm": "IsolationForest",
                        "anomaly_score": float(anomaly_score),
                        "amount": row["amount"],
                        "features": {
                            "day_of_month": row.get("day_of_month"),
                            "is_weekend": row.get("is_weekend"),
                            "is_month_end": row.get("is_month_end"),
                        },
                    },
                    score_impact=min(anomaly_score * 10, 20.0),
                )
                result.violations.append(violation)

        except Exception as e:
            result.error = str(e)

        result.violations_found = len(result.violations)
        return result


class LocalOutlierFactorRule(AuditRule):
    """ML-002: Anomaly detection using Local Outlier Factor."""

    def __init__(
        self,
        contamination: float = 0.01,
        n_neighbors: int = 20,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.contamination = contamination
        self.n_neighbors = n_neighbors
        self.feature_extractor = FeatureExtractor()

    @property
    def rule_id(self) -> str:
        return "ML-002"

    @property
    def rule_name(self) -> str:
        return "LOF異常検知"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ML

    @property
    def description(self) -> str:
        return (
            "Local Outlier Factorアルゴリズムによる局所密度ベース異常検知を実行します。"
        )

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        if len(df) < 100:
            return result

        try:
            X, df_with_features = self.feature_extractor.extract_features(df)
            X_scaled = self.feature_extractor.fit_transform(X)

            # LOF requires novelty=False for training on the same data
            model = LocalOutlierFactor(
                n_neighbors=min(self.n_neighbors, len(df) - 1),
                contamination=self.contamination,
                novelty=False,
                n_jobs=-1,
            )
            predictions = model.fit_predict(X_scaled)
            scores = -model.negative_outlier_factor_  # Higher = more anomalous

            anomaly_mask = predictions == -1
            anomaly_indices = np.where(anomaly_mask)[0]

            for idx in anomaly_indices:
                row = df_with_features.row(idx, named=True)
                lof_score = scores[idx]

                violation = self._create_violation(
                    gl_detail_id=row["gl_detail_id"],
                    journal_id=row["journal_id"],
                    message=f"ML異常検知 (LOF): score={lof_score:.3f}",
                    details={
                        "algorithm": "LocalOutlierFactor",
                        "lof_score": float(lof_score),
                        "amount": row["amount"],
                    },
                    score_impact=min(lof_score * 5, 15.0),
                )
                result.violations.append(violation)

        except Exception as e:
            result.error = str(e)

        result.violations_found = len(result.violations)
        return result


class OneClassSVMRule(AuditRule):
    """ML-003: Anomaly detection using One-Class SVM."""

    def __init__(
        self,
        nu: float = 0.01,
        kernel: str = "rbf",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.nu = nu
        self.kernel = kernel
        self.feature_extractor = FeatureExtractor()

    @property
    def rule_id(self) -> str:
        return "ML-003"

    @property
    def rule_name(self) -> str:
        return "One-Class SVM異常検知"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ML

    @property
    def description(self) -> str:
        return "One-Class SVMアルゴリズムによる境界ベース異常検知を実行します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        # SVM is expensive, use sampling for large datasets
        max_samples = 10000
        if len(df) > max_samples:
            df = df.sample(n=max_samples, seed=42)
            result.total_checked = len(df)

        if len(df) < 100:
            return result

        try:
            X, df_with_features = self.feature_extractor.extract_features(df)
            X_scaled = self.feature_extractor.fit_transform(X)

            model = OneClassSVM(
                nu=self.nu,
                kernel=self.kernel,
                gamma="scale",
            )
            predictions = model.fit_predict(X_scaled)
            scores = -model.decision_function(X_scaled)  # Higher = more anomalous

            anomaly_mask = predictions == -1
            anomaly_indices = np.where(anomaly_mask)[0]

            for idx in anomaly_indices:
                row = df_with_features.row(idx, named=True)
                svm_score = scores[idx]

                violation = self._create_violation(
                    gl_detail_id=row["gl_detail_id"],
                    journal_id=row["journal_id"],
                    message=f"ML異常検知 (SVM): score={svm_score:.3f}",
                    details={
                        "algorithm": "OneClassSVM",
                        "svm_score": float(svm_score),
                        "amount": row["amount"],
                    },
                    score_impact=min(svm_score * 5, 15.0),
                )
                result.violations.append(violation)

        except Exception as e:
            result.error = str(e)

        result.violations_found = len(result.violations)
        return result


class AutoencoderRule(AuditRule):
    """ML-004: Anomaly detection using Autoencoder reconstruction error.

    Note: Uses a simple sklearn-based approach instead of deep learning
    to avoid heavy dependencies.
    """

    def __init__(
        self,
        threshold_percentile: float = 99.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.threshold_percentile = threshold_percentile
        self.feature_extractor = FeatureExtractor()

    @property
    def rule_id(self) -> str:
        return "ML-004"

    @property
    def rule_name(self) -> str:
        return "再構成エラー異常検知"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ML

    @property
    def description(self) -> str:
        return "PCAベースの再構成エラーによる異常検知を実行します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        if len(df) < 100:
            return result

        try:
            from sklearn.decomposition import PCA

            X, df_with_features = self.feature_extractor.extract_features(df)
            X_scaled = self.feature_extractor.fit_transform(X)

            # Use PCA for dimensionality reduction and reconstruction
            n_components = min(5, X_scaled.shape[1] - 1)
            pca = PCA(n_components=n_components)

            # Transform and inverse transform
            X_reduced = pca.fit_transform(X_scaled)
            X_reconstructed = pca.inverse_transform(X_reduced)

            # Calculate reconstruction error
            reconstruction_errors = np.mean((X_scaled - X_reconstructed) ** 2, axis=1)

            # Set threshold
            threshold = np.percentile(reconstruction_errors, self.threshold_percentile)

            # Find anomalies
            anomaly_mask = reconstruction_errors > threshold
            anomaly_indices = np.where(anomaly_mask)[0]

            for idx in anomaly_indices:
                row = df_with_features.row(idx, named=True)
                error = reconstruction_errors[idx]

                violation = self._create_violation(
                    gl_detail_id=row["gl_detail_id"],
                    journal_id=row["journal_id"],
                    message=f"ML異常検知 (再構成): error={error:.3f}",
                    details={
                        "algorithm": "PCA-Reconstruction",
                        "reconstruction_error": float(error),
                        "threshold": float(threshold),
                        "amount": row["amount"],
                    },
                    score_impact=min(error * 10, 15.0),
                )
                result.violations.append(violation)

        except Exception as e:
            result.error = str(e)

        result.violations_found = len(result.violations)
        return result


class EnsembleAnomalyRule(AuditRule):
    """ML-005: Ensemble anomaly detection combining multiple methods."""

    def __init__(
        self,
        min_votes: int = 2,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.min_votes = min_votes
        self.feature_extractor = FeatureExtractor()

    @property
    def rule_id(self) -> str:
        return "ML-005"

    @property
    def rule_name(self) -> str:
        return "アンサンブル異常検知"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ML

    @property
    def description(self) -> str:
        return "複数のMLアルゴリズムを組み合わせた投票ベース異常検知を実行します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        if len(df) < 100:
            return result

        try:
            X, df_with_features = self.feature_extractor.extract_features(df)
            X_scaled = self.feature_extractor.fit_transform(X)

            n_samples = len(X_scaled)
            votes = np.zeros(n_samples)
            scores = np.zeros(n_samples)

            # Isolation Forest
            try:
                if_model = IsolationForest(
                    contamination=0.02,
                    n_estimators=100,
                    random_state=42,
                    n_jobs=-1,
                )
                if_pred = if_model.fit_predict(X_scaled)
                if_scores = -if_model.score_samples(X_scaled)
                votes += (if_pred == -1).astype(int)
                scores += if_scores
            except Exception:
                pass

            # LOF
            try:
                lof_model = LocalOutlierFactor(
                    n_neighbors=min(20, n_samples - 1),
                    contamination=0.02,
                    novelty=False,
                    n_jobs=-1,
                )
                lof_pred = lof_model.fit_predict(X_scaled)
                lof_scores = -lof_model.negative_outlier_factor_
                votes += (lof_pred == -1).astype(int)
                scores += lof_scores
            except Exception:
                pass

            # One-Class SVM (sample for performance)
            try:
                if n_samples <= 5000:
                    svm_model = OneClassSVM(nu=0.02, kernel="rbf", gamma="scale")
                    svm_pred = svm_model.fit_predict(X_scaled)
                    svm_scores = -svm_model.decision_function(X_scaled)
                    votes += (svm_pred == -1).astype(int)
                    scores += svm_scores
            except Exception:
                pass

            # Find consensus anomalies
            anomaly_mask = votes >= self.min_votes
            anomaly_indices = np.where(anomaly_mask)[0]

            for idx in anomaly_indices:
                row = df_with_features.row(idx, named=True)
                vote_count = int(votes[idx])
                combined_score = scores[idx]

                violation = self._create_violation(
                    gl_detail_id=row["gl_detail_id"],
                    journal_id=row["journal_id"],
                    message=f"アンサンブル異常: {vote_count}手法で検出",
                    details={
                        "algorithm": "Ensemble",
                        "vote_count": vote_count,
                        "combined_score": float(combined_score),
                        "amount": row["amount"],
                    },
                    score_impact=vote_count * 8.0,  # Higher impact for consensus
                )
                result.violations.append(violation)

        except Exception as e:
            result.error = str(e)

        result.violations_found = len(result.violations)
        return result


def create_ml_rule_set() -> RuleSet:
    """Create the complete ML anomaly detection rule set.

    Returns:
        RuleSet with all 5 ML rules.
    """
    rule_set = RuleSet(
        name="ml_rules",
        description="機械学習による異常検知ルール (5件)",
    )

    rules = [
        IsolationForestRule(),
        LocalOutlierFactorRule(),
        OneClassSVMRule(),
        AutoencoderRule(),
        EnsembleAnomalyRule(),
    ]

    for rule in rules:
        rule_set.add_rule(rule)

    return rule_set
