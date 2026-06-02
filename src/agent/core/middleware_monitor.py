"""
Middleware Monitoring Module
Monitors OpenStack Pike middleware components (RabbitMQ, MySQL, Redis, etc.)
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import socket
import subprocess
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class MiddlewareHealthStatus:
    """Health status of middleware component"""

    def __init__(self, name: str, is_healthy: bool, metrics: Dict[str, Any]):
        self.name = name
        self.is_healthy = is_healthy
        self.metrics = metrics
        self.timestamp = datetime.utcnow()
        self.issues: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'is_healthy': self.is_healthy,
            'timestamp': self.timestamp.isoformat(),
            'metrics': self.metrics,
            'issues': self.issues
        }


class MiddlewareChecker(ABC):
    """Abstract base class for middleware health checkers"""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    @abstractmethod
    def check_health(self) -> MiddlewareHealthStatus:
        """Check middleware health"""
        pass

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get middleware metrics"""
        pass

    def _is_port_open(self) -> bool:
        """Check if port is accessible"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            return result == 0
        except Exception as e:
            logger.error(f"Error checking port {self.port}: {str(e)}")
            return False

    def _run_command(self, command: str) -> Tuple[bool, str]:
        """Run shell command and return success status and output"""
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=5)
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timeout"
        except Exception as e:
            return False, str(e)


class RabbitMQChecker(MiddlewareChecker):
    """RabbitMQ health checker"""

    def check_health(self) -> MiddlewareHealthStatus:
        """Check RabbitMQ health"""
        metrics = self.get_metrics()
        is_healthy = self._is_port_open() and metrics.get('status') == 'running'

        status = MiddlewareHealthStatus('rabbitmq', is_healthy, metrics)

        if not self._is_port_open():
            status.issues.append(f"Cannot connect to RabbitMQ on {self.host}:{self.port}")
        if metrics.get('disk_alarm'):
            status.issues.append("RabbitMQ disk alarm triggered")
        if metrics.get('memory_alarm'):
            status.issues.append("RabbitMQ memory alarm triggered")
        if metrics.get('queue_backlog', 0) > 10000:
            status.issues.append(f"High queue backlog: {metrics['queue_backlog']}")

        return status

    def get_metrics(self) -> Dict[str, Any]:
        """Get RabbitMQ metrics"""
        metrics: Dict[str, Any] = {
            'status': 'unknown',
            'connections': 0,
            'channels': 0,
            'queues': 0,
            'messages': 0,
            'disk_alarm': False,
            'memory_alarm': False,
            'queue_backlog': 0
        }

        try:
            # Check if RabbitMQ is running
            success, _ = self._run_command("rabbitmqctl status")
            if success:
                metrics['status'] = 'running'

                # Try to get more detailed metrics
                success, output = self._run_command("rabbitmqctl list_connections | wc -l")
                if success:
                    metrics['connections'] = int(output.strip() or 0)

                success, output = self._run_command("rabbitmqctl list_queues | wc -l")
                if success:
                    metrics['queues'] = int(output.strip() or 0)
            else:
                metrics['status'] = 'stopped'
        except Exception as e:
            logger.error(f"Error getting RabbitMQ metrics: {str(e)}")
            metrics['status'] = 'error'

        return metrics


class MySQLChecker(MiddlewareChecker):
    """MySQL health checker"""

    def __init__(self, host: str, port: int, user: str = 'root', password: str = ''):
        super().__init__(host, port)
        self.user = user
        self.password = password

    def check_health(self) -> MiddlewareHealthStatus:
        """Check MySQL health"""
        metrics = self.get_metrics()
        is_healthy = self._is_port_open() and metrics.get('status') == 'running'

        status = MiddlewareHealthStatus('mysql', is_healthy, metrics)

        if not self._is_port_open():
            status.issues.append(f"Cannot connect to MySQL on {self.host}:{self.port}")
        if metrics.get('threads_connected', 0) > 100:
            status.issues.append(f"High connection count: {metrics['threads_connected']}")
        if metrics.get('questions_rate', 0) > 5000:
            status.issues.append(f"High query rate: {metrics['questions_rate']}/sec")
        if metrics.get('slow_queries', 0) > 100:
            status.issues.append(f"Many slow queries: {metrics['slow_queries']}")

        return status

    def get_metrics(self) -> Dict[str, Any]:
        """Get MySQL metrics"""
        metrics: Dict[str, Any] = {
            'status': 'unknown',
            'threads_connected': 0,
            'questions_rate': 0,
            'slow_queries': 0,
            'replication_lag': 0,
            'uptime': 0
        }

        try:
            # Check if MySQL is running
            success, _ = self._run_command(f"mysql -h {self.host} -u {self.user} -e 'SELECT 1' 2>/dev/null")
            if success:
                metrics['status'] = 'running'
                # Get basic metrics
                cmd = f"mysql -h {self.host} -u {self.user} -e 'SHOW STATUS LIKE \"Threads_connected\"' 2>/dev/null"
                success, output = self._run_command(cmd)
                if success and 'Threads_connected' in output:
                    try:
                        value = output.split()[-1]
                        metrics['threads_connected'] = int(value)
                    except:
                        pass
            else:
                metrics['status'] = 'stopped'
        except Exception as e:
            logger.error(f"Error getting MySQL metrics: {str(e)}")
            metrics['status'] = 'error'

        return metrics


class RedisChecker(MiddlewareChecker):
    """Redis health checker"""

    def check_health(self) -> MiddlewareHealthStatus:
        """Check Redis health"""
        metrics = self.get_metrics()
        is_healthy = self._is_port_open() and metrics.get('status') == 'running'

        status = MiddlewareHealthStatus('redis', is_healthy, metrics)

        if not self._is_port_open():
            status.issues.append(f"Cannot connect to Redis on {self.host}:{self.port}")
        if metrics.get('used_memory_percent', 0) > 80:
            status.issues.append(f"High memory usage: {metrics['used_memory_percent']}%")
        if metrics.get('rejected_connections', 0) > 0:
            status.issues.append(f"Rejected connections: {metrics['rejected_connections']}")

        return status

    def get_metrics(self) -> Dict[str, Any]:
        """Get Redis metrics"""
        metrics: Dict[str, Any] = {
            'status': 'unknown',
            'used_memory': 0,
            'used_memory_percent': 0,
            'connected_clients': 0,
            'rejected_connections': 0,
            'instantaneous_ops': 0
        }

        try:
            success, output = self._run_command(f"redis-cli -h {self.host} -p {self.port} info 2>/dev/null")
            if success and output:
                metrics['status'] = 'running'
                # Parse INFO output
                for line in output.split('\n'):
                    if line.startswith('used_memory:'):
                        metrics['used_memory'] = int(line.split(':')[1])
                    elif line.startswith('used_memory_peak:'):
                        peak_memory = int(line.split(':')[1])
                        if peak_memory > 0:
                            metrics['used_memory_percent'] = int(metrics['used_memory'] / peak_memory * 100)
                    elif line.startswith('connected_clients:'):
                        metrics['connected_clients'] = int(line.split(':')[1])
                    elif line.startswith('rejected_connections:'):
                        metrics['rejected_connections'] = int(line.split(':')[1])
            else:
                metrics['status'] = 'stopped'
        except Exception as e:
            logger.error(f"Error getting Redis metrics: {str(e)}")
            metrics['status'] = 'error'

        return metrics


class MiddlewareMonitor:
    """
    Main middleware monitoring service
    """

    def __init__(self):
        """
        Initialize middleware monitor
        """
        self.checkers: Dict[str, MiddlewareChecker] = {}
        self.health_history: Dict[str, List[MiddlewareHealthStatus]] = {}

    def register_checker(self, name: str, checker: MiddlewareChecker):
        """
        Register a middleware checker

        Args:
            name: Middleware name
            checker: MiddlewareChecker instance
        """
        self.checkers[name] = checker
        self.health_history[name] = []
        logger.info(f"Registered middleware checker: {name}")

    def check_all_middleware(self) -> Dict[str, MiddlewareHealthStatus]:
        """
        Check all registered middleware components

        Returns:
            Dictionary of middleware health statuses
        """
        results: Dict[str, MiddlewareHealthStatus] = {}

        for name, checker in self.checkers.items():
            try:
                status = checker.check_health()
                results[name] = status
                self.health_history[name].append(status)

                # Keep last 100 records
                if len(self.health_history[name]) > 100:
                    self.health_history[name] = self.health_history[name][-100:]

                logger.info(f"{name} health: {status.is_healthy}")
            except Exception as e:
                logger.error(f"Error checking {name} health: {str(e)}")

        return results

    def get_middleware_status_report(self) -> Dict[str, Any]:
        """
        Get comprehensive middleware status report

        Returns:
            Status report dictionary
        """
        statuses = self.check_all_middleware()
        healthy_count = sum(1 for s in statuses.values() if s.is_healthy)

        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_middleware': len(statuses),
            'healthy': healthy_count,
            'unhealthy': len(statuses) - healthy_count,
            'health_percentage': round((healthy_count / len(statuses) * 100) if statuses else 0, 2),
            'components': {name: status.to_dict() for name, status in statuses.items()}
        }

        return report

    def get_critical_issues(self) -> List[Dict[str, Any]]:
        """
        Get all critical middleware issues

        Returns:
            List of critical issues
        """
        issues: List[Dict[str, Any]] = []
        statuses = self.check_all_middleware()

        for name, status in statuses.items():
            if not status.is_healthy:
                issues.append({
                    'component': name,
                    'severity': 'critical',
                    'timestamp': status.timestamp.isoformat(),
                    'issues': status.issues
                })

        return issues
