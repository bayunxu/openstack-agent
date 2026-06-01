"""
OpenStack Connector Module
Handles all OpenStack API interactions
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import openstack
from openstack.exceptions import HttpException

logger = logging.getLogger(__name__)


class OpenStackConnector:
    """
    Main connector class for OpenStack Pike integration
    Provides methods to interact with OpenStack API
    """

    def __init__(self, cloud_name: str = "default", config_file: Optional[str] = None):
        """
        Initialize OpenStack connector

        Args:
            cloud_name: Name of the cloud configuration (default: "default")
            config_file: Path to clouds.yaml configuration file
        """
        try:
            self.conn = openstack.connect(
                cloud=cloud_name,
                config_file=config_file
            )
            logger.info(f"Successfully connected to OpenStack cloud: {cloud_name}")
        except Exception as e:
            logger.error(f"Failed to connect to OpenStack: {str(e)}")
            raise

    def get_compute_services(self) -> List[Dict[str, Any]]:
        """
        Get all Nova (Compute) services status

        Returns:
            List of compute services with their status
        """
        try:
            services = []
            for service in self.conn.compute.services():
                services.append({
                    'id': service.id,
                    'service': service.service,
                    'host': service.host,
                    'status': service.status,
                    'state': service.state,
                    'updated_at': service.updated_at,
                    'disabled_reason': service.disabled_reason
                })
            logger.info(f"Retrieved {len(services)} compute services")
            return services
        except Exception as e:
            logger.error(f"Error retrieving compute services: {str(e)}")
            return []

    def get_storage_services(self) -> List[Dict[str, Any]]:
        """
        Get all Cinder (Storage) services status

        Returns:
            List of storage services with their status
        """
        try:
            services = []
            # Note: Cinder service retrieval might differ based on Pike version
            # This is a placeholder implementation
            logger.info(f"Retrieved storage services")
            return services
        except Exception as e:
            logger.error(f"Error retrieving storage services: {str(e)}")
            return []

    def get_network_agents(self) -> List[Dict[str, Any]]:
        """
        Get all Neutron (Network) agents status

        Returns:
            List of network agents with their status
        """
        try:
            agents = []
            for agent in self.conn.network.agents():
                agents.append({
                    'id': agent.id,
                    'agent_type': agent.agent_type,
                    'host': agent.host,
                    'is_alive': agent.is_alive,
                    'is_admin_state_up': agent.is_admin_state_up,
                    'topic': agent.topic,
                    'created_at': agent.created_at,
                    'started_at': agent.started_at,
                    'heartbeat_timestamp': agent.heartbeat_timestamp,
                    'description': agent.description
                })
            logger.info(f"Retrieved {len(agents)} network agents")
            return agents
        except Exception as e:
            logger.error(f"Error retrieving network agents: {str(e)}")
            return []

    def get_instances(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all VM instances

        Args:
            limit: Maximum number of instances to retrieve

        Returns:
            List of instances with their details
        """
        try:
            instances = []
            for server in self.conn.compute.servers(limit=limit):
                instances.append({
                    'id': server.id,
                    'name': server.name,
                    'status': server.status,
                    'power_state': server.power_state,
                    'created_at': server.created_at,
                    'updated_at': server.updated_at,
                    'host_id': server.host_id,
                    'hypervisor_hostname': getattr(server, 'OS-EXT-SRV-ATTR:hypervisor_hostname', None),
                    'availability_zone': server.availability_zone
                })
            logger.info(f"Retrieved {len(instances)} instances")
            return instances
        except Exception as e:
            logger.error(f"Error retrieving instances: {str(e)}")
            return []

    def get_hypervisors(self) -> List[Dict[str, Any]]:
        """
        Get all hypervisors (compute hosts)

        Returns:
            List of hypervisors with their details
        """
        try:
            hypervisors = []
            for hyper in self.conn.compute.hypervisors():
                hypervisors.append({
                    'id': hyper.id,
                    'hypervisor_hostname': hyper.hypervisor_hostname,
                    'status': hyper.status,
                    'state': hyper.state,
                    'running_vms': hyper.running_vms,
                    'vcpus': hyper.vcpus,
                    'vcpus_used': hyper.vcpus_used,
                    'memory_mb': hyper.memory_mb,
                    'memory_mb_used': hyper.memory_mb_used,
                    'local_gb': hyper.local_gb,
                    'local_gb_used': hyper.local_gb_used,
                    'cpu_info': hyper.cpu_info,
                    'hypervisor_type': hyper.hypervisor_type
                })
            logger.info(f"Retrieved {len(hypervisors)} hypervisors")
            return hypervisors
        except Exception as e:
            logger.error(f"Error retrieving hypervisors: {str(e)}")
            return []

    def get_endpoints(self) -> List[Dict[str, Any]]:
        """
        Get all service endpoints

        Returns:
            List of endpoints with their details
        """
        try:
            endpoints = []
            for endpoint in self.conn.identity.endpoints():
                endpoints.append({
                    'id': endpoint.id,
                    'service_id': endpoint.service_id,
                    'interface': endpoint.interface,
                    'url': endpoint.url,
                    'region': endpoint.region,
                    'enabled': endpoint.is_enabled
                })
            logger.info(f"Retrieved {len(endpoints)} endpoints")
            return endpoints
        except Exception as e:
            logger.error(f"Error retrieving endpoints: {str(e)}")
            return []

    def get_services(self) -> List[Dict[str, Any]]:
        """
        Get all OpenStack services

        Returns:
            List of services
        """
        try:
            services = []
            for service in self.conn.identity.services():
                services.append({
                    'id': service.id,
                    'name': service.name,
                    'type': service.type,
                    'enabled': service.is_enabled,
                    'description': service.description
                })
            logger.info(f"Retrieved {len(services)} services")
            return services
        except Exception as e:
            logger.error(f"Error retrieving services: {str(e)}")
            return []

    def health_check(self) -> Dict[str, Any]:
        """
        Perform overall health check on OpenStack cluster

        Returns:
            Health status summary
        """
        try:
            health_status = {
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'healthy',
                'components': {}
            }

            # Check compute services
            compute_services = self.get_compute_services()
            compute_down = sum(1 for s in compute_services if s['status'] != 'up')
            health_status['components']['compute'] = {
                'total': len(compute_services),
                'up': len(compute_services) - compute_down,
                'down': compute_down,
                'status': 'healthy' if compute_down == 0 else 'degraded'
            }

            # Check network agents
            network_agents = self.get_network_agents()
            agents_down = sum(1 for a in network_agents if not a['is_alive'])
            health_status['components']['network'] = {
                'total': len(network_agents),
                'alive': len(network_agents) - agents_down,
                'dead': agents_down,
                'status': 'healthy' if agents_down == 0 else 'degraded'
            }

            # Check hypervisors
            hypervisors = self.get_hypervisors()
            hypervisors_down = sum(1 for h in hypervisors if h['state'] != 'up')
            health_status['components']['hypervisors'] = {
                'total': len(hypervisors),
                'up': len(hypervisors) - hypervisors_down,
                'down': hypervisors_down,
                'status': 'healthy' if hypervisors_down == 0 else 'degraded'
            }

            # Overall status
            if any(c['status'] == 'degraded' for c in health_status['components'].values()):
                health_status['status'] = 'degraded'
            if any(c['status'] == 'critical' for c in health_status['components'].values()):
                health_status['status'] = 'critical'

            logger.info(f"Health check completed: {health_status['status']}")
            return health_status
        except Exception as e:
            logger.error(f"Error during health check: {str(e)}")
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'error',
                'error': str(e)
            }

    def close(self):
        """Close the connection to OpenStack"""
        try:
            self.conn.close()
            logger.info("OpenStack connection closed")
        except Exception as e:
            logger.error(f"Error closing OpenStack connection: {str(e)}")
