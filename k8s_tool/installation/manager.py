"""
Installation manager for Kubernetes components.
"""

import os
import sys
import logging
import subprocess
import json
import yaml
import tempfile
import platform
import time
from typing import Dict, Any, Optional, Tuple, List

from k8s_tool.connection.connector import ClusterConnector

logger = logging.getLogger(__name__)

class InstallationManager:
    """
    InstallationManager provides functionality to install and verify tools
    in a Kubernetes cluster, including Helm and KEDA.
    """
    
    def __init__(self, connector: ClusterConnector):
        """
        Initialize a new InstallationManager instance.
        
        Args:
            connector: A connected ClusterConnector instance
        """
        self.connector = connector
    
    def install_helm(self, version: str = "latest") -> Dict[str, Any]:
        """
        Install Helm client on the local system and initialize Tiller in the cluster if needed.
        
        Args:
            version: Helm version to install, or 'latest'
            
        Returns:
            Dict containing installation status and details
        """
        result = {
            "success": False,
            "message": "",
            "version": "",
        }
        
        try:
            # Check if Helm is already installed
            helm_installed, helm_version = self._check_helm_installed()
            
            if helm_installed:
                logger.info(f"Helm is already installed: {helm_version}")
                result["success"] = True
                result["message"] = f"Helm is already installed"
                result["version"] = helm_version
                return result
            
            # Install Helm based on OS
            os_type = platform.system().lower()
            
            if os_type == "linux":
                return self._install_helm_linux(version)
            elif os_type == "darwin":
                return self._install_helm_macos(version)
            elif os_type == "windows":
                return self._install_helm_windows(version)
            else:
                result["message"] = f"Unsupported OS: {os_type}"
                return result
            
        except Exception as e:
            logger.error(f"Error installing Helm: {e}")
            result["message"] = f"Error installing Helm: {str(e)}"
            return result
    
    def _check_helm_installed(self) -> Tuple[bool, str]:
        """
        Check if Helm is installed and get its version.
        
        Returns:
            Tuple containing:
                bool indicating if Helm is installed
                str containing Helm version if installed, empty string otherwise
        """
        try:
            process = subprocess.run(
                ["helm", "version", "--client", "--short"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                check=False
            )
            
            if process.returncode == 0:
                version = process.stdout.strip()
                return True, version
            
            return False, ""
            
        except Exception:
            return False, ""
    
    def _install_helm_linux(self, version: str) -> Dict[str, Any]:
        """
        Install Helm on Linux using the script from helm.sh.
        
        Args:
            version: Helm version to install
            
        Returns:
            Dict containing installation status and details
        """
        result = {
            "success": False,
            "message": "",
            "version": "",
        }
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                # Download and run Helm installation script
                script_path = os.path.join(tmp_dir, "get_helm.sh")
                
                # Download script
                subprocess.run(
                    ["curl", "-fsSL", "-o", script_path, "https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3"],
                    check=True
                )
                
                # Set execute permissions
                os.chmod(script_path, 0o755)
                
                # Run installation script
                env = os.environ.copy()
                if version != "latest":
                    env["DESIRED_VERSION"] = f"v{version}"
                
                subprocess.run([script_path], env=env, check=True)
                
                # Verify installation
                helm_installed, helm_version = self._check_helm_installed()
                
                if helm_installed:
                    result["success"] = True
                    result["message"] = "Helm installed successfully"
                    result["version"] = helm_version
                else:
                    result["message"] = "Failed to verify Helm installation"
                
                return result
                
            except subprocess.SubprocessError as e:
                logger.error(f"Error installing Helm: {e}")
                result["message"] = f"Error during installation: {str(e)}"
                return result
            except Exception as e:
                logger.error(f"Error installing Helm: {e}")
                result["message"] = f"Error: {str(e)}"
                return result
    
    def _install_helm_macos(self, version: str) -> Dict[str, Any]:
        """
        Install Helm on macOS using Homebrew or the script.
        
        Args:
            version: Helm version to install
            
        Returns:
            Dict containing installation status and details
        """
        result = {
            "success": False,
            "message": "",
            "version": "",
        }
        
        try:
            # First try using Homebrew if available
            try:
                # Check if Homebrew is installed
                subprocess.run(["brew", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                
                # Install using Homebrew
                subprocess.run(["brew", "install", "helm"], check=True)
                
                # Verify installation
                helm_installed, helm_version = self._check_helm_installed()
                
                if helm_installed:
                    result["success"] = True
                    result["message"] = "Helm installed successfully using Homebrew"
                    result["version"] = helm_version
                    return result
                
            except (subprocess.SubprocessError, FileNotFoundError):
                # Homebrew not available or installation failed
                # Fall back to script installation
                pass
                
            # Use script installation (same as Linux)
            return self._install_helm_linux(version)
            
        except Exception as e:
            logger.error(f"Error installing Helm: {e}")
            result["message"] = f"Error: {str(e)}"
            return result
    
    def _install_helm_windows(self, version: str) -> Dict[str, Any]:
        """
        Install Helm on Windows.
        
        Args:
            version: Helm version to install
            
        Returns:
            Dict containing installation status and details
        """
        result = {
            "success": False,
            "message": "",
            "version": "",
        }
        
        try:
            # Try using Chocolatey first if available
            try:
                # Check if Chocolatey is installed
                subprocess.run(["choco", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                
                # Install using Chocolatey
                subprocess.run(["choco", "install", "kubernetes-helm", "-y"], check=True)
                
                # Verify installation
                helm_installed, helm_version = self._check_helm_installed()
                
                if helm_installed:
                    result["success"] = True
                    result["message"] = "Helm installed successfully using Chocolatey"
                    result["version"] = helm_version
                    return result
                
            except (subprocess.SubprocessError, FileNotFoundError):
                # Chocolatey not available or installation failed
                pass
            
            # Suggest manual download for Windows
            result["message"] = "Automatic installation on Windows not supported. Please download from https://github.com/helm/helm/releases"
            return result
            
        except Exception as e:
            logger.error(f"Error installing Helm: {e}")
            result["message"] = f"Error: {str(e)}"
            return result
    
    def install_keda(self, version: str = "latest", namespace: str = "keda") -> Dict[str, Any]:
        """
        Install KEDA on the Kubernetes cluster using Helm.
        If KEDA is already installed, check its health status instead of reinstalling.
        
        Args:
            version: KEDA version to install, or 'latest'
            namespace: Namespace to install KEDA into
            
        Returns:
            Dict containing installation status and details
        """
        result = {
            "success": False,
            "message": "",
            "version": "",
        }
        
        try:
            # Check if KEDA is already installed
            keda_installed, keda_version = self._check_keda_installed()
            
            if keda_installed:
                logger.info(f"KEDA is already installed (version: {keda_version})")
                
                # Check health status of existing KEDA installation
                keda_namespace = self._find_keda_namespace()
                
                if keda_namespace:
                    logger.info(f"Found existing KEDA installation in namespace '{keda_namespace}'")
                    result["success"] = True
                    result["message"] = f"KEDA is already installed"
                    result["version"] = keda_version
                    result["status"] = "Installed"
                else:
                    result["success"] = True
                    result["message"] = f"KEDA is already installed but namespace could not be determined"
                    result["version"] = keda_version
                    result["status"] = "Unknown"
                
                return result
            
            # Continue with new KEDA installation if not already installed
            
            # Check if Helm is installed
            helm_installed, helm_version = self._check_helm_installed()
            
            if not helm_installed:
                result["message"] = "Helm is not installed. Please install Helm first."
                return result
            
            # Add KEDA Helm repository
            add_repo_cmd = ["helm", "repo", "add", "kedacore", "https://kedacore.github.io/charts"]
            subprocess.run(add_repo_cmd, check=True)
            
            # Update Helm repositories
            update_repo_cmd = ["helm", "repo", "update"]
            subprocess.run(update_repo_cmd, check=True)
            
            # Create namespace if not exists
            self._ensure_namespace_exists(namespace)
            
            # Install KEDA using Helm
            install_cmd = [
                "helm", "install", "keda",
                "kedacore/keda",
                "--namespace", namespace,
                "--create-namespace"
            ]
            
            if version != "latest":
                install_cmd.extend(["--version", version])
            
            logger.info(f"Installing KEDA {version if version != 'latest' else '(latest)'} in namespace '{namespace}'")
            subprocess.run(install_cmd, check=True)
            
            # Check if KEDA was installed successfully
            keda_installed, keda_version = self._check_keda_installed()
            if keda_installed:
                result["success"] = True
                result["message"] = "KEDA installed successfully"
                result["version"] = keda_version
                result["status"] = "Installed"
            else:
                result["message"] = "KEDA installation may have failed"
                result["status"] = "Failed"
            
            return result
            
        except subprocess.SubprocessError as e:
            logger.error(f"Error installing KEDA: {e}")
            result["message"] = f"Error during installation: {str(e)}"
            return result
        except Exception as e:
            logger.error(f"Error installing KEDA: {e}")
            result["message"] = f"Error: {str(e)}"
            return result
    
    def _ensure_namespace_exists(self, namespace: str) -> None:
        """
        Ensure the specified namespace exists in the cluster.
        Creates it if it doesn't exist.
        
        Args:
            namespace: The namespace to check/create
        """
        cmd = ["get", "namespace", namespace]
        
        result = self.connector.run_command(cmd)
        
        if not result["success"]:
            # Namespace doesn't exist, create it
            create_cmd = ["create", "namespace", namespace]
            self.connector.run_command(create_cmd)
    
    def _verify_keda_installation(self, namespace: str, timeout_seconds: int = 300) -> bool:
        """
        Verify KEDA installation by checking if required pods are running.
        
        Args:
            namespace: Namespace where KEDA is installed
            timeout_seconds: Maximum time to wait for KEDA pods to be ready
            
        Returns:
            bool: True if KEDA installation is verified, False otherwise
        """
        start_time = time.time()
        attempt = 0
        
        logger.info(f"Verifying KEDA installation in namespace '{namespace}' (timeout: {timeout_seconds}s)")
        
        while time.time() - start_time < timeout_seconds:
            attempt += 1
            # Check KEDA operator pods
            cmd = ["get", "pods", "-n", namespace, "-o", "json"]
            result = self.connector.run_command(cmd)
            
            if result["success"]:
                import json
                try:
                    pods_data = json.loads(result["output"])
                    pods = pods_data.get("items", [])
                    
                    if not pods:
                        logger.warning(f"No KEDA operator pods found in namespace '{namespace}' (attempt {attempt})")
                        time.sleep(10)
                        continue
                        
                    # Log pod status details for debugging
                    ready_pods = 0
                    for pod in pods:
                        pod_name = pod.get("metadata", {}).get("name", "unknown")
                        status = pod.get("status", {})
                        phase = status.get("phase", "Unknown")
                        container_statuses = status.get("containerStatuses", [])
                        
                        if self._check_pod_ready(pod):
                            ready_pods += 1
                            logger.info(f"Pod {pod_name} is ready (phase: {phase})")
                        else:
                            conditions = []
                            for condition in status.get("conditions", []):
                                if condition.get("status") != "True":
                                    conditions.append(f"{condition.get('type')}: {condition.get('reason')}")
                            
                            container_issues = []
                            for container in container_statuses:
                                if not container.get("ready", False):
                                    state = container.get("state", {})
                                    if "waiting" in state:
                                        reason = state["waiting"].get("reason", "Unknown")
                                        message = state["waiting"].get("message", "")
                                        container_issues.append(f"{container.get('name')}: {reason} - {message}")
                            
                            logger.warning(f"Pod {pod_name} not ready (phase: {phase})")
                            if conditions:
                                logger.warning(f"Pod conditions: {', '.join(conditions)}")
                            if container_issues:
                                logger.warning(f"Container issues: {', '.join(container_issues)}")
                    
                    if ready_pods == len(pods):
                        logger.info(f"All KEDA operator pods are ready ({ready_pods}/{len(pods)})")
                        return True
                    else:
                        logger.info(f"Not all KEDA pods are ready yet: {ready_pods}/{len(pods)} (attempt {attempt})")
                
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing pod data: {e}")
            else:
                logger.warning(f"Failed to get KEDA operator pods: {result.get('error', '')}")
            
            # If we've been waiting more than 1/3 of timeout, try checking if KEDA CRDs exist
            # This might mean KEDA is actually installed but pods are having issues
            if time.time() - start_time > timeout_seconds / 3:
                cmd = ["get", "pods", "-n", namespace, "-o", "json"]
                crd_result = self.connector.run_command(crd_cmd)
                if crd_result["success"] and "scaledobjects.keda.sh" in crd_result["output"]:
                    logger.info("KEDA CRDs are installed, but pods might still be starting")
            
            logger.info(f"Waiting for KEDA pods to be ready... (attempt {attempt})")
            time.sleep(10)
        
        logger.error(f"Timed out waiting for KEDA pods after {timeout_seconds} seconds")
        
        # As a last resort, check if KEDA CRDs exist - if they do, we'll consider KEDA installed
        # even if the pods aren't fully ready (they might just be slow to start)
        crd_cmd = ["get", "crd", "scaledobjects.keda.sh", "-o", "name"]
        crd_result = self.connector.run_command(crd_cmd)
        if crd_result["success"] and "scaledobjects.keda.sh" in crd_result["output"]:
            logger.warning("KEDA CRDs are installed but pods are not fully ready. Installation may still work.")
            return True
            
        return False
    
    def _check_pod_ready(self, pod_data: Dict[str, Any]) -> bool:
        """
        Check if a pod is running and ready.
        
        Args:
            pod_data: Pod data from Kubernetes API
            
        Returns:
            bool: True if the pod is ready, False otherwise
        """
        status = pod_data.get("status", {})
        
        # First check phase
        if status.get("phase") != "Running":
            return False
        
        # Check if all containers are ready
        container_statuses = status.get("containerStatuses", [])
        if not container_statuses:
            return False
            
        for container in container_statuses:
            if not container.get("ready", False):
                return False
                
        return True
    
    def _get_keda_version(self, namespace: str) -> str:
        """
        Get the installed KEDA version.
        
        Args:
            namespace: Namespace where KEDA is installed
            
        Returns:
            str: KEDA version or "Unknown"
        """
        cmd = ["get", "deployment", "-n", namespace, "keda-operator", "-o", "json"]
        result = self.connector.run_command(cmd)
        
        if result["success"]:
            import json
            try:
                deployment = json.loads(result["output"])
                containers = deployment.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
                
                for container in containers:
                    if container.get("name") == "keda-operator":
                        image = container.get("image", "")
                        # Extract version from image
                        if ":" in image:
                            return image.split(":")[-1]
                
            except (json.JSONDecodeError, KeyError, IndexError):
                pass
        
        return "Unknown"
    
    def get_cluster_info(self) -> Dict[str, Any]:
        """
        Get general information about the connected Kubernetes cluster.
        
        Returns:
            Dict containing cluster information
        """
        info = {
            "api_version": self.connector.get_api_version(),
            "context": self.connector.get_current_context(),
            "nodes": [],
            "namespaces": [],
            "helm_version": "",
            "keda_installed": False,
            "keda_version": "",
        }
        
        # Get nodes
        nodes_cmd = ["get", "nodes", "-o", "json"]
        nodes_result = self.connector.run_command(nodes_cmd)
        
        if nodes_result["success"]:
            import json
            try:
                nodes_data = json.loads(nodes_result["output"])
                info["nodes"] = [
                    {
                        "name": node.get("metadata", {}).get("name", ""),
                        "status": self._get_node_status(node),
                        "roles": self._get_node_roles(node),
                        "kernel_version": node.get("status", {}).get("nodeInfo", {}).get("kernelVersion", ""),
                        "kubelet_version": node.get("status", {}).get("nodeInfo", {}).get("kubeletVersion", ""),
                    }
                    for node in nodes_data.get("items", [])
                ]
            except json.JSONDecodeError:
                pass
        
        # Get namespaces
        info["namespaces"] = self.connector.get_namespaces()
        
        # Get Helm version
        helm_installed, helm_version = self._check_helm_installed()
        info["helm_version"] = helm_version if helm_installed else "Not installed"
        
        # Check KEDA installation
        keda_installed, keda_version = self._check_keda_installed()
        info["keda_installed"] = keda_installed
        info["keda_version"] = keda_version
        
        return info
    
    def _get_node_status(self, node: Dict[str, Any]) -> str:
        """
        Get node status from node data.
        
        Args:
            node: Node data from Kubernetes API
            
        Returns:
            str: Node status (Ready/NotReady)
        """
        conditions = node.get("status", {}).get("conditions", [])
        for condition in conditions:
            if condition.get("type") == "Ready":
                return "Ready" if condition.get("status") == "True" else "NotReady"
        return "Unknown"
    
    def _get_node_roles(self, node: Dict[str, Any]) -> List[str]:
        """
        Get node roles from node data.
        
        Args:
            node: Node data from Kubernetes API
            
        Returns:
            List[str]: Node roles
        """
        roles = []
        labels = node.get("metadata", {}).get("labels", {})
        
        for label in labels:
            if label.startswith("node-role.kubernetes.io/"):
                role = label.split("/")[-1]
                roles.append(role)
        
        return roles or ["<none>"]
    
    def _check_keda_installed(self) -> Tuple[bool, str]:
        """
        Check if KEDA is installed in the cluster.
        
        Returns:
            Tuple containing:
                bool indicating if KEDA is installed
                str containing KEDA version if installed, empty string otherwise
        """
        # Check for KEDA CRDs
        cmd = ["get", "crd", "scaledobjects.keda.sh"]
        result = self.connector.run_command(cmd)
        
        if not result["success"]:
            return False, ""
        
        # Try to get KEDA version from namespace
        for namespace in ["keda", "default"]:
            version = self._get_keda_version(namespace)
            if version != "Unknown":
                return True, version
        
        # KEDA is installed but couldn't determine version
        return True, "Unknown"
    
    def _find_keda_namespace(self) -> Optional[str]:
        """
        Find the namespace where KEDA is installed.
        Checks common namespaces like 'keda' and 'default'.
        
        Returns:
            str: Namespace where KEDA is installed, or None if not found
        """
        for namespace in ["keda", "default"]:
            cmd = ["get", "namespace", namespace]
            result = self.connector.run_command(cmd)
            
            if result["success"]:
                return namespace
            
        return None
    
    def _check_keda_crds(self) -> bool:
        """
        Check if KEDA CRDs are installed and available.
        
        Returns:
            bool: True if KEDA CRDs are available, False otherwise
        """
        cmd = ["get", "crd", "scaledobjects.keda.sh", "-o", "name"]
        result = self.connector.run_command(cmd)
        
        return result["success"] and "scaledobjects.keda.sh" in result["output"]

    def _verify_metrics_server_installation(self, namespace: str, timeout_seconds: int = 300) -> bool:
        """
        Verify metrics-server installation by checking if it's working properly.
        
        Args:
            namespace: Namespace where metrics-server is installed
            timeout_seconds: Maximum time to wait for metrics-server to be ready
            
        Returns:
            bool: True if metrics-server is working, False otherwise
        """
        start_time = time.time()
        attempt = 0
        
        logger.info(f"Verifying metrics-server installation in namespace '{namespace}' (timeout: {timeout_seconds}s)")
        
        while time.time() - start_time < timeout_seconds:
            attempt += 1
            
            # First check if metrics-server pod is running
            cmd = ["get", "pods", "-n", namespace, "-l", "k8s-app=metrics-server", "-o", "json"]
            result = self.connector.run_command(cmd)
            
            if result["success"]:
                import json
                try:
                    pods_data = json.loads(result["output"])
                    pods = pods_data.get("items", [])
                    
                    if not pods:
                        logger.warning(f"No metrics-server pods found in namespace '{namespace}' (attempt {attempt})")
                        time.sleep(10)
                        continue
                    
                    # Check if all pods are ready
                    ready_pods = 0
                    for pod in pods:
                        pod_name = pod.get("metadata", {}).get("name", "unknown")
                        status = pod.get("status", {})
                        phase = status.get("phase", "Unknown")
                        
                        if self._check_pod_ready(pod):
                            ready_pods += 1
                            logger.info(f"Pod {pod_name} is ready (phase: {phase})")
                        else:
                            logger.warning(f"Pod {pod_name} not ready (phase: {phase})")
                    
                    if ready_pods == len(pods):
                        logger.info(f"All metrics-server pods are ready ({ready_pods}/{len(pods)})")
                        
                        # Now verify metrics-server is working by trying to get metrics
                        try:
                            # Try to get node metrics
                            cmd = ["top", "nodes"]
                            result = self.connector.run_command(cmd)
                            
                            if result["success"] and result["output"].strip():
                                logger.info("Successfully retrieved node metrics")
                                return True
                            else:
                                logger.warning(f"Failed to get node metrics: {result.get('error', '')}")
                        except Exception as e:
                            logger.error(f"Error getting node metrics: {e}")
                    else:
                        logger.info(f"Not all metrics-server pods are ready yet: {ready_pods}/{len(pods)} (attempt {attempt})")
                
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing pod data: {e}")
            else:
                logger.warning(f"Failed to get metrics-server pods: {result.get('error', '')}")
            
            logger.info(f"Waiting for metrics-server to be ready... (attempt {attempt})")
            time.sleep(10)
        
        logger.error(f"Timed out waiting for metrics-server to be ready after {timeout_seconds} seconds")
        return False

    def install_metrics_server(self, version: str = "latest", namespace: str = "kube-system") -> Dict[str, Any]:
        """
        Install metrics-server on the Kubernetes cluster using the official manifest.
        If metrics-server is already installed, check its health status instead of reinstalling.
        
        Args:
            version: metrics-server version to install, or 'latest'
            namespace: Namespace to install metrics-server into (default: kube-system)
            
        Returns:
            Dict containing installation status and details
        """
        result = {
            "success": False,
            "message": "",
            "version": "",
        }
        
        try:
            # First check if we're connected to a cluster
            if not self.connector._connector:
                result["message"] = "Not connected to any Kubernetes cluster. Please connect first using 'k8s-tool connect'."
                return result
            
            # Verify cluster connection by getting API version
            api_version = self.connector.get_api_version()
            if not api_version:
                result["message"] = "Failed to verify cluster connection. Please ensure you're connected to the correct cluster."
                return result
            
            logger.info(f"Connected to Kubernetes cluster (API version: {api_version})")
            
            # Check if metrics-server is already installed
            metrics_server_installed, metrics_server_version = self._check_metrics_server_installed()
            
            if metrics_server_installed:
                logger.info(f"metrics-server is already installed (version: {metrics_server_version})")
                
                # Check health status of existing metrics-server installation
                metrics_server_namespace = self._find_metrics_server_namespace()
                
                if metrics_server_namespace:
                    logger.info(f"Found existing metrics-server installation in namespace '{metrics_server_namespace}'")
                    
                    # Verify the existing installation is working
                    if self._verify_metrics_server_installation(metrics_server_namespace):
                        result["success"] = True
                        result["message"] = f"metrics-server is already installed and working"
                        result["version"] = metrics_server_version
                        result["status"] = "Installed and Working"
                    else:
                        result["success"] = False
                        result["message"] = f"metrics-server is installed but not working properly"
                        result["version"] = metrics_server_version
                        result["status"] = "Installed but Not Working"
                else:
                    result["success"] = True
                    result["message"] = f"metrics-server is already installed but namespace could not be determined"
                    result["version"] = metrics_server_version
                    result["status"] = "Unknown"
                
                return result
            
            # Create namespace if not exists
            self._ensure_namespace_exists(namespace)
            
            # Create metrics-server manifest with the required configuration
            manifest = f"""
apiVersion: v1
kind: ServiceAccount
metadata:
  labels:
    k8s-app: metrics-server
  name: metrics-server
  namespace: {namespace}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  labels:
    k8s-app: metrics-server
    rbac.authorization.k8s.io/aggregate-to-admin: "true"
    rbac.authorization.k8s.io/aggregate-to-edit: "true"
    rbac.authorization.k8s.io/aggregate-to-view: "true"
  name: system:aggregated-metrics-reader
rules:
- apiGroups:
  - metrics.k8s.io
  resources:
  - pods
  - nodes
  verbs:
  - get
  - list
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  labels:
    k8s-app: metrics-server
  name: system:metrics-server
rules:
- apiGroups:
  - ""
  resources:
  - nodes/metrics
  - nodes/stats
  - nodes/proxy
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - ""
  resources:
  - pods
  - nodes
  verbs:
  - get
  - list
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  labels:
    k8s-app: metrics-server
  name: metrics-server-auth-reader
  namespace: {namespace}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: extension-apiserver-authentication-reader
subjects:
- kind: ServiceAccount
  name: metrics-server
  namespace: {namespace}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  labels:
    k8s-app: metrics-server
  name: metrics-server:system:auth-delegator
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:auth-delegator
subjects:
- kind: ServiceAccount
  name: metrics-server
  namespace: {namespace}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  labels:
    k8s-app: metrics-server
  name: system:metrics-server
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:metrics-server
subjects:
- kind: ServiceAccount
  name: metrics-server
  namespace: {namespace}
---
apiVersion: v1
kind: Service
metadata:
  labels:
    k8s-app: metrics-server
  name: metrics-server
  namespace: {namespace}
spec:
  ports:
  - name: main-port
    port: 4443
    protocol: TCP
    targetPort: 4443
  selector:
    k8s-app: metrics-server
---
apiVersion: apiregistration.k8s.io/v1
kind: APIService
metadata:
  labels:
    k8s-app: metrics-server
  name: v1beta1.metrics.k8s.io
spec:
  group: metrics.k8s.io
  groupPriorityMinimum: 100
  insecureSkipTLSVerify: true
  service:
    name: metrics-server
    namespace: {namespace}
    port: 4443
  version: v1beta1
  versionPriority: 100
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: metrics-server
  namespace: {namespace}
  labels:
    k8s-app: metrics-server
spec:
  selector:
    matchLabels:
      k8s-app: metrics-server
  template:
    metadata:
      labels:
        k8s-app: metrics-server
    spec:
      serviceAccountName: metrics-server
      containers:
      - name: metrics-server
        image: registry.k8s.io/metrics-server/metrics-server:v0.5.2
        imagePullPolicy: IfNotPresent
        args:
        - --cert-dir=/tmp
        - --secure-port=4443
        - --kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname
        - --kubelet-use-node-status-port
        - --metric-resolution=15s
        - --kubelet-insecure-tls
        - --v=4
        ports:
        - name: main-port
          containerPort: 4443
          protocol: TCP
        resources:
          requests:
            cpu: 100m
            memory: 200Mi
        livenessProbe:
          httpGet:
            path: /livez
            port: main-port
            scheme: HTTPS
          initialDelaySeconds: 30
          timeoutSeconds: 5
          periodSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /readyz
            port: main-port
            scheme: HTTPS
          initialDelaySeconds: 60
          timeoutSeconds: 5
          periodSeconds: 10
          failureThreshold: 3
        volumeMounts:
        - name: tmp-dir
          mountPath: /tmp
      volumes:
      - name: tmp-dir
        emptyDir: {{}}
      priorityClassName: system-cluster-critical
      nodeSelector:
        kubernetes.io/os: linux
"""
            
            # Create a temporary file with the manifest
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(manifest)
                manifest_path = f.name
            
            try:
                # Apply the manifest
                logger.info(f"Installing metrics-server in namespace '{namespace}'")
                apply_cmd = ["kubectl", "apply", "-f", manifest_path]
                subprocess.run(apply_cmd, check=True)
                
                # Check if metrics-server was installed successfully
                metrics_server_installed, metrics_server_version = self._check_metrics_server_installed()
                if metrics_server_installed:
                    # Verify the installation is working
                    if self._verify_metrics_server_installation(namespace):
                        result["success"] = True
                        result["message"] = "metrics-server installed and verified successfully"
                        result["version"] = metrics_server_version
                        result["status"] = "Installed and Working"
                    else:
                        result["success"] = False
                        result["message"] = "metrics-server installed but not working properly"
                        result["version"] = metrics_server_version
                        result["status"] = "Installed but Not Working"
                else:
                    result["message"] = "metrics-server installation may have failed"
                    result["status"] = "Failed"
                
            finally:
                # Clean up the temporary file
                os.unlink(manifest_path)
            
            return result
            
        except subprocess.SubprocessError as e:
            logger.error(f"Error installing metrics-server: {e}")
            result["message"] = f"Error during installation: {str(e)}"
            return result
        except Exception as e:
            logger.error(f"Error installing metrics-server: {e}")
            result["message"] = f"Error: {str(e)}"
            return result

    def _check_metrics_server_installed(self) -> Tuple[bool, str]:
        """
        Check if metrics-server is installed in the cluster.
        
        Returns:
            Tuple containing:
                bool indicating if metrics-server is installed
                str containing metrics-server version if installed, empty string otherwise
        """
        # Check for metrics-server deployment
        cmd = ["get", "deployment", "metrics-server", "-n", "kube-system", "-o", "json"]
        result = self.connector.run_command(cmd)
        
        if not result["success"]:
            return False, ""
        
        # Try to get metrics-server version from deployment
        try:
            import json
            deployment = json.loads(result["output"])
            containers = deployment.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
            
            for container in containers:
                if container.get("name") == "metrics-server":
                    image = container.get("image", "")
                    # Extract version from image
                    if ":" in image:
                        return True, image.split(":")[-1]
        except (json.JSONDecodeError, KeyError, IndexError):
            pass
        
        # metrics-server is installed but couldn't determine version
        return True, "Unknown"

    def _find_metrics_server_namespace(self) -> Optional[str]:
        """
        Find the namespace where metrics-server is installed.
        Checks common namespaces like 'kube-system'.
        
        Returns:
            str: Namespace where metrics-server is installed, or None if not found
        """
        for namespace in ["kube-system"]:
            cmd = ["get", "deployment", "metrics-server", "-n", namespace]
            result = self.connector.run_command(cmd)
            
            if result["success"]:
                return namespace
            
        return None