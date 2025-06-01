"""
Connector module for K8s cluster connections.
Provides a unified interface for connecting to K8s clusters using kubectl.
"""

import os
import logging
from typing import Optional, Dict, Any, Union
from .kubectl import KubectlConnector

logger = logging.getLogger(__name__)

class ClusterConnector:
    """
    ClusterConnector provides a unified interface for connecting to Kubernetes clusters
    using kubectl CLI tool.
    """
    
    def __init__(
        self, 
        kubeconfig: Optional[str] = None, 
        context: Optional[str] = None,
        namespace: str = "default"
    ):
        """
        Initialize a new ClusterConnector instance.
        
        Args:
            kubeconfig: Path to kubeconfig file. If None, uses default (~/.kube/config)
            context: Kubernetes context to use. If None, uses current context
            namespace: Kubernetes namespace to use
        """
        self.kubeconfig = kubeconfig or os.path.expanduser("~/.kube/config")
        self.context = context
        self.namespace = namespace
        self._connector = None
        self.connected = False
    
    def connect(self) -> bool:
        """
        Connect to the Kubernetes cluster using kubectl.
        
        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            # Initialize the kubectl connector
            self._connector = KubectlConnector(
                kubeconfig=self.kubeconfig,
                context=self.context,
                namespace=self.namespace
            )
            
            # Attempt to connect and return the result
            self.connected = self._connector.connect()
            if self.connected:
                logger.info("Successfully connected to Kubernetes cluster using kubectl")
            else:
                logger.error("Failed to connect to cluster using kubectl")
            
            return self.connected
            
        except Exception as e:
            logger.error(f"Error connecting to cluster using kubectl: {e}")
            return False
    
    def get_api_version(self) -> str:
        """Get Kubernetes server API version"""
        self._ensure_connected()
        return self._connector.get_api_version()
    
    def get_namespaces(self) -> list:
        """Get list of available namespaces"""
        self._ensure_connected()
        return self._connector.get_namespaces()
    
    def get_current_context(self) -> str:
        """Get current Kubernetes context name"""
        self._ensure_connected()
        return self._connector.get_current_context()
    
    def run_command(self, command: Union[str, list], **kwargs) -> Dict[str, Any]:
        """
        Run a Kubernetes command using kubectl
        
        Args:
            command: Command to run
            **kwargs: Additional arguments to pass to the connector
            
        Returns:
            Dict containing command output and status
        """
        self._ensure_connected()
        return self._connector.run_command(command, **kwargs)
    
    def _ensure_connected(self):
        """Ensure connector is initialized and connected"""
        if not self._connector or not self.connected:
            self.connected = self.connect()
            if not self.connected:
                raise RuntimeError("Not connected to Kubernetes cluster using kubectl")