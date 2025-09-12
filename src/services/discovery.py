"""Network discovery service for automatic host detection"""

import subprocess
import socket
import ipaddress
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

class NetworkDiscoveryService:
    """Automatic network discovery and host detection"""
    
    def __init__(self, max_workers: int = 32):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def discover_network_range(self, network: str, timeout: int = 1) -> List[Dict]:
        """Discover hosts in a network range (e.g., '192.168.1.0/24')"""
        try:
            network_obj = ipaddress.IPv4Network(network, strict=False)
            hosts = []
            
            # Use ThreadPoolExecutor for concurrent scanning
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {}
                
                for ip in network_obj.hosts():
                    ip_str = str(ip)
                    future = executor.submit(self._check_host_alive, ip_str, timeout)
                    futures[future] = ip_str
                
                for future in futures:
                    ip_str = futures[future]
                    try:
                        is_alive = future.result(timeout=timeout + 1)
                        if is_alive:
                            # Try to resolve hostname
                            hostname = self._get_hostname(ip_str)
                            hosts.append({
                                'ip': ip_str,
                                'hostname': hostname,
                                'discovered_at': str(datetime.now())
                            })
                    except:
                        continue
            
            return hosts
            
        except Exception as e:
            logger.error(f"Network discovery failed for {network}: {e}")
            return []
    
    def _check_host_alive(self, ip: str, timeout: int = 1) -> bool:
        """Quick check if host is alive"""
        try:
            # Try ICMP ping first
            result = subprocess.run(
                ["ping", "-c", "1", "-W", str(timeout * 1000), ip],
                capture_output=True,
                timeout=timeout + 1
            )
            if result.returncode == 0:
                return True
            
            # If ping fails, try common TCP ports
            common_ports = [22, 80, 443, 3389, 445]
            for port in common_ports:
                if self._check_tcp_port(ip, port, timeout):
                    return True
            
            return False
            
        except:
            return False
    
    def _check_tcp_port(self, ip: str, port: int, timeout: int = 1) -> bool:
        """Check if TCP port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False
    
    def _get_hostname(self, ip: str) -> Optional[str]:
        """Try to resolve hostname from IP"""
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except:
            return None
    
    def discover_current_network(self) -> List[Dict]:
        """Discover hosts on current network"""
        try:
            # Get current network interface info
            import netifaces
            
            # Get default gateway interface
            gateways = netifaces.gateways()
            default_gateway = gateways.get('default', {}).get(netifaces.AF_INET)
            
            if default_gateway:
                interface = default_gateway[1]
                addresses = netifaces.ifaddresses(interface).get(netifaces.AF_INET, [])
                
                for addr_info in addresses:
                    ip = addr_info.get('addr')
                    netmask = addr_info.get('netmask')
                    
                    if ip and netmask:
                        # Calculate network
                        network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
                        return self.discover_network_range(str(network.network))
            
            # Fallback to common private networks
            common_networks = [
                "192.168.1.0/24",
                "192.168.0.0/24", 
                "10.0.0.0/24"
            ]
            
            for network in common_networks:
                hosts = self.discover_network_range(network)
                if hosts:
                    return hosts
            
            return []
            
        except ImportError:
            logger.warning("netifaces not available, using fallback discovery")
            # Fallback without netifaces
            return self.discover_network_range("192.168.1.0/24")
        except Exception as e:
            logger.error(f"Current network discovery failed: {e}")
            return []
    
    def scan_port_range(self, ip: str, start_port: int = 1, end_port: int = 1024, 
                       timeout: int = 1) -> List[int]:
        """Scan port range on specific host"""
        open_ports = []
        
        with ThreadPoolExecutor(max_workers=min(50, end_port - start_port + 1)) as executor:
            futures = {}
            
            for port in range(start_port, end_port + 1):
                future = executor.submit(self._check_tcp_port, ip, port, timeout)
                futures[future] = port
            
            for future in futures:
                port = futures[future]
                try:
                    if future.result(timeout=timeout + 1):
                        open_ports.append(port)
                except:
                    continue
        
        return sorted(open_ports)
    
    def identify_service_type(self, ip: str, open_ports: List[int]) -> str:
        """Try to identify what type of device/service this is"""
        service_signatures = {
            'Windows PC': [3389, 445, 135],
            'Linux Server': [22, 80, 443],
            'Web Server': [80, 443],
            'Database Server': [3306, 5432, 1433],
            'Router/Switch': [23, 80, 443, 161],
            'Printer': [9100, 631, 515],
            'Network Storage': [21, 22, 80, 139, 445]
        }
        
        best_match = 'Unknown Device'
        max_matches = 0
        
        for service_type, signature_ports in service_signatures.items():
            matches = len(set(signature_ports) & set(open_ports))
            if matches > max_matches:
                max_matches = matches
                best_match = service_type
        
        return best_match