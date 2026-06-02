"""
Anomaly Detection Module
Uses machine learning to detect anomalies in OpenStack metrics
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Detects anomalies in time-series metrics using Isolation Forest
    """

    def __init__(self, contamination: float = 0.1, window_size: int = 100):
        """
        Initialize anomaly detector

        Args:
            contamination: Expected proportion of anomalies (default: 0.1)
            window_size: Minimum data points required for detection
        """
        self.contamination = contamination
        self.window_size = window_size
        self.models: Dict[str, IsolationForest] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.metric_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self.anomalies: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def add_metric(self, metric_name: str, value: float, timestamp: Optional[datetime] = None):
        """
        Add a metric data point

        Args:
            metric_name: Name of the metric
            value: Metric value
            timestamp: Timestamp of the metric (default: now)
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        self.metric_history[metric_name].append((timestamp, value))

        # Keep only last 1000 data points per metric
        if len(self.metric_history[metric_name]) > 1000:
            self.metric_history[metric_name] = self.metric_history[metric_name][-1000:]

    def detect_anomalies(self, metric_name: str) -> List[Dict[str, Any]]:
        """
        Detect anomalies for a metric

        Args:
            metric_name: Name of the metric

        Returns:
            List of detected anomalies
        """
        if metric_name not in self.metric_history:
            logger.warning(f"No history for metric: {metric_name}")
            return []

        history = self.metric_history[metric_name]
        if len(history) < self.window_size:
            logger.debug(f"Insufficient data for {metric_name}: {len(history)} < {self.window_size}")
            return []

        # Extract values
        values = np.array([v for _, v in history]).reshape(-1, 1)
        timestamps = [t for t, _ in history]

        # Train or update model
        if metric_name not in self.models:
            self.models[metric_name] = IsolationForest(
                contamination=self.contamination,
                random_state=42,
                n_estimators=100
            )
            self.scalers[metric_name] = StandardScaler()
            scaled_values = self.scalers[metric_name].fit_transform(values)
        else:
            scaled_values = self.scalers[metric_name].transform(values)

        # Predict anomalies
        predictions = self.models[metric_name].predict(scaled_values)
        anomaly_scores = self.models[metric_name].score_samples(scaled_values)

        # Find anomalies
        detected_anomalies = []
        for idx, (pred, score) in enumerate(zip(predictions, anomaly_scores)):
            if pred == -1:  # Anomaly detected
                anomaly_info = {
                    'metric_name': metric_name,
                    'timestamp': timestamps[idx].isoformat(),
                    'value': values[idx][0],
                    'anomaly_score': float(score),
                    'severity': self._score_to_severity(score)
                }
                detected_anomalies.append(anomaly_info)

        # Store detected anomalies
        if detected_anomalies:
            self.anomalies[metric_name].extend(detected_anomalies)
            logger.warning(f"Detected {len(detected_anomalies)} anomalies for {metric_name}")

        return detected_anomalies

    def _score_to_severity(self, score: float) -> str:
        """
        Convert anomaly score to severity level

        Args:
            score: Anomaly score (lower is more anomalous)

        Returns:
            Severity level
        """
        if score < -0.5:
            return "critical"
        elif score < 0:
            return "high"
        else:
            return "medium"

    def detect_anomalies_batch(self, metrics: Dict[str, float]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detect anomalies for multiple metrics

        Args:
            metrics: Dictionary of metric_name -> value

        Returns:
            Dictionary of metric_name -> list of anomalies
        """
        results = {}
        for metric_name, value in metrics.items():
            self.add_metric(metric_name, value)
            anomalies = self.detect_anomalies(metric_name)
            if anomalies:
                results[metric_name] = anomalies
        return results

    def get_anomaly_history(self, metric_name: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get anomaly history

        Args:
            metric_name: Optional specific metric (default: all)

        Returns:
            Dictionary of anomalies
        """
        if metric_name:
            return {metric_name: self.anomalies.get(metric_name, [])}
        return dict(self.anomalies)

    def get_metric_statistics(self, metric_name: str) -> Dict[str, float]:
        """
        Get statistics for a metric

        Args:
            metric_name: Name of the metric

        Returns:
            Statistics dictionary
        """
        if metric_name not in self.metric_history:
            return {}

        values = np.array([v for _, v in self.metric_history[metric_name]])
        return {
            'count': len(values),
            'mean': float(np.mean(values)),
            'std': float(np.std(values)),
            'min': float(np.min(values)),
            'max': float(np.max(values)),
            'p50': float(np.percentile(values, 50)),
            'p95': float(np.percentile(values, 95)),
            'p99': float(np.percentile(values, 99))
        }
