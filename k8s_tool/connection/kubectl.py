"""
KubectlConnector module for K8s connections using kubectl CLI.
Provides functionality to interact with K8s clusters using kubectl commands.
"""

import os
import json
import logging
import subprocess
from typing import Optional, Dict, Any, Union, List
import yaml

logger = logging.getLogger(__name__)

class KubectlConnector:
    """
    KubectlConnector provides functionality to interact with Kubernetes clusters
    using kubectl CLI commands through subprocess.
    """
    
    def __init__(
        self, 
        kubeconfig: Optional[str] = None, 
        context: Optional[str] = None,
        namespace: str = "default"
    ):
        """
        Initialize a new KubectlConnector instance.
        
        Args:
            kubeconfig: Path to kubeconfig file. If None, uses default (~/.kube/config)
            context: Kubernetes context to use. If None, uses current context
            namespace: Kubernetes namespace to use
        """
        self.kubeconfig = kubeconfig or os.path.expanduser("~/.kube/config")
        self.context = context
        self.namespace = namespace
        self.connected = False
    
    def connect(self) -> bool:
        """
        Verify connection to the Kubernetes cluster.
        
        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            # Check if kubectl is installed
            version_cmd = ["kubectl", "version", "--client", "--output=json"]
            self._execute_command(version_cmd)
            
            # Prepare base kubectl command with config and context
            base_cmd = ["kubectl"]
            
            if self.kubeconfig:
                base_cmd.extend(["--kubeconfig", self.kubeconfig])
            
            if self.context:
                base_cmd.extend(["--context", self.context])
            
            # Test connection by getting API version
            base_cmd.extend(["version", "--output=json"])
            result = self._execute_command(base_cmd)
            
            if result["success"]:
                self.connected = True
                logger.info("Successfully connected to Kubernetes cluster using kubectl")
                return True
            else:
                logger.error(f"Failed to connect to cluster: {result['error']}")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to cluster: {e}")
            return False
    
    def get_api_version(self) -> str:
        """
        Get Kubernetes server API version.
        
        Returns:
            str: Server API version
        """
        cmd = self._build_base_command()
        cmd.extend(["version", "--output=json"])
        
        result = self._execute_command(cmd)
        if not result["success"]:
            raise RuntimeError(f"Failed to get API version: {result['error']}")
        
        try:
            version_info = json.loads(result["output"])
            server_version = version_info.get("serverVersion", {})
            return f"{server_version.get('major', '')}.{server_version.get('minor', '')}"
        except Exception as e:
            logger.error(f"Error parsing API version: {e}")
            return "Unknown"
    
    def get_namespaces(self) -> List[str]:
        """
        Get list of available namespaces.
        
        Returns:
            List[str]: List of namespace names
        """
        cmd = self._build_base_command()
        cmd.extend(["get", "namespaces", "-o", "json"])
        
        result = self._execute_command(cmd)
        if not result["success"]:
            raise RuntimeError(f"Failed to get namespaces: {result['error']}")
        
        try:
            namespaces_info = json.loads(result["output"])
            return [item["metadata"]["name"] for item in namespaces_info.get("items", [])]
        except Exception as e:
            logger.error(f"Error parsing namespaces: {e}")
            return []
    
    def get_current_context(self) -> str:
        """
        Get current Kubernetes context name.
        
        Returns:
            str: Current context name
        """
        cmd = self._build_base_command()
        cmd.extend(["config", "current-context"])
        
        result = self._execute_command(cmd)
        if not result["success"]:
            raise RuntimeError(f"Failed to get current context: {result['error']}")
        
        return result["output"].strip()
    
    def run_command(self, command: Union[str, List[str]], **kwargs) -> Dict[str, Any]:
        """
        Run a kubectl command.
        
        Args:
            command: Command to run (string or list)
            **kwargs: Additional arguments
                use_namespace: Whether to include namespace in command (default: True)
                manifest_file: Path to a manifest file (to check if namespace is included)
                manifest_data: Dictionary containing manifest data (to check if namespace is included)
            
        Returns:
            Dict containing command output and status
        """
        if isinstance(command, str):
            command = command.split()
        
        # Map custom resource types
        if command and command[0] == 'get':
            if len(command) > 1 and command[1] == 'scaledobject':
                command[1] = 'scaledobject.keda.sh'
            if len(command) > 1 and command[1] == 'scaledobjects':
                command[1] = 'scaledobjects.keda.sh'
            # hpa is supported as-is
        
        # Check if namespace is already specified in deployment manifest
        use_namespace = kwargs.get('use_namespace', True)
        manifest_file = kwargs.get('manifest_file')
        manifest_data = kwargs.get('manifest_data')
        
        # Check if we need to extract namespace from manifest
        if use_namespace and (manifest_file or manifest_data):
            # Check if the manifest already contains namespace information
            namespace_in_manifest = self._has_namespace_in_manifest(manifest_file, manifest_data)
            if namespace_in_manifest:
                # If namespace is in manifest, don't add the namespace flag
                use_namespace = False
                logger.debug("Namespace found in manifest. Not adding namespace flag to command.")
        
        if use_namespace:
            cmd = self._build_base_command()
            cmd.extend(command)
        else:
            # Build command without namespace
            cmd = ["kubectl"]
            
            if self.kubeconfig:
                cmd.extend(["--kubeconfig", self.kubeconfig])
            
            if self.context:
                cmd.extend(["--context", self.context])
                
            cmd.extend(command)
        
        return self._execute_command(cmd)
    
    def _has_namespace_in_manifest(self, manifest_file=None, manifest_data=None) -> bool:
        """
        Check if a Kubernetes manifest contains namespace information.
        
        Args:
            manifest_file: Path to manifest file
            manifest_data: Dictionary with manifest data
            
        Returns:
            bool: True if namespace is specified in manifest, False otherwise
        """
        try:
            # If manifest_data is provided, use it
            if manifest_data:
                return "namespace" in manifest_data.get("metadata", {})
                
            # Otherwise, try to load from file
            if manifest_file and os.path.exists(manifest_file):
                with open(manifest_file, 'r') as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        return "namespace" in data.get("metadata", {})
                    elif isinstance(data, list):
                        # For YAML files with multiple documents
                        for item in data:
                            if isinstance(item, dict) and "namespace" in item.get("metadata", {}):
                                return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking namespace in manifest: {e}")
            return False
    
    def _build_base_command(self) -> List[str]:
        """
        Build base kubectl command with config, context, and namespace.
        
        Returns:
            List[str]: Base command as list of strings
        """
        cmd = ["kubectl"]
        
        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])
        
        if self.context:
            cmd.extend(["--context", self.context])
            
        if self.namespace:
            cmd.extend(["--namespace", self.namespace])
            
        return cmd
    
    def _execute_command(self, cmd: List[str]) -> Dict[str, Any]:
        """
        Execute a command using subprocess.
        
        Args:
            cmd: Command to execute as list of strings
            
        Returns:
            Dict containing:
                success: bool indicating command success
                output: command output if successful
                error: error message if command failed
                returncode: command return code
        """
        logger.debug(f"Executing command: {' '.join(cmd)}")
        
        result = {
            "success": False,
            "output": "",
            "error": "",
            "returncode": -1
        }
        
        try:
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                check=False
            )
            
            result["returncode"] = process.returncode
            
            if process.returncode == 0:
                result["success"] = True
                result["output"] = process.stdout
            else:
                result["error"] = process.stderr
                
            return result
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            result["error"] = str(e)
            return result