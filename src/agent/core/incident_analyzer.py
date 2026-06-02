"""
Comprehensive Diagnostic and Incident Analysis Module
Integrates middleware monitoring with root cause analysis for complete failure diagnosis
"""

import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass

from .middleware_monitor import MiddlewareMonitor, MiddlewareHealthStatus
from ..ai.root_cause_analysis import RootCauseAnalyzer, RootCauseCandidate
from ..alerting.rule_engine import Alert, AlertSeverity
from ..core.health_check import HealthChecker

logger = logging.getLogger(__name__)


@dataclass
class IncidentContext:
    """Context information for an incident"""
    incident_id: str
    timestamp: datetime
    affected_openstack_components: List[str]
    affected_middleware: List[str]
    detected_anomalies: Dict[str, List[Dict[str, Any]]]
    triggered_alerts: List[Alert]
    middleware_issues: List[Dict[str, Any]]
    dependency_chain: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'incident_id': self.incident_id,
            'timestamp': self.timestamp.isoformat(),
            'affected_openstack_components': self.affected_openstack_components,
            'affected_middleware': self.affected_middleware,
            'detected_anomalies': self.detected_anomalies,
            'triggered_alerts': [a.to_dict() for a in self.triggered_alerts],
            'middleware_issues': self.middleware_issues,
            'dependency_chain': self.dependency_chain
        }


class IncidentAnalyzer:
    """
    Comprehensive incident analysis integrating all monitoring and analysis components
    """

    def __init__(self, health_checker: HealthChecker, root_cause_analyzer: RootCauseAnalyzer,
                 middleware_monitor: MiddlewareMonitor):
        """
        Initialize incident analyzer

        Args:
            health_checker: HealthChecker instance
            root_cause_analyzer: RootCauseAnalyzer instance
            middleware_monitor: MiddlewareMonitor instance
        """
        self.health_checker = health_checker
        self.root_cause_analyzer = root_cause_analyzer
        self.middleware_monitor = middleware_monitor
        self.incident_history: Dict[str, IncidentContext] = {}
        self.incident_counter = 0

    def analyze_incident(self, detected_anomalies: Dict[str, List[Dict[str, Any]]],
                        alerts: List[Alert]) -> Dict[str, Any]:
        """
        Analyze a detected incident comprehensively

        Args:
            detected_anomalies: Detected anomalies from AI module
            alerts: Triggered alerts

        Returns:
            Comprehensive incident analysis report
        """
        self.incident_counter += 1
        incident_id = f"incident_{self.incident_counter}_{int(datetime.utcnow().timestamp())}"

        logger.info(f"Starting incident analysis: {incident_id}")

        # Step 1: Determine affected OpenStack components
        affected_openstack_components = self._extract_affected_components(alerts)

        # Step 2: Check middleware health
        middleware_issues = self.middleware_monitor.get_critical_issues()
        affected_middleware = [issue['component'] for issue in middleware_issues]

        # Step 3: Perform root cause analysis
        root_causes = self.root_cause_analyzer.analyze_failure(
            affected_openstack_components,
            detected_anomalies
        )

        # Step 4: Build dependency chain to trace failure propagation
        dependency_chain = self._build_dependency_chain(
            affected_openstack_components,
            affected_middleware,
            root_causes
        )

        # Step 5: Create incident context
        incident_context = IncidentContext(
            incident_id=incident_id,
            timestamp=datetime.utcnow(),
            affected_openstack_components=affected_openstack_components,
            affected_middleware=affected_middleware,
            detected_anomalies=detected_anomalies,
            triggered_alerts=alerts,
            middleware_issues=middleware_issues,
            dependency_chain=dependency_chain
        )

        # Store incident
        self.incident_history[incident_id] = incident_context

        # Step 6: Generate comprehensive report
        report = self._generate_comprehensive_report(
            incident_id,
            incident_context,
            root_causes
        )

        logger.info(f"Incident analysis completed: {incident_id}, Root causes: {len(root_causes)}")

        return report

    def _extract_affected_components(self, alerts: List[Alert]) -> List[str]:
        """Extract affected components from alerts"""
        components: Set[str] = set()
        for alert in alerts:
            components.add(alert.component)
        return list(components)

    def _build_dependency_chain(self, openstack_components: List[str],
                                middleware_components: List[str],
                                root_causes: List[RootCauseCandidate]) -> List[str]:
        """
        Build dependency chain showing failure propagation

        Args:
            openstack_components: Affected OpenStack components
            middleware_components: Affected middleware components
            root_causes: Identified root causes

        Returns:
            Ordered list of components from root cause to final impact
        """
        chain: List[str] = []

        # Start with root causes
        if root_causes:
            primary_root_cause = root_causes[0]
            chain.append(primary_root_cause.component)

            # Add affected middleware
            chain.extend(middleware_components)

            # Add affected OpenStack components
            chain.extend(openstack_components)

        return chain

    def _generate_comprehensive_report(self, incident_id: str, context: IncidentContext,
                                       root_causes: List[RootCauseCandidate]) -> Dict[str, Any]:
        """
        Generate comprehensive incident analysis report

        Args:
            incident_id: Incident identifier
            context: Incident context
            root_causes: Root cause analysis results

        Returns:
            Comprehensive report dictionary
        """
        report = {
            'incident_id': incident_id,
            'timestamp': datetime.utcnow().isoformat(),
            'severity': self._calculate_severity(context),
            'status': 'active',

            # Executive Summary
            'summary': {
                'description': self._generate_summary_description(context),
                'affected_components': context.affected_openstack_components,
                'affected_middleware': context.affected_middleware,
                'anomaly_count': sum(len(a) for a in context.detected_anomalies.values()),
                'alert_count': len(context.triggered_alerts)
            },

            # Impact Analysis
            'impact_analysis': {
                'component_failures': context.affected_openstack_components,
                'middleware_failures': context.affected_middleware,
                'dependency_chain': context.dependency_chain,
                'potential_service_impact': self._assess_service_impact(context)
            },

            # Root Cause Analysis
            'root_cause_analysis': {
                'primary_root_cause': root_causes[0].to_dict() if root_causes else None,
                'contributing_factors': [rc.to_dict() for rc in root_causes[1:3]],
                'confidence': root_causes[0].confidence if root_causes else 0.0
            },

            # Timeline and Correlation
            'timeline': self._build_incident_timeline(context),
            'component_correlations': self._analyze_component_correlations(context),

            # Middleware Specific Analysis
            'middleware_analysis': self._analyze_middleware_issues(context),

            # Remediation Plan
            'remediation': {
                'immediate_actions': self._generate_immediate_actions(context, root_causes),
                'short_term_fixes': self._generate_short_term_fixes(context, root_causes),
                'long_term_preventions': self._generate_long_term_preventions(context, root_causes)
            },

            # Recommendations
            'recommendations': self._root_cause_analyzer.generate_recommendations(root_causes) if root_causes else [],

            # Detailed Diagnostics
            'diagnostics': {
                'detected_anomalies': context.detected_anomalies,
                'triggered_alerts': [a.to_dict() for a in context.triggered_alerts],
                'middleware_issues': context.middleware_issues
            }
        }

        return report

    def _calculate_severity(self, context: IncidentContext) -> str:\n        \"\"\"Calculate incident severity\"\"\"\n        critical_components = ['keystone', 'nova', 'mysql']\n        \n        affected_critical = any(c in critical_components for c in context.affected_openstack_components)\n        middleware_down = len(context.affected_middleware) > 0\n        anomaly_count = sum(len(a) for a in context.detected_anomalies.values())\n        critical_alerts = sum(1 for a in context.triggered_alerts if a.severity == AlertSeverity.CRITICAL)\n        \n        if affected_critical and middleware_down:\n            return 'critical'\n        elif affected_critical or critical_alerts > 0:\n            return 'high'\n        elif anomaly_count > 5:\n            return 'medium'\n        else:\n            return 'low'\n\n    def _generate_summary_description(self, context: IncidentContext) -> str:\n        \"\"\"Generate human-readable summary\"\"\"\n        components_str = ', '.join(context.affected_openstack_components) if context.affected_openstack_components else 'unknown'\n        middleware_str = ', '.join(context.affected_middleware) if context.affected_middleware else 'none'\n        \n        return f\"OpenStack components [{components_str}] experienced failures. Middleware issues detected: [{middleware_str}]. {len(context.triggered_alerts)} alerts triggered.\"\n\n    def _assess_service_impact(self, context: IncidentContext) -> Dict[str, Any]:\n        \"\"\"Assess impact on services\"\"\"\n        return {\n            'compute_services_affected': 'nova' in context.affected_openstack_components,\n            'storage_services_affected': 'cinder' in context.affected_openstack_components,\n            'network_services_affected': 'neutron' in context.affected_openstack_components,\n            'identity_services_affected': 'keystone' in context.affected_openstack_components,\n            'middleware_reliability': 'critical' if len(context.affected_middleware) > 1 else 'normal'\n        }\n\n    def _build_incident_timeline(self, context: IncidentContext) -> List[Dict[str, Any]]:\n        \"\"\"Build chronological timeline of incident\"\"\"\n        events: List[Dict[str, Any]] = []\n        \n        # Sort alerts by timestamp\n        sorted_alerts = sorted(context.triggered_alerts, key=lambda a: a.triggered_at)\n        \n        for alert in sorted_alerts:\n            events.append({\n                'timestamp': alert.triggered_at.isoformat(),\n                'event_type': 'alert',\n                'component': alert.component,\n                'message': alert.message,\n                'severity': alert.severity.value\n            })\n        \n        return events\n\n    def _analyze_component_correlations(self, context: IncidentContext) -> Dict[str, Any]:\n        \"\"\"Analyze correlations between affected components\"\"\"\n        return {\n            'correlated_failures': {\n                'compute_and_network': 'nova' in context.affected_openstack_components and 'neutron' in context.affected_openstack_components,\n                'storage_and_compute': 'cinder' in context.affected_openstack_components and 'nova' in context.affected_openstack_components,\n                'middleware_chain_failure': len(context.affected_middleware) > 1\n            },\n            'propagation_pattern': self._detect_propagation_pattern(context)\n        }\n\n    def _detect_propagation_pattern(self, context: IncidentContext) -> str:\n        \"\"\"Detect how failure propagates\"\"\"\n        if context.dependency_chain:\n            if context.dependency_chain[0] in ['rabbitmq', 'mysql']:\n                return 'bottom_up_cascade'\n            elif context.dependency_chain[-1] in ['nova', 'neutron']:\n                return 'top_level_failure'\n        return 'complex_pattern'\n\n    def _analyze_middleware_issues(self, context: IncidentContext) -> Dict[str, Any]:\n        \"\"\"Detailed middleware analysis\"\"\"\n        return {\n            'components': context.affected_middleware,\n            'issues': context.middleware_issues,\n            'impact_assessment': {\n                'rabbitmq_down': 'rabbitmq' in context.affected_middleware,\n                'database_down': 'mysql' in context.affected_middleware,\n                'cache_down': 'redis' in context.affected_middleware\n            },\n            'recovery_strategy': self._determine_recovery_strategy(context)\n        }\n\n    def _determine_recovery_strategy(self, context: IncidentContext) -> str:\n        \"\"\"Determine optimal recovery strategy\"\"\"\n        if 'mysql' in context.affected_middleware:\n            return 'database_recovery_priority'\n        elif 'rabbitmq' in context.affected_middleware:\n            return 'message_queue_recovery'\n        else:\n            return 'standard_recovery'\n\n    def _generate_immediate_actions(self, context: IncidentContext,\n                                   root_causes: List[RootCauseCandidate]) -> List[str]:\n        \"\"\"Generate immediate remediation actions\"\"\"\n        actions: List[str] = []\n        \n        if root_causes:\n            primary = root_causes[0]\n            \n            if 'rabbitmq' in primary.component.lower():\n                actions.extend([\n                    \"Check RabbitMQ service: systemctl status rabbitmq-server\",\n                    \"Review RabbitMQ logs for errors\",\n                    \"Check RabbitMQ disk and memory: rabbitmqctl status\"\n                ])\n            elif 'mysql' in primary.component.lower():\n                actions.extend([\n                    \"Check MySQL service: systemctl status mysql\",\n                    \"Monitor MySQL connections: mysql -e 'SHOW PROCESSLIST'\",\n                    \"Check database locks\"\n                ])\n            elif 'nova' in primary.component.lower():\n                actions.extend([\n                    \"Check Nova API service: systemctl status openstack-nova-api\",\n                    \"Restart Nova services on affected nodes\",\n                    \"Verify hypervisor connectivity\"\n                ])\n        \n        actions.append(\"Escalate to senior administrator\")\n        return actions\n\n    def _generate_short_term_fixes(self, context: IncidentContext,\n                                  root_causes: List[RootCauseCandidate]) -> List[str]:\n        \"\"\"Generate short-term fixes\"\"\"\n        return [\n            \"Restart affected services\",\n            \"Clear message queues if necessary\",\n            \"Verify service connectivity\",\n            \"Monitor for service stabilization\"\n        ]\n\n    def _generate_long_term_preventions(self, context: IncidentContext,\n                                        root_causes: List[RootCauseCandidate]) -> List[str]:\n        \"\"\"Generate long-term prevention measures\"\"\"\n        return [\n            \"Implement enhanced monitoring for middleware components\",\n            \"Set up automatic failover for critical services\",\n            \"Conduct post-incident review\",\n            \"Update runbooks and documentation\",\n            \"Plan capacity upgrades if needed\"\n        ]\n\n    def get_incident_report(self, incident_id: str) -> Optional[Dict[str, Any]]:\n        \"\"\"Retrieve stored incident report\"\"\"\n        if incident_id in self.incident_history:\n            context = self.incident_history[incident_id]\n            return context.to_dict()\n        return None\n\n    def get_active_incidents(self) -> List[str]:\n        \"\"\"Get list of active incidents\"\"\"\n        return list(self.incident_history.keys())\n