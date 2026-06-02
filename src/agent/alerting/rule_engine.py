"""
Alert Rule Engine
Provides rule-based alerting for OpenStack components
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from datetime import datetime, timedelta
import json
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(Enum):
    """Alert status"""
    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass
class Alert:
    """Represents an alert"""
    id: str
    rule_id: str
    name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    component: str
    metric_name: str
    metric_value: float
    threshold: float
    triggered_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    annotations: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['severity'] = self.severity.value
        data['status'] = self.status.value
        data['triggered_at'] = self.triggered_at.isoformat()
        data['acknowledged_at'] = self.acknowledged_at.isoformat() if self.acknowledged_at else None
        data['resolved_at'] = self.resolved_at.isoformat() if self.resolved_at else None
        return data


class AlertRule:
    """Alert rule definition"""

    def __init__(self, rule_id: str, name: str, metric_name: str, severity: AlertSeverity,
                 operator: str, threshold: float, duration: int = 300, enabled: bool = True):
        """
        Initialize alert rule

        Args:
            rule_id: Unique rule identifier
            name: Rule name
            metric_name: Metric name to monitor
            severity: Alert severity level
            operator: Comparison operator (>, <, >=, <=, ==, !=)
            threshold: Threshold value
            duration: Duration in seconds that condition must be met (default: 300)
            enabled: Whether the rule is enabled
        """
        self.rule_id = rule_id
        self.name = name
        self.metric_name = metric_name
        self.severity = severity
        self.operator = operator
        self.threshold = threshold
        self.duration = duration
        self.enabled = enabled
        self.component = self._extract_component(metric_name)
        self.condition_start_time: Optional[datetime] = None

    def _extract_component(self, metric_name: str) -> str:
        """Extract component name from metric name"""
        parts = metric_name.split('.')
        return parts[1] if len(parts) > 1 else 'unknown'

    def evaluate(self, metric_value: float) -> bool:
        """
        Evaluate if metric violates this rule

        Args:
            metric_value: Metric value to check

        Returns:
            True if rule is violated
        """
        if not self.enabled:
            return False

        if self.operator == '>':
            return metric_value > self.threshold
        elif self.operator == '<':
            return metric_value < self.threshold
        elif self.operator == '>=':
            return metric_value >= self.threshold
        elif self.operator == '<=':
            return metric_value <= self.threshold
        elif self.operator == '==':
            return metric_value == self.threshold
        elif self.operator == '!=':
            return metric_value != self.threshold
        else:
            logger.warning(f"Unknown operator: {self.operator}")
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'rule_id': self.rule_id,
            'name': self.name,
            'metric_name': self.metric_name,
            'severity': self.severity.value,
            'operator': self.operator,
            'threshold': self.threshold,
            'duration': self.duration,
            'enabled': self.enabled,
            'component': self.component
        }


class AlertRuleEngine:
    """
    Rule-based alert engine
    Evaluates metrics against predefined rules and generates alerts
    """

    def __init__(self):
        """
        Initialize alert rule engine
        """
        self.rules: Dict[str, AlertRule] = {}
        self.alerts: Dict[str, Alert] = {}
        self.triggered_conditions: Dict[str, datetime] = {}  # Track when conditions started
        self.alert_counter = 0

    def add_rule(self, rule: AlertRule):
        """
        Add alert rule

        Args:
            rule: AlertRule instance
        """
        self.rules[rule.rule_id] = rule
        logger.info(f"Added alert rule: {rule.rule_id}")

    def remove_rule(self, rule_id: str):
        """
        Remove alert rule

        Args:
            rule_id: Rule ID to remove
        """
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Removed alert rule: {rule_id}")

    def enable_rule(self, rule_id: str):
        """Enable a rule"""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True

    def disable_rule(self, rule_id: str):
        """Disable a rule"""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False

    def evaluate_metric(self, metric_name: str, metric_value: float, component: str = '') -> List[Alert]:
        """
        Evaluate metric against all applicable rules

        Args:
            metric_name: Name of the metric
            metric_value: Value of the metric
            component: Component associated with metric

        Returns:
            List of triggered alerts
        """
        triggered_alerts: List[Alert] = []
        now = datetime.utcnow()

        for rule_id, rule in self.rules.items():
            if rule.metric_name != metric_name:
                continue

            if rule.evaluate(metric_value):
                # Condition is met, check if it has persisted long enough
                condition_key = f"{rule_id}_{metric_name}"

                if condition_key not in self.triggered_conditions:
                    # First time this condition is met
                    self.triggered_conditions[condition_key] = now
                    logger.info(f"Condition met for rule {rule_id}: {metric_name}={metric_value}")

                elapsed = (now - self.triggered_conditions[condition_key]).total_seconds()

                if elapsed >= rule.duration:
                    # Condition has persisted, generate alert
                    alert = self._create_alert(rule, metric_name, metric_value, component)
                    self.alerts[alert.id] = alert
                    triggered_alerts.append(alert)
                    logger.warning(f"Alert triggered: {alert.name}")
            else:
                # Condition no longer met, clean up
                condition_key = f"{rule_id}_{metric_name}"
                if condition_key in self.triggered_conditions:
                    del self.triggered_conditions[condition_key]
                    logger.info(f"Condition cleared for rule {rule_id}: {metric_name}")

        return triggered_alerts

    def _create_alert(self, rule: AlertRule, metric_name: str, metric_value: float, component: str) -> Alert:
        """Create an alert from a rule"""
        self.alert_counter += 1
        alert_id = f"alert_{self.alert_counter}_{int(datetime.utcnow().timestamp())}"

        return Alert(
            id=alert_id,
            rule_id=rule.rule_id,
            name=rule.name,
            severity=rule.severity,
            status=AlertStatus.TRIGGERED,
            message=f"{rule.name}: {metric_name} = {metric_value} (threshold: {rule.threshold})",
            component=component or rule.component,
            metric_name=metric_name,
            metric_value=metric_value,
            threshold=rule.threshold,
            triggered_at=datetime.utcnow(),
            annotations={'rule_id': rule.rule_id, 'operator': rule.operator}
        )

    def get_alerts(self, status: Optional[AlertStatus] = None, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """
        Get alerts filtered by status and/or severity

        Args:
            status: Filter by alert status
            severity: Filter by alert severity

        Returns:
            List of alerts
        """
        alerts = list(self.alerts.values())

        if status:
            alerts = [a for a in alerts if a.status == status]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return alerts

    def acknowledge_alert(self, alert_id: str):
        """Acknowledge an alert"""
        if alert_id in self.alerts:
            self.alerts[alert_id].status = AlertStatus.ACKNOWLEDGED
            self.alerts[alert_id].acknowledged_at = datetime.utcnow()
            logger.info(f"Alert acknowledged: {alert_id}")

    def resolve_alert(self, alert_id: str):
        """Resolve an alert"""
        if alert_id in self.alerts:
            self.alerts[alert_id].status = AlertStatus.RESOLVED
            self.alerts[alert_id].resolved_at = datetime.utcnow()
            logger.info(f"Alert resolved: {alert_id}")

    def get_active_alerts(self) -> List[Alert]:
        """Get all active (triggered or acknowledged) alerts"""
        return [
            a for a in self.alerts.values()
            if a.status in [AlertStatus.TRIGGERED, AlertStatus.ACKNOWLEDGED]
        ]

    def load_rules_from_config(self, config: Dict[str, Any]):
        """
        Load rules from configuration dictionary

        Args:
            config: Configuration dictionary with rules
        """
        if 'rules' not in config:
            logger.warning("No rules found in configuration")
            return

        for rule_config in config['rules']:
            try:
                rule = AlertRule(
                    rule_id=rule_config.get('id', rule_config.get('name')),
                    name=rule_config.get('name'),
                    metric_name=rule_config.get('metric'),
                    severity=AlertSeverity(rule_config.get('severity', 'warning')),
                    operator=rule_config.get('operator'),
                    threshold=rule_config.get('threshold'),
                    duration=rule_config.get('duration', 300),
                    enabled=rule_config.get('enabled', True)
                )
                self.add_rule(rule)
            except Exception as e:
                logger.error(f"Error loading rule from config: {str(e)}")

    def get_rules(self) -> List[AlertRule]:
        """Get all alert rules"""
        return list(self.rules.values())
