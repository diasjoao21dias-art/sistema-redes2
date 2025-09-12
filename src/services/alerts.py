"""Professional alert management service"""

import json
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
import requests
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from ..models.base import SessionLocal
from ..models.alert import AlertRule, AlertInstance, NotificationChannel, AlertSeverity, AlertStatus, NotificationType
from ..models.host import Host, HostHistory, HostStatus
import logging

logger = logging.getLogger(__name__)

class AlertService:
    """Professional alert management with multiple notification channels"""
    
    def __init__(self):
        self.notification_handlers = {
            NotificationType.EMAIL: self._send_email_notification,
            NotificationType.SLACK: self._send_slack_notification, 
            NotificationType.WEBHOOK: self._send_webhook_notification,
            NotificationType.SMS: self._send_sms_notification
        }
    
    def evaluate_alert_rules(self, hostname: str, current_status: HostStatus, 
                           latency_ms: Optional[float] = None):
        """Evaluate all alert rules for a host status change"""
        with SessionLocal() as db:
            # Get applicable alert rules
            rules = db.query(AlertRule).filter(AlertRule.enabled == True).all()
            
            for rule in rules:
                should_trigger = self._should_trigger_alert(rule, hostname, current_status, latency_ms)
                
                if should_trigger:
                    self._create_alert_instance(db, rule, hostname, current_status, latency_ms)
                else:
                    # Check if we should resolve existing alerts
                    self._check_alert_resolution(db, rule, hostname, current_status)
    
    def _should_trigger_alert(self, rule: AlertRule, hostname: str, 
                            status: HostStatus, latency_ms: Optional[float]) -> bool:
        """Check if alert rule should trigger"""
        # Check targeting
        if not self._matches_target(rule, hostname):
            return False
        
        # Check condition
        if rule.condition_type == "status":
            if rule.condition_operator == "equals":
                return status.value == rule.condition_value
            elif rule.condition_operator == "not_equals":
                return status.value != rule.condition_value
        
        elif rule.condition_type == "latency" and latency_ms is not None:
            try:
                threshold = float(rule.condition_value)
                if rule.condition_operator == "greater_than":
                    return latency_ms > threshold
                elif rule.condition_operator == "less_than":
                    return latency_ms < threshold
            except ValueError:
                return False
        
        return False
    
    def _matches_target(self, rule: AlertRule, hostname: str) -> bool:
        """Check if hostname matches rule targeting"""
        with SessionLocal() as db:
            host = db.query(Host).filter(Host.hostname == hostname).first()
            if not host:
                return False
            
            # Check specific hosts
            if rule.target_hosts:
                try:
                    target_hosts = json.loads(rule.target_hosts)
                    if "*" in target_hosts or hostname in target_hosts:
                        return True
                except:
                    if rule.target_hosts == "*" or hostname in rule.target_hosts:
                        return True
            
            # Check tags
            if rule.target_tags and host.tags:
                try:
                    rule_tags = json.loads(rule.target_tags)
                    host_tags = json.loads(host.tags)
                    if any(tag in host_tags for tag in rule_tags):
                        return True
                except:
                    pass
            
            # Check groups
            if rule.target_groups and host.group_name:
                try:
                    rule_groups = json.loads(rule.target_groups)
                    if host.group_name in rule_groups:
                        return True
                except:
                    if host.group_name in rule.target_groups:
                        return True
            
            # Default to match if no targeting specified
            if not any([rule.target_hosts, rule.target_tags, rule.target_groups]):
                return True
        
        return False
    
    def _create_alert_instance(self, db: Session, rule: AlertRule, hostname: str, 
                              status: HostStatus, latency_ms: Optional[float]):
        """Create new alert instance"""
        # Check for existing active alert
        existing = db.query(AlertInstance).filter(
            and_(
                AlertInstance.rule_id == rule.id,
                AlertInstance.hostname == hostname,
                AlertInstance.status == AlertStatus.ACTIVE
            )
        ).first()
        
        if existing:
            # Update existing alert
            existing.trigger_value = str(latency_ms) if latency_ms else status.value
            existing.notification_count += 1
        else:
            # Create new alert
            title = f"{rule.name} - {hostname}"
            message = self._generate_alert_message(rule, hostname, status, latency_ms)
            
            alert = AlertInstance(
                rule_id=rule.id,
                hostname=hostname,
                status=AlertStatus.ACTIVE,
                severity=rule.severity,
                title=title,
                message=message,
                triggered_at=datetime.now(timezone.utc),
                trigger_value=str(latency_ms) if latency_ms else status.value,
                notification_count=1
            )
            
            db.add(alert)
            db.commit()
            
            # Send notifications
            self._send_alert_notifications(rule, alert)
    
    def _check_alert_resolution(self, db: Session, rule: AlertRule, 
                               hostname: str, status: HostStatus):
        """Check if alert should be resolved"""
        active_alerts = db.query(AlertInstance).filter(
            and_(
                AlertInstance.rule_id == rule.id,
                AlertInstance.hostname == hostname,
                AlertInstance.status == AlertStatus.ACTIVE
            )
        ).all()
        
        for alert in active_alerts:
            # Simple resolution logic - if condition no longer matches
            if not self._should_trigger_alert(rule, hostname, status, None):
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now(timezone.utc)
                
                # Send resolution notification
                self._send_resolution_notification(rule, alert)
        
        db.commit()
    
    def _generate_alert_message(self, rule: AlertRule, hostname: str, 
                               status: HostStatus, latency_ms: Optional[float]) -> str:
        """Generate alert message"""
        message = f"Alert: {rule.name}\n\n"
        message += f"Host: {hostname}\n"
        message += f"Status: {status.value}\n"
        
        if latency_ms:
            message += f"Latency: {latency_ms:.2f}ms\n"
        
        message += f"Severity: {rule.severity.value.upper()}\n"
        message += f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        
        if rule.description:
            message += f"\nDescription: {rule.description}"
        
        return message
    
    def _send_alert_notifications(self, rule: AlertRule, alert: AlertInstance):
        """Send notifications for alert"""
        if not rule.notification_channels:
            return
        
        try:
            channel_ids = json.loads(rule.notification_channels)
        except:
            return
        
        with SessionLocal() as db:
            for channel_id in channel_ids:
                channel = db.query(NotificationChannel).filter(
                    and_(
                        NotificationChannel.id == channel_id,
                        NotificationChannel.enabled == True
                    )
                ).first()
                
                if channel:
                    self._send_notification(channel, alert, is_resolution=False)
    
    def _send_resolution_notification(self, rule: AlertRule, alert: AlertInstance):
        """Send resolution notification"""
        if not rule.notification_channels:
            return
        
        try:
            channel_ids = json.loads(rule.notification_channels)
        except:
            return
        
        with SessionLocal() as db:
            for channel_id in channel_ids:
                channel = db.query(NotificationChannel).filter(
                    NotificationChannel.id == channel_id
                ).first()
                
                if channel:
                    self._send_notification(channel, alert, is_resolution=True)
    
    def _send_notification(self, channel: NotificationChannel, alert: AlertInstance, 
                          is_resolution: bool = False):
        """Send notification through channel"""
        try:
            handler = self.notification_handlers.get(channel.type)
            if handler:
                success = handler(channel, alert, is_resolution)
                
                with SessionLocal() as db:
                    db_channel = db.query(NotificationChannel).filter(
                        NotificationChannel.id == channel.id
                    ).first()
                    
                    if db_channel:
                        if success:
                            db_channel.success_count = (db_channel.success_count or 0) + 1
                        else:
                            db_channel.error_count = (db_channel.error_count or 0) + 1
                        
                        db_channel.last_used = datetime.now(timezone.utc)
                        db.commit()
                        
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    def _send_email_notification(self, channel: NotificationChannel, 
                                alert: AlertInstance, is_resolution: bool) -> bool:
        """Send email notification"""
        try:
            config = channel.config
            if not config:
                return False
            
            smtp_server = config.get('smtp_server', 'localhost')
            smtp_port = config.get('smtp_port', 587)
            username = config.get('username')
            password = config.get('password')
            recipients = config.get('recipients', [])
            
            if not recipients:
                return False
            
            # Create message
            subject = f"[{'RESOLVED' if is_resolution else alert.severity.value.upper()}] {alert.title}"
            
            msg = MIMEMultipart()
            msg['From'] = config.get('from_email', username)
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            
            body = alert.message
            if is_resolution:
                body += f"\n\nAlert resolved at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(smtp_server, smtp_port)
            if config.get('use_tls', True):
                server.starttls()
            if username and password:
                server.login(username, password)
            
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            logger.error(f"Email notification failed: {e}")
            return False
    
    def _send_slack_notification(self, channel: NotificationChannel, 
                                alert: AlertInstance, is_resolution: bool) -> bool:
        """Send Slack notification"""
        try:
            config = channel.config
            webhook_url = config.get('webhook_url')
            
            if not webhook_url:
                return False
            
            color = "good" if is_resolution else {
                AlertSeverity.LOW: "#36a64f",
                AlertSeverity.MEDIUM: "#ff9900", 
                AlertSeverity.HIGH: "#ff0000",
                AlertSeverity.CRITICAL: "#800000"
            }.get(alert.severity, "#ff0000")
            
            payload = {
                "text": f"[{'RESOLVED' if is_resolution else 'ALERT'}] {alert.title}",
                "attachments": [
                    {
                        "color": color,
                        "fields": [
                            {
                                "title": "Host",
                                "value": alert.hostname,
                                "short": True
                            },
                            {
                                "title": "Severity",
                                "value": alert.severity.value.upper(),
                                "short": True
                            },
                            {
                                "title": "Details",
                                "value": alert.message,
                                "short": False
                            }
                        ],
                        "footer": "Sistemas Olivium Network Monitor",
                        "ts": int(alert.triggered_at.timestamp())
                    }
                ]
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Slack notification failed: {e}")
            return False
    
    def _send_webhook_notification(self, channel: NotificationChannel, 
                                  alert: AlertInstance, is_resolution: bool) -> bool:
        """Send webhook notification"""
        try:
            config = channel.config
            url = config.get('url')
            method = config.get('method', 'POST').upper()
            headers = config.get('headers', {})
            
            if not url:
                return False
            
            payload = {
                "event": "alert_resolved" if is_resolution else "alert_triggered",
                "alert": {
                    "id": alert.id,
                    "title": alert.title,
                    "hostname": alert.hostname,
                    "severity": alert.severity.value,
                    "status": alert.status.value,
                    "message": alert.message,
                    "triggered_at": alert.triggered_at.isoformat(),
                    "trigger_value": alert.trigger_value
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            if method == 'POST':
                response = requests.post(url, json=payload, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=payload, headers=headers, timeout=10)
            else:
                return False
            
            return response.status_code < 400
            
        except Exception as e:
            logger.error(f"Webhook notification failed: {e}")
            return False
    
    def _send_sms_notification(self, channel: NotificationChannel, 
                              alert: AlertInstance, is_resolution: bool) -> bool:
        """Send SMS notification (placeholder for SMS service integration)"""
        # This would integrate with SMS services like Twilio, AWS SNS, etc.
        logger.info(f"SMS notification would be sent: {alert.title}")
        return True
    
    def get_active_alerts(self, limit: int = 100) -> List[AlertInstance]:
        """Get active alerts"""
        with SessionLocal() as db:
            return db.query(AlertInstance).filter(
                AlertInstance.status == AlertStatus.ACTIVE
            ).order_by(AlertInstance.triggered_at.desc()).limit(limit).all()
    
    def acknowledge_alert(self, alert_id: int, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        try:
            with SessionLocal() as db:
                alert = db.query(AlertInstance).filter(AlertInstance.id == alert_id).first()
                if alert and alert.status == AlertStatus.ACTIVE:
                    alert.status = AlertStatus.ACKNOWLEDGED
                    alert.acknowledged_at = datetime.now(timezone.utc)
                    alert.acknowledged_by = acknowledged_by
                    db.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
            return False
    
    def create_notification_channel(self, name: str, channel_type: NotificationType, 
                                   config: Dict) -> NotificationChannel:
        """Create notification channel"""
        with SessionLocal() as db:
            channel = NotificationChannel(
                name=name,
                type=channel_type,
                config=config,
                enabled=True
            )
            db.add(channel)
            db.commit()
            return channel