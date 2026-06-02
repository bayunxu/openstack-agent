"""
Failure Predictor Module
Predicts potential failures based on historical data and patterns
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict

try:
    from prophet import Prophet
except ImportError:
    Prophet = None

logger = logging.getLogger(__name__)


class FailurePredictor:
    """
    Predicts potential failures using time-series analysis
    """

    def __init__(self):
        """
        Initialize failure predictor
        """
        self.models: Dict[str, Any] = {}
        self.metric_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.predictions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def add_historical_data(self, metric_name: str, timestamp: datetime, value: float):
        """
        Add historical metric data

        Args:
            metric_name: Name of the metric
            timestamp: Timestamp of the metric
            value: Metric value
        """
        self.metric_history[metric_name].append({
            'timestamp': timestamp,
            'value': value
        })

        # Keep last 2000 data points
        if len(self.metric_history[metric_name]) > 2000:
            self.metric_history[metric_name] = self.metric_history[metric_name][-2000:]

    def predict_failures(self, metric_name: str, periods: int = 24, freq: str = 'H') -> List[Dict[str, Any]]:
        """
        Predict potential failures for a metric

        Args:
            metric_name: Name of the metric
            periods: Number of periods to forecast
            freq: Frequency of predictions (H=hourly, D=daily, etc.)

        Returns:
            List of predictions
        """
        if metric_name not in self.metric_history:
            logger.warning(f"No history for metric: {metric_name}")
            return []

        history = self.metric_history[metric_name]
        if len(history) < 50:
            logger.debug(f"Insufficient data for prediction: {len(history)} < 50")
            return []

        predictions = []

        # Use simple trend analysis if Prophet is not available
        if Prophet is None:
            predictions = self._predict_with_trend_analysis(metric_name, history, periods)
        else:
            predictions = self._predict_with_prophet(metric_name, history, periods)

        self.predictions[metric_name] = predictions
        return predictions

    def _predict_with_trend_analysis(self, metric_name: str, history: List[Dict[str, Any]], periods: int) -> List[Dict[str, Any]]:
        """
        Simple trend-based prediction
        """
        predictions = []
        values = np.array([h['value'] for h in history])
        timestamps = [h['timestamp'] for h in history]

        # Calculate trend
        x = np.arange(len(values))
        coeffs = np.polyfit(x, values, 1)
        poly = np.poly1d(coeffs)

        # Generate predictions
        last_timestamp = timestamps[-1]
        last_index = len(values)

        for i in range(1, periods + 1):
            pred_value = poly(last_index + i)
            pred_timestamp = last_timestamp + timedelta(hours=i)

            # Check for concerning trends
            threshold = np.mean(values) * 1.5
            is_concerning = pred_value > threshold

            predictions.append({
                'timestamp': pred_timestamp.isoformat(),
                'predicted_value': float(pred_value),
                'is_concerning': is_concerning,
                'confidence': 0.6,
                'reason': 'Trend analysis indicates potential increase' if is_concerning else 'Normal trend expected'
            })

        return predictions

    def _predict_with_prophet(self, metric_name: str, history: List[Dict[str, Any]], periods: int) -> List[Dict[str, Any]]:
        """
        Prophet-based time series prediction
        """
        try:
            # Prepare data for Prophet
            df_data = {
                'ds': [h['timestamp'] for h in history],
                'y': [h['value'] for h in history]
            }
            import pandas as pd
            df = pd.DataFrame(df_data)

            # Train model
            model = Prophet(yearly_seasonality=False, daily_seasonality=False, interval_width=0.95)
            model.fit(df)

            # Make forecast
            future = model.make_future_dataframe(periods=periods)
            forecast = model.predict(future)

            # Extract predictions
            predictions = []
            for _, row in forecast.iloc[-periods:].iterrows():
                pred_value = row['yhat']
                is_concerning = pred_value > (np.mean(df['y']) * 1.5)

                predictions.append({
                    'timestamp': row['ds'].isoformat(),
                    'predicted_value': float(pred_value),
                    'confidence_low': float(row['yhat_lower']),
                    'confidence_high': float(row['yhat_upper']),
                    'is_concerning': is_concerning,
                    'confidence': 0.85
                })

            return predictions
        except Exception as e:
            logger.error(f"Error in Prophet prediction: {str(e)}")
            return []

    def detect_anomaly_trends(self, metric_name: str, window_size: int = 10) -> Dict[str, Any]:
        """
        Detect trends that might lead to failures

        Args:
            metric_name: Name of the metric
            window_size: Size of the window for trend analysis

        Returns:
            Trend analysis result
        """
        if metric_name not in self.metric_history:
            return {}

        history = self.metric_history[metric_name][-window_size:]
        if len(history) < window_size:
            return {}

        values = np.array([h['value'] for h in history])

        # Calculate statistics
        mean = np.mean(values)
        std = np.std(values)
        trend = values[-1] - values[0]
        trend_direction = 'increasing' if trend > 0 else 'decreasing'
        trend_rate = abs(trend) / window_size

        # Check for concerning patterns
        concerns = []
        if trend_rate > std:
            concerns.append(f"Rapid {trend_direction} trend detected")
        if values[-1] > mean + 2 * std:
            concerns.append("Current value significantly above average")
        if std > mean * 0.5:
            concerns.append("High variability in metric")

        return {
            'metric_name': metric_name,
            'current_value': float(values[-1]),
            'average_value': float(mean),
            'std_deviation': float(std),
            'trend': trend_direction,
            'trend_rate': float(trend_rate),
            'concerns': concerns,
            'risk_level': 'high' if len(concerns) >= 2 else 'medium' if len(concerns) >= 1 else 'low'
        }

    def get_predictions(self, metric_name: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get predictions

        Args:
            metric_name: Optional specific metric (default: all)

        Returns:
            Dictionary of predictions
        """
        if metric_name:
            return {metric_name: self.predictions.get(metric_name, [])}
        return dict(self.predictions)
