"""
Health Check Module
Provides comprehensive health checking for OpenStack components
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

from .openstack_connector import OpenStackConnector

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    ERROR = "error"


class ComponentHealth:
    """Represents health status of a component"""

    def __init__(self, name: str, status: HealthStatus, total: int = 0, healthy: int = 0, unhealthy: int = 0):
        self.name = name
        self.status = status
        self.total = total
        self.healthy = healthy
        self.unhealthy = unhealthy
        self.details: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'status': self.status.value,
            'total': self.total,
            'healthy': self.healthy,
            'unhealthy': self.unhealthy,
            'health_percentage': round((self.healthy / self.total * 100) if self.total > 0 else 0, 2),
            'details': self.details
        }


class HealthChecker:
    """
    Health checking service for OpenStack cluster
    """

    def __init__(self, connector: OpenStackConnector):
        """
        Initialize health checker

        Args:
            connector: OpenStackConnector instance
        """
        self.connector = connector

    def check_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check

        Returns:
            Health status report
        """
        try:
            report = {
                'timestamp': datetime.utcnow().isoformat(),
                'overall_status': HealthStatus.HEALTHY.value,
                'components': {}
            }

            # Check each component
            components_health = [
                self._check_compute_health(),
                self._check_network_health(),
                self._check_hypervisor_health(),
                self._check_services_health()
            ]

            for component in components_health:
                report['components'][component.name] = component.to_dict()

            # Determine overall status
            statuses = [c.status for c in components_health]
            if any(s == HealthStatus.CRITICAL for s in statuses):
                report['overall_status'] = HealthStatus.CRITICAL.value
            elif any(s == HealthStatus.DEGRADED for s in statuses):
                report['overall_status'] = HealthStatus.DEGRADED.value
            elif any(s == HealthStatus.ERROR for s in statuses):
                report['overall_status'] = HealthStatus.ERROR.value

            logger.info(f"Health check completed: {report['overall_status']}")
            return report
        except Exception as e:
            logger.error(f"Error during health check: {str(e)}")
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'overall_status': HealthStatus.ERROR.value,
                'error': str(e)
            }

    def _check_compute_health(self) -> ComponentHealth:
        """Check Nova (Compute) service health"""
        try:
            services = self.connector.get_compute_services()
            up_count = sum(1 for s in services if s['status'] == 'up')

            component = ComponentHealth(
                name='compute',
                status=self._determine_status(up_count, len(services)),
                total=len(services),
                healthy=up_count,
                unhealthy=len(services) - up_count
            )

            component.details = {
                'services': [{
                    'host': s['host'],
                    'service': s['service'],
                    'status': s['status'],
                    'state': s['state']
                } for s in services]
            }

            return component
        except Exception as e:
            logger.error(f"Error checking compute health: {str(e)}")
            return ComponentHealth('compute', HealthStatus.ERROR)

    def _check_network_health(self) -> ComponentHealth:
        """Check Neutron (Network) agent health"""
        try:
            agents = self.connector.get_network_agents()
            alive_count = sum(1 for a in agents if a['is_alive'])

            component = ComponentHealth(
                name='network',
                status=self._determine_status(alive_count, len(agents)),
                total=len(agents),
                healthy=alive_count,
                unhealthy=len(agents) - alive_count
            )

            component.details = {
                'agents': [{
                    'host': a['host'],
                    'agent_type': a['agent_type'],
                    'is_alive': a['is_alive'],
                    'admin_state_up': a['is_admin_state_up']
                } for a in agents]
            }

            return component
        except Exception as e:
            logger.error(f"Error checking network health: {str(e)}")
            return ComponentHealth('network', HealthStatus.ERROR)

    def _check_hypervisor_health(self) -> ComponentHealth:
        """Check hypervisor health"""
        try:
            hypervisors = self.connector.get_hypervisors()
            up_count = sum(1 for h in hypervisors if h['state'] == 'up')

            component = ComponentHealth(
                name='hypervisors',
                status=self._determine_status(up_count, len(hypervisors)),
                total=len(hypervisors),
                healthy=up_count,
                unhealthy=len(hypervisors) - up_count
            )

            component.details = {
                'hypervisors': [{
                    'hostname': h['hypervisor_hostname'],
                    'type': h['hypervisor_type'],
                    'state': h['state'],
                    'status': h['status'],
                    'vcpus_available': h['vcpus'] - h['vcpus_used'],
                    'memory_available_mb': h['memory_mb'] - h['memory_mb_used'],
                    'running_vms': h['running_vms']
                } for h in hypervisors]
            }

            return component
        except Exception as e:
            logger.error(f"Error checking hypervisor health: {str(e)}")
            return ComponentHealth('hypervisors', HealthStatus.ERROR)

    def _check_services_health(self) -> ComponentHealth:
        """Check service endpoints health"""
        try:
            services = self.connector.get_services()
            enabled_count = sum(1 for s in services if s['enabled'])

            component = ComponentHealth(
                name='services',
                status=self._determine_status(enabled_count, len(services)),
                total=len(services),
                healthy=enabled_count,
                unhealthy=len(services) - enabled_count
            )

            component.details = {
                'services': [{
                    'name': s['name'],
                    'type': s['type'],
                    'enabled': s['enabled']
                } for s in services]
            }

            return component
        except Exception as e:
            logger.error(f"Error checking services health: {str(e)}")
            return ComponentHealth('services', HealthStatus.ERROR)

    @staticmethod
    def _determine_status(healthy: int, total: int) -> HealthStatus:
        """
        Determine component status based on health ratio

        Args:
            healthy: Number of healthy items
            total: Total number of items

        Returns:
            HealthStatus enumeration
        """
        if total == 0:
            return HealthStatus.ERROR

        health_ratio = healthy / total

        if health_ratio >= 0.95:
            return HealthStatus.HEALTHY
        elif health_ratio >= 0.75:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.CRITICAL
