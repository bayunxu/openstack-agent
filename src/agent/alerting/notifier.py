"""
Alert Notifier
Handles alert notifications via various channels
"""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
import json

from .rule_engine import Alert, AlertSeverity

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """Supported notification channels"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    LOG = "log"


class AlertNotifier:
    """
    Alert notifier
    Sends alerts through various channels
    """

    def __init__(self):
        """
        Initialize alert notifier
        """
        self.channels: Dict[str, Any] = {}
        self.notification_history: List[Dict[str, Any]] = []

    def configure_channel(self, channel: NotificationChannel, config: Dict[str, Any]):
        """
        Configure a notification channel

        Args:
            channel: Notification channel enum
            config: Channel configuration
        """
        self.channels[channel.value] = config
        logger.info(f"Configured notification channel: {channel.value}")

    def send_alert(self, alert: Alert, channels: Optional[List[NotificationChannel]] = None):
        """
        Send alert through configured channels

        Args:
            alert: Alert to send
            channels: List of channels to use (default: all configured)
        """
        if not channels:
            channels = [NotificationChannel(c) for c in self.channels.keys()]

        for channel in channels:
            try:
                if channel == NotificationChannel.LOG:
                    self._send_log_notification(alert)
                elif channel == NotificationChannel.EMAIL:
                    self._send_email_notification(alert)
                elif channel == NotificationChannel.SLACK:
                    self._send_slack_notification(alert)
                elif channel == NotificationChannel.WEBHOOK:
                    self._send_webhook_notification(alert)

                # Record notification
                self.notification_history.append({
                    'alert_id': alert.id,
                    'channel': channel.value,
                    'timestamp': datetime.utcnow().isoformat(),
                    'status': 'sent'
                })
            except Exception as e:
                logger.error(f"Error sending alert via {channel.value}: {str(e)}")
                self.notification_history.append({
                    'alert_id': alert.id,
                    'channel': channel.value,
                    'timestamp': datetime.utcnow().isoformat(),
                    'status': 'failed',
                    'error': str(e)
                })

    def _send_log_notification(self, alert: Alert):
        """Send alert via logging"""
        level = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.CRITICAL: logging.CRITICAL,
            AlertSeverity.EMERGENCY: logging.CRITICAL
        }.get(alert.severity, logging.WARNING)

        logger.log(level, f"ALERT [{alert.severity.value.upper()}]: {alert.message}")

    def _send_email_notification(self, alert: Alert):
        """Send alert via email"""
        config = self.channels.get('email', {})
        if not config:
            logger.warning("Email channel not configured")
            return

        # TODO: Implement email sending
        logger.info(f"Would send email alert: {alert.id} to {config.get('recipients', [])}")

    def _send_slack_notification(self, alert: Alert):
        """Send alert via Slack"""
        config = self.channels.get('slack', {})
        if not config:
            logger.warning("Slack channel not configured")
            return

        # TODO: Implement Slack notification
        webhook_url = config.get('webhook_url')
        logger.info(f"Would send Slack alert: {alert.id} to {webhook_url}")

    def _send_webhook_notification(self, alert: Alert):
        """Send alert via webhook"""
        config = self.channels.get('webhook', {})
        if not config:
            logger.warning("Webhook channel not configured")
            return

        # TODO: Implement webhook notification
        webhook_url = config.get('url')
        logger.info(f"Would send webhook alert: {alert.id} to {webhook_url}")

    def get_notification_history(self, alert_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get notification history

        Args:
            alert_id: Optional alert ID to filter by

        Returns:
            List of notification records
        """
        if alert_id:
            return [n for n in self.notification_history if n['alert_id'] == alert_id]
        return self.notification_history
