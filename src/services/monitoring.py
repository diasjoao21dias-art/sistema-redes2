"""Enhanced monitoring service with multiple check types"""

import asyncio
import subprocess
import socket
import ssl
import time
import requests
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from ..models.base import SessionLocal
from ..models.host import Host, HostHistory, HostStatus, CheckType
import logging

logger = logging.getLogger(__name__)

class MonitoringService:
    """Professional monitoring service with multiple check types"""
    
    def __init__(self, max_workers: int = 64):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Performance stats
        self.stats = {
            'total_checks': 0,
            'successful_checks': 0,
            'failed_checks': 0,
            'avg_response_time': 0.0,
            'last_scan_duration': 0.0
        }
    
    def ping_icmp(self, target: str, timeout: int = 5) -> Tuple[bool, Optional[float]]:
        """ICMP ping with latency measurement"""
        try:
            import platform
            system = platform.system().lower()
            
            if system == "windows":
                cmd = f"ping -n 1 -w {timeout*1000} {target}"
                latency_pattern = r"time[<=](\d+)ms"
            else:
                cmd = f"ping -c 1 -W {timeout} {target}"
                latency_pattern = r"time=([0-9.]+) ms"
            
            start_time = time.time()
            result = subprocess.run(
                cmd.split(), 
                capture_output=True, 
                text=True, 
                timeout=timeout + 2
            )
            
            if result.returncode == 0:
                # Extract latency from output
                import re
                match = re.search(latency_pattern, result.stdout)
                if match:
                    latency = float(match.group(1))
                else:
                    # Fallback to measured time
                    latency = (time.time() - start_time) * 1000
                
                return True, latency
            
            return False, None
            
        except Exception as e:
            logger.debug(f"ICMP ping failed for {target}: {e}")
            return False, None
    
    def ping_tcp(self, host: str, port: int, timeout: int = 5) -> Tuple[bool, Optional[float]]:
        """TCP port check with latency measurement"""
        try:
            start_time = time.time()
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            result = sock.connect_ex((host, port))
            latency = (time.time() - start_time) * 1000
            
            sock.close()
            
            if result == 0:
                return True, latency
            return False, None
            
        except Exception as e:
            logger.debug(f"TCP ping failed for {host}:{port}: {e}")
            return False, None
    
    def ping_http(self, url: str, timeout: int = 10) -> Tuple[bool, Optional[float], Optional[str]]:
        """HTTP/HTTPS check with response time and status"""
        try:
            start_time = time.time()
            
            response = requests.get(
                url, 
                timeout=timeout,
                verify=False,  # Skip SSL verification for internal networks
                allow_redirects=True
            )
            
            latency = (time.time() - start_time) * 1000
            
            # Consider 2xx and 3xx as success
            if response.status_code < 400:
                return True, latency, f"HTTP {response.status_code}"
            else:
                return False, latency, f"HTTP {response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, None, "HTTP Timeout"
        except requests.exceptions.ConnectionError:
            return False, None, "Connection Error"
        except Exception as e:
            return False, None, f"HTTP Error: {str(e)}"
    
    def check_ssl_certificate(self, hostname: str, port: int = 443, timeout: int = 10) -> Tuple[bool, Optional[dict]]:
        """Check SSL certificate validity and expiration"""
        try:
            context = ssl.create_default_context()
            
            with socket.create_connection((hostname, port), timeout=timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    
                    # Check if certificate is valid
                    not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                    days_until_expiry = (not_after - datetime.now()).days
                    
                    cert_info = {
                        'subject': dict(x[0] for x in cert['subject']),
                        'issuer': dict(x[0] for x in cert['issuer']),
                        'expires': cert['notAfter'],
                        'days_until_expiry': days_until_expiry,
                        'is_valid': days_until_expiry > 0
                    }
                    
                    return True, cert_info
                    
        except Exception as e:
            logger.debug(f"SSL check failed for {hostname}:{port}: {e}")
            return False, None
    
    def resolve_hostname(self, hostname: str, timeout: int = 5) -> Tuple[Optional[str], Optional[str]]:
        """DNS resolution with error handling"""
        try:
            import socket
            socket.setdefaulttimeout(timeout)
            ip = socket.gethostbyname(hostname)
            return ip, None
        except socket.gaierror as e:
            return None, f"DNS resolution failed: {e}"
        except Exception as e:
            return None, f"DNS error: {e}"
    
    def check_host_comprehensive(self, host: Host) -> Dict:
        """Comprehensive host check with multiple methods"""
        results = {
            'hostname': host.hostname,
            'timestamp': datetime.now(timezone.utc),
            'overall_status': HostStatus.UNKNOWN,
            'checks': {},
            'primary_ip': None,
            'response_time': None,
            'error_message': None
        }
        
        # Skip if in maintenance
        if host.in_maintenance:
            if host.maintenance_until and datetime.now(timezone.utc) > host.maintenance_until:
                # End maintenance window
                with SessionLocal() as db:
                    db_host = db.query(Host).filter(Host.hostname == host.hostname).first()
                    if db_host:
                        db_host.in_maintenance = False
                        db_host.maintenance_until = None
                        db.commit()
            else:
                results['overall_status'] = HostStatus.MAINTENANCE
                return results
        
        # DNS resolution
        resolved_ip, dns_error = self.resolve_hostname(host.hostname)
        if resolved_ip:
            results['primary_ip'] = resolved_ip
            results['checks']['dns'] = {'success': True, 'ip': resolved_ip}
        else:
            results['checks']['dns'] = {'success': False, 'error': dns_error}
            # Use fallback IP if available
            if host.fallback_ip:
                results['primary_ip'] = host.fallback_ip
                results['checks']['dns']['fallback_used'] = True
        
        target_ip = results['primary_ip']
        if not target_ip:
            results['overall_status'] = HostStatus.OFFLINE
            results['error_message'] = "No IP address available"
            return results
        
        # Parse check types
        check_types = [ct.strip().lower() for ct in (host.check_types or "icmp,tcp").split(',')]
        any_success = False
        best_latency = None
        
        # ICMP Check
        if 'icmp' in check_types:
            icmp_success, icmp_latency = self.ping_icmp(target_ip, host.timeout)
            results['checks']['icmp'] = {
                'success': icmp_success,
                'latency_ms': icmp_latency,
                'target': target_ip
            }
            
            if icmp_success:
                any_success = True
                if best_latency is None or (icmp_latency and icmp_latency < best_latency):
                    best_latency = icmp_latency
        
        # TCP Port Checks
        if 'tcp' in check_types and host.tcp_ports:
            tcp_ports = [int(p.strip()) for p in host.tcp_ports.split(',') if p.strip().isdigit()]
            tcp_results = []
            
            for port in tcp_ports:
                tcp_success, tcp_latency = self.ping_tcp(target_ip, port, host.timeout)
                tcp_results.append({
                    'port': port,
                    'success': tcp_success,
                    'latency_ms': tcp_latency
                })
                
                if tcp_success:
                    any_success = True
                    if best_latency is None or (tcp_latency and tcp_latency < best_latency):
                        best_latency = tcp_latency
            
            results['checks']['tcp'] = tcp_results
        
        # HTTP/HTTPS Checks
        if 'http' in check_types:
            http_url = f"http://{target_ip}"
            http_success, http_latency, http_status = self.ping_http(http_url, host.timeout)
            results['checks']['http'] = {
                'success': http_success,
                'latency_ms': http_latency,
                'status': http_status,
                'url': http_url
            }
            
            if http_success:
                any_success = True
                if best_latency is None or (http_latency and http_latency < best_latency):
                    best_latency = http_latency
        
        if 'https' in check_types:
            https_url = f"https://{target_ip}"
            https_success, https_latency, https_status = self.ping_http(https_url, host.timeout)
            results['checks']['https'] = {
                'success': https_success,
                'latency_ms': https_latency,
                'status': https_status,
                'url': https_url
            }
            
            # SSL Certificate Check
            ssl_success, ssl_info = self.check_ssl_certificate(target_ip, 443, host.timeout)
            results['checks']['ssl'] = {
                'success': ssl_success,
                'certificate': ssl_info
            }
            
            if https_success:
                any_success = True
                if best_latency is None or (https_latency and https_latency < best_latency):
                    best_latency = https_latency
        
        # Determine overall status
        if any_success:
            results['overall_status'] = HostStatus.ONLINE
            results['response_time'] = best_latency
        else:
            results['overall_status'] = HostStatus.OFFLINE
            
            # Try to determine specific error
            if not results['checks'].get('dns', {}).get('success'):
                results['error_message'] = "DNS resolution failed"
            else:
                results['error_message'] = "All checks failed"
        
        return results
    
    def save_check_result(self, result: Dict):
        """Save check result to database"""
        try:
            with SessionLocal() as db:
                # Update host current status
                host = db.query(Host).filter(Host.hostname == result['hostname']).first()
                if host and result.get('primary_ip'):
                    # Update IP address if resolved
                    if result['primary_ip'] != host.ip_address:
                        host.ip_address = result['primary_ip']
                
                # Save to history
                history_entry = HostHistory(
                    hostname=result['hostname'],
                    status=result['overall_status'],
                    ip=result.get('primary_ip'),
                    latency_ms=result.get('response_time'),
                    timestamp=result['timestamp'],
                    reason=result.get('error_message'),
                    check_type=CheckType.ICMP  # Default, could be more specific
                )
                
                db.add(history_entry)
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to save check result for {result['hostname']}: {e}")
    
    def get_monitoring_stats(self) -> Dict:
        """Get current monitoring statistics"""
        return self.stats.copy()
    
    def update_stats(self, successful: bool, response_time: float = None):
        """Update monitoring statistics"""
        self.stats['total_checks'] += 1
        
        if successful:
            self.stats['successful_checks'] += 1
        else:
            self.stats['failed_checks'] += 1
        
        if response_time is not None:
            # Update running average
            total_successful = self.stats['successful_checks']
            current_avg = self.stats['avg_response_time']
            self.stats['avg_response_time'] = (
                (current_avg * (total_successful - 1) + response_time) / total_successful
            )