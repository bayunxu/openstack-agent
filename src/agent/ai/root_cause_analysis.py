"""
Root Cause Analysis Module
Uses correlation analysis and ML to determine root causes of failures
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RootCauseCandidate:
    """Represents a potential root cause"""
    component: str
    metric_name: str
    anomaly_value: float
    confidence: float
    correlation_score: float
    supporting_metrics: List[str]
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'component': self.component,
            'metric_name': self.metric_name,
            'anomaly_value': self.anomaly_value,
            'confidence': self.confidence,
            'correlation_score': self.correlation_score,
            'supporting_metrics': self.supporting_metrics,
            'description': self.description
        }


class RootCauseAnalyzer:
    """
    Performs root cause analysis on OpenStack failures
    """

    def __init__(self):
        """
        Initialize root cause analyzer
        """
        self.anomaly_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.dependency_graph: Dict[str, List[str]] = self._build_dependency_graph()
        self.component_relationships: Dict[str, List[Tuple[str, float]]] = {}

    def _build_dependency_graph(self) -> Dict[str, List[str]]:
        """
        Build dependency graph for OpenStack components

        Returns:
            Dictionary mapping component to its dependencies
        """
        return {
            'nova': ['keystone', 'rabbitmq', 'mysql', 'neutron', 'glance'],
            'neutron': ['keystone', 'rabbitmq', 'mysql'],
            'glance': ['keystone', 'mysql'],
            'cinder': ['keystone', 'rabbitmq', 'mysql'],
            'keystone': ['mysql'],
            'rabbitmq': [],
            'mysql': [],
            'redis': [],
            'hypervisor': ['nova'],
            'network_agent': ['neutron', 'rabbitmq']
        }

    def analyze_failure(self, affected_components: List[str], anomalies: Dict[str, List[Dict[str, Any]]]) -> List[RootCauseCandidate]:
        """
        Analyze failure to determine root cause

        Args:
            affected_components: List of affected components
            anomalies: Dictionary of detected anomalies

        Returns:
            List of root cause candidates ranked by confidence
        """
        candidates: List[RootCauseCandidate] = []

        # 1. Check if failure originated from dependency
        for component in affected_components:
            deps = self.dependency_graph.get(component, [])
            for dep in deps:
                if self._has_anomaly(dep, anomalies):
                    confidence = self._calculate_confidence(component, dep, anomalies)
                    candidate = RootCauseCandidate(
                        component=dep,
                        metric_name=self._get_critical_metric(dep, anomalies),
                        anomaly_value=self._get_anomaly_value(dep, anomalies),
                        confidence=confidence,
                        correlation_score=self._calculate_correlation(component, dep, anomalies),
                        supporting_metrics=self._get_supporting_metrics(dep, anomalies),
                        description=f"{dep} anomaly is causing {component} failure"
                    )
                    candidates.append(candidate)

        # 2. Check for middleware issues
        middleware_issues = self._detect_middleware_issues(anomalies)
        candidates.extend(middleware_issues)

        # 3. Sort by confidence
        candidates.sort(key=lambda x: x.confidence, reverse=True)

        logger.info(f"Found {len(candidates)} root cause candidates")
        return candidates

    def _has_anomaly(self, component: str, anomalies: Dict[str, List[Dict[str, Any]]]) -> bool:
        """
        Check if component has detected anomalies
        """
        for metric_name, anomaly_list in anomalies.items():
            if component.lower() in metric_name.lower() and anomaly_list:
                return True
        return False

    def _get_critical_metric(self, component: str, anomalies: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Get the most critical metric for a component
        """
        for metric_name, anomaly_list in anomalies.items():
            if component.lower() in metric_name.lower() and anomaly_list:
                return metric_name
        return f"openstack.{component}.status"

    def _get_anomaly_value(self, component: str, anomalies: Dict[str, List[Dict[str, Any]]]) -> float:
        """
        Get the anomaly value for a component
        """
        for metric_name, anomaly_list in anomalies.items():
            if component.lower() in metric_name.lower() and anomaly_list:
                return anomaly_list[0].get('value', 0.0)
        return 0.0

    def _calculate_confidence(self, affected: str, potential_cause: str, anomalies: Dict[str, List[Dict[str, Any]]]) -> float:
        """
        Calculate confidence that potential_cause is root cause of affected failure

        Args:
            affected: Affected component
            potential_cause: Potential root cause component
            anomalies: Detected anomalies

        Returns:
            Confidence score between 0 and 1
        """
        score = 0.5  # Base confidence

        # Check dependency relationship
        if potential_cause in self.dependency_graph.get(affected, []):
            score += 0.3

        # Check anomaly severity
        for metric_name, anomaly_list in anomalies.items():
            if potential_cause.lower() in metric_name.lower():
                for anomaly in anomaly_list:
                    if anomaly.get('severity') == 'critical':
                        score += 0.15
                    elif anomaly.get('severity') == 'high':
                        score += 0.10

        return min(score, 1.0)

    def _calculate_correlation(self, component1: str, component2: str, anomalies: Dict[str, List[Dict[str, Any]]]) -> float:
        """
        Calculate correlation between two components
        """
        # Simple correlation based on anomaly timing
        timestamps1 = []
        timestamps2 = []

        for metric_name, anomaly_list in anomalies.items():
            if component1.lower() in metric_name.lower():
                timestamps1.extend([a.get('timestamp') for a in anomaly_list])
            if component2.lower() in metric_name.lower():
                timestamps2.extend([a.get('timestamp') for a in anomaly_list])

        if not timestamps1 or not timestamps2:
            return 0.0

        # Check time proximity
        time_diff_threshold = 60  # seconds
        matching_pairs = 0
        for t1 in timestamps1:
            for t2 in timestamps2:
                try:
                    diff = abs((datetime.fromisoformat(t1) - datetime.fromisoformat(t2)).total_seconds())
                    if diff < time_diff_threshold:
                        matching_pairs += 1
                except:
                    pass

        return min(matching_pairs / max(len(timestamps1), len(timestamps2)), 1.0) if max(len(timestamps1), len(timestamps2)) > 0 else 0.0

    def _get_supporting_metrics(self, component: str, anomalies: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        """
        Get supporting metrics for a component
        """
        supporting = []
        for metric_name, anomaly_list in anomalies.items():
            if component.lower() in metric_name.lower() and anomaly_list:
                supporting.append(metric_name)
        return supporting

    def _detect_middleware_issues(self, anomalies: Dict[str, List[Dict[str, Any]]]) -> List[RootCauseCandidate]:
        """
        Detect middleware-related root causes
        """
        candidates: List[RootCauseCandidate] = []
        middleware_components = ['rabbitmq', 'mysql', 'redis', 'memcached']

        for middleware in middleware_components:
            for metric_name, anomaly_list in anomalies.items():
                if middleware in metric_name.lower() and anomaly_list:
                    for anomaly in anomaly_list:
                        candidate = RootCauseCandidate(
                            component=middleware,
                            metric_name=metric_name,
                            anomaly_value=anomaly.get('value', 0.0),
                            confidence=0.8 if anomaly.get('severity') == 'critical' else 0.6,
                            correlation_score=0.7,
                            supporting_metrics=[metric_name],
                            description=f"{middleware} middleware issue detected"
                        )
                        candidates.append(candidate)

        return candidates

    def generate_diagnosis_report(self, incident_id: str, affected_components: List[str],
                                   anomalies: Dict[str, List[Dict[str, Any]]],
                                   alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate comprehensive diagnosis report

        Args:
            incident_id: Incident identifier
            affected_components: List of affected components
            anomalies: Detected anomalies
            alerts: Associated alerts

        Returns:
            Diagnosis report
        """
        root_causes = self.analyze_failure(affected_components, anomalies)

        report = {
            'incident_id': incident_id,
            'timestamp': datetime.utcnow().isoformat(),
            'affected_components': affected_components,
            'anomaly_count': sum(len(a) for a in anomalies.values()),
            'alert_count': len(alerts),
            'root_cause_candidates': [rc.to_dict() for rc in root_causes],
            'primary_root_cause': root_causes[0].to_dict() if root_causes else None,
            'recommendations': self._generate_recommendations(root_causes),
            'severity': self._calculate_incident_severity(affected_components, anomalies)
        }

        return report

    def _generate_recommendations(self, root_causes: List[RootCauseCandidate]) -> List[str]:
        """
        Generate remediation recommendations
        """
        recommendations = []

        if root_causes:
            primary = root_causes[0]
            if 'rabbitmq' in primary.component.lower():
                recommendations.extend([
                    "Check RabbitMQ service status: systemctl status rabbitmq-server",
                    "Verify RabbitMQ disk and memory usage",
                    "Check RabbitMQ queues for message backlog",
                    "Restart RabbitMQ service if necessary: systemctl restart rabbitmq-server"
                ])
            elif 'mysql' in primary.component.lower():
                recommendations.extend([
                    "Check MySQL service status: systemctl status mysql",
                    "Monitor MySQL connections and queries",
                    "Check database locks and slow queries",
                    "Restart MySQL service if necessary"
                ])
            elif 'nova' in primary.component.lower():
                recommendations.extend([
                    "Check Nova service status on controller and compute nodes",
                    "Review Nova logs for errors",
                    "Verify hypervisor connectivity"
                ])
            elif 'neutron' in primary.component.lower():
                recommendations.extend([
                    "Check Neutron agents status: openstack network agent list",
                    "Verify network connectivity between nodes",
                    "Review Neutron logs for errors"
                ])

        recommendations.extend([
            "Escalate to senior administrator if issue persists",
            "Collect diagnostic data for further analysis"
        ])

        return recommendations

    def _calculate_incident_severity(self, affected_components: List[str], anomalies: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Calculate incident severity
        """
        critical_components = ['keystone', 'nova', 'mysql']
        affected_critical = any(c in critical_components for c in affected_components)

        anomaly_count = sum(len(a) for a in anomalies.values())
        critical_anomalies = sum(1 for a_list in anomalies.values() for a in a_list if a.get('severity') == 'critical')

        if affected_critical and critical_anomalies > 0:
            return 'critical'
        elif anomaly_count > 5:
            return 'high'
        elif anomaly_count > 2:
            return 'medium'
        else:
            return 'low'
