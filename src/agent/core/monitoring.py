"""
Monitoring Module
Handles continuous monitoring of OpenStack cluster
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from threading import Thread, Event
import json

from .openstack_connector import OpenStackConnector

logger = logging.getLogger(__name__)


class MetricPoint:
    """Represents a single metric data point"""

    def __init__(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None, timestamp: Optional[datetime] = None):
        self.metric_name = metric_name
        self.value = value
        self.tags = tags or {}
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> Dict:
        return {
            'metric_name': self.metric_name,
            'value': self.value,
            'tags': self.tags,
            'timestamp': self.timestamp.isoformat()
        }


class MonitoringService:
    """
    Main monitoring service for OpenStack cluster
    Collects and aggregates metrics from OpenStack components
    """

    def __init__(self, openstack_connector: OpenStackConnector, interval: int = 60):
        """
        Initialize monitoring service

        Args:
            openstack_connector: OpenStackConnector instance
            interval: Collection interval in seconds (default: 60)
        """
        self.connector = openstack_connector
        self.interval = interval
        self.running = False
        self.metrics: List[MetricPoint] = []
        self.stop_event = Event()
        self.monitor_thread: Optional[Thread] = None

    def start(self):
        """Start the monitoring service"""
        if self.running:
            logger.warning("Monitoring service is already running")
            return

        self.running = True
        self.stop_event.clear()
        self.monitor_thread = Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Monitoring service started")

    def stop(self):
        """Stop the monitoring service"""
        if not self.running:
            logger.warning("Monitoring service is not running")
            return

        self.running = False
        self.stop_event.set()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        logger.info("Monitoring service stopped")

    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.running and not self.stop_event.is_set():
            try:
                self._collect_metrics()
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(self.interval)

    def _collect_metrics(self):
        """Collect metrics from OpenStack components"""
        timestamp = datetime.utcnow()

        # Collect compute metrics
        self._collect_compute_metrics(timestamp)

        # Collect network metrics
        self._collect_network_metrics(timestamp)

        # Collect hypervisor metrics
        self._collect_hypervisor_metrics(timestamp)

    def _collect_compute_metrics(self, timestamp: datetime):
        """Collect Nova (Compute) service metrics"""
        try:
            services = self.connector.get_compute_services()
            up_count = sum(1 for s in services if s['status'] == 'up')
            down_count = len(services) - up_count

            self.metrics.append(MetricPoint(
                'openstack.compute.services.total',
                len(services),
                tags={'component': 'nova'},
                timestamp=timestamp
            ))
            self.metrics.append(MetricPoint(
                'openstack.compute.services.up',
                up_count,
                tags={'component': 'nova', 'status': 'up'},
                timestamp=timestamp
            ))
            self.metrics.append(MetricPoint(
                'openstack.compute.services.down',
                down_count,
                tags={'component': 'nova', 'status': 'down'},
                timestamp=timestamp
            ))
            logger.debug(f"Collected compute metrics: {len(services)} services, {up_count} up, {down_count} down")
        except Exception as e:
            logger.error(f"Error collecting compute metrics: {str(e)}")

    def _collect_network_metrics(self, timestamp: datetime):
        """Collect Neutron (Network) agent metrics"""
        try:
            agents = self.connector.get_network_agents()
            alive_count = sum(1 for a in agents if a['is_alive'])
            dead_count = len(agents) - alive_count

            self.metrics.append(MetricPoint(
                'openstack.network.agents.total',
                len(agents),
                tags={'component': 'neutron'},
                timestamp=timestamp
            ))
            self.metrics.append(MetricPoint(
                'openstack.network.agents.alive',
                alive_count,
                tags={'component': 'neutron', 'status': 'alive'},
                timestamp=timestamp
            ))
            self.metrics.append(MetricPoint(
                'openstack.network.agents.dead',
                dead_count,
                tags={'component': 'neutron', 'status': 'dead'},
                timestamp=timestamp
            ))
            logger.debug(f"Collected network metrics: {len(agents)} agents, {alive_count} alive, {dead_count} dead")
        except Exception as e:
            logger.error(f"Error collecting network metrics: {str(e)}")

    def _collect_hypervisor_metrics(self, timestamp: datetime):
        """Collect hypervisor (compute host) metrics"""
        try:
            hypervisors = self.connector.get_hypervisors()

            for hyper in hypervisors:
                tags = {
                    'component': 'hypervisor',
                    'hostname': hyper['hypervisor_hostname'],
                    'type': hyper['hypervisor_type']
                }

                # CPU metrics
                self.metrics.append(MetricPoint(
                    'openstack.hypervisor.vcpu.total',
                    hyper['vcpus'],
                    tags={**tags, 'metric': 'vcpu_total'},
                    timestamp=timestamp
                ))
                self.metrics.append(MetricPoint(
                    'openstack.hypervisor.vcpu.used',
                    hyper['vcpus_used'],
                    tags={**tags, 'metric': 'vcpu_used'},
                    timestamp=timestamp
                ))

                # Memory metrics
                self.metrics.append(MetricPoint(
                    'openstack.hypervisor.memory.total',
                    hyper['memory_mb'],
                    tags={**tags, 'metric': 'memory_total'},
                    timestamp=timestamp
                ))
                self.metrics.append(MetricPoint(
                    'openstack.hypervisor.memory.used',
                    hyper['memory_mb_used'],
                    tags={**tags, 'metric': 'memory_used'},
                    timestamp=timestamp
                ))

                # Storage metrics
                self.metrics.append(MetricPoint(
                    'openstack.hypervisor.disk.total',
                    hyper['local_gb'],
                    tags={**tags, 'metric': 'disk_total'},
                    timestamp=timestamp
                ))
                self.metrics.append(MetricPoint(
                    'openstack.hypervisor.disk.used',
                    hyper['local_gb_used'],
                    tags={**tags, 'metric': 'disk_used'},
                    timestamp=timestamp
                ))

                # VM count
                self.metrics.append(MetricPoint(
                    'openstack.hypervisor.vms.running',
                    hyper['running_vms'],
                    tags={**tags, 'metric': 'vms_running'},
                    timestamp=timestamp
                ))

            logger.debug(f"Collected hypervisor metrics for {len(hypervisors)} hosts")
        except Exception as e:
            logger.error(f"Error collecting hypervisor metrics: {str(e)}")

    def get_metrics(self, count: Optional[int] = None) -> List[Dict]:
        """
        Get collected metrics

        Args:
            count: Number of latest metrics to return (default: all)

        Returns:
            List of metric dictionaries
        """
        if count:
            return [m.to_dict() for m in self.metrics[-count:]]
        return [m.to_dict() for m in self.metrics]

    def clear_metrics(self):
        """Clear collected metrics"""
        self.metrics.clear()
        logger.info("Metrics cleared")

    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get summary of collected metrics

        Returns:
            Summary dictionary
        """
        if not self.metrics:
            return {'total': 0, 'metrics': []}

        metric_names = set(m.metric_name for m in self.metrics)
        return {
            'total': len(self.metrics),
            'unique_metrics': len(metric_names),
            'metrics': list(metric_names),
            'latest_timestamp': self.metrics[-1].timestamp.isoformat() if self.metrics else None
        }
