"""
Monitoring service module for retrieving health and status information from K8s deployments.
Provides functionality to check deployment health, status, and metrics.
"""

import logging
import json
from typing import Dict, Any, List, Optional

from ..connection.connector import ClusterConnector

logger = logging.getLogger(__name__)

class MonitoringService:
    """
    MonitoringService provides functionality to monitor and retrieve health information
    about Kubernetes deployments and resources.
    """
    
    def __init__(self, connector: ClusterConnector):
        """
        Initialize a new MonitoringService instance.
        
        Args:
            connector: A connected ClusterConnector instance
        """
        self.connector = connector
    
    def get_health_status(self, deployment_id: str, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive health status for a deployment by its ID.
        
        Args:
            deployment_id: Deployment ID (from labels)
            namespace: Kubernetes namespace, or None to search in all namespaces
            
        Returns:
            Dict containing health status and details
        """
        health_status = {
            "success": False,
            "message": "",
            "deployment_id": deployment_id,
            "status": "Unknown",
            "details": {
                "deployment": {},
                "pods": [],
                "services": [],
                "hpa": {},
                "scaled_object": {},
                "metrics": {},
                "events": [],
            },
            "summary": {
                "ready": False,
                "pods_ready": 0,
                "pods_total": 0,
                "restarts": 0,
                "status_reason": "",
                "resource_usage": {},
                "warnings": [],
            }
        }
        
        try:
            # Find deployments with the given ID
            deployment_found = False
            
            # Check in specified namespace or all namespaces
            if namespace:
                namespaces = [namespace]
            else:
                namespaces = self.connector.get_namespaces()
            
            for ns in namespaces:
                # Look for deployment with specified ID
                cmd = [
                    "get", "deployment",
                    "-l", f"deployment-id={deployment_id}",
                    "-n", ns,
                    "-o", "json"
                ]
                result = self.connector.run_command(cmd)
                
                if result["success"]:
                    deployments = json.loads(result["output"])
                    items = deployments.get("items", [])
                    
                    if items:
                        deployment = items[0]  # Get the first matching deployment
                        deployment_found = True
                        
                        # Extract deployment details
                        name = deployment.get("metadata", {}).get("name", "")
                        namespace = deployment.get("metadata", {}).get("namespace", ns)
                        
                        # Store deployment details
                        health_status["details"]["deployment"] = deployment
                        
                        # Get overall status
                        status = self._determine_deployment_status(deployment)
                        health_status["status"] = status
                        
                        # Get pods
                        pods_info = self._get_pods_info(name, namespace)
                        health_status["details"]["pods"] = pods_info["pods"]
                        
                        # Get services
                        services_info = self._get_services_info(name, namespace)
                        health_status["details"]["services"] = services_info["services"]
                        
                        # Get HPA
                        hpa_info = self._get_hpa_info(name, namespace)
                        if hpa_info["found"]:
                            health_status["details"]["hpa"] = hpa_info["hpa"]
                        
                        # Get KEDA ScaledObject
                        keda_info = self._get_keda_scaled_object_info(name, namespace)
                        if keda_info["found"]:
                            health_status["details"]["scaled_object"] = keda_info["scaled_object"]
                        
                        # Get metrics
                        metrics_info = self._get_metrics_info(name, namespace)
                        health_status["details"]["metrics"] = metrics_info["metrics"]
                        
                        # Get events
                        events_info = self._get_events_info(name, namespace)
                        health_status["details"]["events"] = events_info["events"]
                        
                        # Create summary
                        summary = self._create_health_summary(
                            deployment=deployment,
                            pods=pods_info["pods"],
                            metrics=metrics_info["metrics"],
                            events=events_info["events"],
                            status=status
                        )
                        health_status["summary"] = summary
                        
                        # Set success
                        health_status["success"] = True
                        health_status["message"] = f"Successfully retrieved health status for deployment {deployment_id}"
                        
                        # Stop searching other namespaces
                        break
            
            if not deployment_found:
                health_status["message"] = f"No deployment found with ID {deployment_id}"
            
            return health_status
                
        except Exception as e:
            logger.error(f"Error getting health status: {e}")
            health_status["message"] = f"Error getting health status: {str(e)}"
            return health_status
    
    def _determine_deployment_status(self, deployment: Dict[str, Any]) -> str:
        """
        Determine the overall status of a deployment.
        
        Args:
            deployment: Deployment resource data
            
        Returns:
            str: Status (Healthy, Degraded, Failed, Pending, Unknown)
        """
        try:
            status = deployment.get("status", {})
            spec = deployment.get("spec", {})
            
            # Get desired and available replicas
            desired_replicas = spec.get("replicas", 0)
            available_replicas = status.get("availableReplicas", 0)
            ready_replicas = status.get("readyReplicas", 0)
            updated_replicas = status.get("updatedReplicas", 0)
            
            # Check for generation mismatch (indicates update in progress)
            observed_generation = status.get("observedGeneration", 0)
            metadata_generation = deployment.get("metadata", {}).get("generation", 0)
            
            if observed_generation < metadata_generation:
                return "Updating"
            
            if desired_replicas == 0:
                return "Scaled to Zero"
                
            if available_replicas == 0:
                return "Unavailable"
                
            if available_replicas < desired_replicas:
                return "Degraded"
                
            if ready_replicas < desired_replicas:
                return "NotReady"
                
            if updated_replicas < desired_replicas:
                return "Updating"
                
            return "Healthy"
            
        except Exception:
            return "Unknown"
    
    def _get_pods_info(self, deployment_name: str, namespace: str) -> Dict[str, Any]:
        """
        Get information about pods for a deployment.
        
        Args:
            deployment_name: Name of the deployment
            namespace: Kubernetes namespace
            
        Returns:
            Dict containing pod information
        """
        result = {
            "success": False,
            "pods": [],
        }
        
        try:
            # Get pods with the app label
            cmd = ["get", "pods", "-l", f"app={deployment_name}", "-n", namespace, "-o", "json"]
            cmd_result = self.connector.run_command(cmd)
            
            if cmd_result["success"]:
                pods_data = json.loads(cmd_result["output"])
                result["pods"] = pods_data.get("items", [])
                result["success"] = True
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting pods info: {e}")
            return result
    
    def _get_services_info(self, deployment_name: str, namespace: str) -> Dict[str, Any]:
        """
        Get information about services for a deployment.
        
        Args:
            deployment_name: Name of the deployment
            namespace: Kubernetes namespace
            
        Returns:
            Dict containing service information
        """
        result = {
            "success": False,
            "services": [],
        }
        
        try:
            # Get services with the app label matching the deployment name
            cmd = ["get", "services", "-l", f"app={deployment_name}", "-n", namespace, "-o", "json"]
            cmd_result = self.connector.run_command(cmd)
            
            if cmd_result["success"]:
                services_data = json.loads(cmd_result["output"])
                result["services"] = services_data.get("items", [])
                result["success"] = True
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting services info: {e}")
            return result
    
    def _get_hpa_info(self, deployment_name: str, namespace: str) -> Dict[str, Any]:
        """
        Get information about HPA for a deployment.
        
        Args:
            deployment_name: Name of the deployment
            namespace: Kubernetes namespace
            
        Returns:
            Dict containing HPA information
        """
        result = {
            "success": False,
            "found": False,
            "hpa": {},
        }
        
        try:
            # Get HPA for the deployment
            cmd = ["get", "hpa", "-n", namespace, "-o", "json"]
            cmd_result = self.connector.run_command(cmd)
            
            if cmd_result["success"]:
                hpas_data = json.loads(cmd_result["output"])
                
                # Find HPA for this deployment
                for hpa in hpas_data.get("items", []):
                    target_ref = hpa.get("spec", {}).get("scaleTargetRef", {})
                    
                    if (target_ref.get("kind") == "Deployment" and 
                        target_ref.get("name") == deployment_name):
                        result["hpa"] = hpa
                        result["found"] = True
                        result["success"] = True
                        break
                
                if not result["found"]:
                    result["success"] = True  # No error, but no HPA found
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting HPA info: {e}")
            return result
    
    def _get_keda_scaled_object_info(self, deployment_name: str, namespace: str) -> Dict[str, Any]:
        """
        Get information about KEDA ScaledObject for a deployment.
        
        Args:
            deployment_name: Name of the deployment
            namespace: Kubernetes namespace
            
        Returns:
            Dict containing ScaledObject information
        """
        result = {
            "success": False,
            "found": False,
            "scaled_object": {},
        }
        
        try:
            # Get ScaledObjects in the namespace
            cmd = ["get", "scaledobject", "-n", namespace, "-o", "json"]
            cmd_result = self.connector.run_command(cmd)
            
            if cmd_result["success"]:
                scaled_objects_data = json.loads(cmd_result["output"])
                
                # Find ScaledObject for this deployment
                for scaled_object in scaled_objects_data.get("items", []):
                    target_ref = scaled_object.get("spec", {}).get("scaleTargetRef", {})
                    
                    if target_ref.get("name") == deployment_name:
                        result["scaled_object"] = scaled_object
                        result["found"] = True
                        result["success"] = True
                        break
                
                if not result["found"]:
                    result["success"] = True  # No error, but no ScaledObject found
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting KEDA ScaledObject info: {e}")
            return result
    
    def _get_metrics_info(self, deployment_name: str, namespace: str) -> Dict[str, Any]:
        """
        Get metrics information for a deployment.
        
        Args:
            deployment_name: Name of the deployment
            namespace: Kubernetes namespace
            
        Returns:
            Dict containing metrics information
        """
        result = {
            "success": False,
            "metrics": {
                "cpu": {},
                "memory": {},
                "network": {},
            },
        }
        
        try:
            # Try to get metrics using kubectl top
            pods_cmd = ["top", "pod", "-l", f"app={deployment_name}", "-n", namespace]
            pods_result = self.connector.run_command(pods_cmd)
            
            if pods_result["success"]:
                # Parse the output to extract CPU and memory metrics
                lines = pods_result["output"].strip().split("\n")
                
                if len(lines) > 1:  # Skip header line
                    total_cpu_millicores = 0
                    total_memory_bytes = 0
                    pod_count = 0
                    
                    # Process each pod line
                    for line in lines[1:]:
                        parts = line.split()
                        if len(parts) >= 3:
                            # Parse CPU value (e.g., "10m" or "0.1")
                            cpu_value = parts[1]
                            if cpu_value.endswith("m"):
                                cpu_millicores = int(cpu_value[:-1])
                            else:
                                cpu_millicores = int(float(cpu_value) * 1000)
                            
                            # Parse memory value (e.g., "10Mi" or "1Gi")
                            memory_value = parts[2]
                            memory_bytes = self._parse_memory_value(memory_value)
                            
                            total_cpu_millicores += cpu_millicores
                            total_memory_bytes += memory_bytes
                            pod_count += 1
                    
                    # Calculate averages and set metrics
                    if pod_count > 0:
                        result["metrics"]["cpu"]["total_millicores"] = total_cpu_millicores
                        result["metrics"]["cpu"]["average_millicores"] = total_cpu_millicores / pod_count
                        result["metrics"]["cpu"]["total_cores"] = total_cpu_millicores / 1000
                        result["metrics"]["cpu"]["average_cores"] = (total_cpu_millicores / 1000) / pod_count
                        
                        result["metrics"]["memory"]["total_bytes"] = total_memory_bytes
                        result["metrics"]["memory"]["average_bytes"] = total_memory_bytes / pod_count
                        result["metrics"]["memory"]["total_formatted"] = self._format_memory_value(total_memory_bytes)
                        result["metrics"]["memory"]["average_formatted"] = self._format_memory_value(total_memory_bytes / pod_count)
                        
                        result["success"] = True
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting metrics info: {e}")
            return result
    
    def _get_events_info(self, deployment_name: str, namespace: str) -> Dict[str, Any]:
        """
        Get events information related to a deployment.
        
        Args:
            deployment_name: Name of the deployment
            namespace: Kubernetes namespace
            
        Returns:
            Dict containing events information
        """
        result = {
            "success": False,
            "events": [],
        }
        
        try:
            # Get events for the deployment
            cmd = [
                "get", "events",
                "--field-selector", f"involvedObject.name={deployment_name}",
                "-n", namespace,
                "-o", "json"
            ]
            cmd_result = self.connector.run_command(cmd)
            
            if cmd_result["success"]:
                events_data = json.loads(cmd_result["output"])
                result["events"] = events_data.get("items", [])
                result["success"] = True
            
            # Also get events for the pods
            pods_cmd = ["get", "pods", "-l", f"app={deployment_name}", "-n", namespace, "-o", "json"]
            pods_result = self.connector.run_command(pods_cmd)
            
            if pods_result["success"]:
                pods_data = json.loads(pods_result["output"])
                
                for pod in pods_data.get("items", []):
                    pod_name = pod.get("metadata", {}).get("name", "")
                    
                    if pod_name:
                        pod_events_cmd = [
                            "get", "events",
                            "--field-selector", f"involvedObject.name={pod_name}",
                            "-n", namespace,
                            "-o", "json"
                        ]
                        pod_events_result = self.connector.run_command(pod_events_cmd)
                        
                        if pod_events_result["success"]:
                            pod_events_data = json.loads(pod_events_result["output"])
                            result["events"].extend(pod_events_data.get("items", []))
            
            # Sort events by last timestamp
            result["events"].sort(
                key=lambda e: e.get("lastTimestamp", ""),
                reverse=True
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting events info: {e}")
            return result
    
    def _create_health_summary(
        self,
        deployment: Dict[str, Any],
        pods: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        events: List[Dict[str, Any]],
        status: str
    ) -> Dict[str, Any]:
        """
        Create a summary of deployment health.
        
        Args:
            deployment: Deployment resource data
            pods: List of pod resources
            metrics: Metrics data
            events: List of events
            status: Overall deployment status
            
        Returns:
            Dict containing health summary
        """
        summary = {
            "ready": status == "Healthy",
            "pods_ready": 0,
            "pods_total": len(pods),
            "restarts": 0,
            "status_reason": status,
            "resource_usage": {
                "cpu": metrics.get("cpu", {}),
                "memory": metrics.get("memory", {}),
            },
            "warnings": [],
            "recent_events": [],
        }
        
        # Count ready pods and restarts
        for pod in pods:
            pod_status = pod.get("status", {})
            
            # Check if pod is ready
            if pod_status.get("phase") == "Running":
                conditions = pod_status.get("conditions", [])
                for condition in conditions:
                    if condition.get("type") == "Ready" and condition.get("status") == "True":
                        summary["pods_ready"] += 1
                        break
            
            # Count restarts
            container_statuses = pod_status.get("containerStatuses", [])
            for container in container_statuses:
                summary["restarts"] += container.get("restartCount", 0)
        
        # Check for deployment issues
        deployment_conditions = deployment.get("status", {}).get("conditions", [])
        for condition in deployment_conditions:
            if condition.get("type") in ["Progressing", "Available", "ReplicaFailure"]:
                if condition.get("status") != "True" and condition.get("type") != "ReplicaFailure":
                    summary["warnings"].append({
                        "type": condition.get("type", ""),
                        "reason": condition.get("reason", ""),
                        "message": condition.get("message", ""),
                        "last_update": condition.get("lastUpdateTime", ""),
                    })
                elif condition.get("status") == "True" and condition.get("type") == "ReplicaFailure":
                    summary["warnings"].append({
                        "type": "ReplicaFailure",
                        "reason": condition.get("reason", ""),
                        "message": condition.get("message", ""),
                        "last_update": condition.get("lastUpdateTime", ""),
                    })
        
        # Extract recent warning events
        for event in events[:5]:  # Get most recent 5 events
            if event.get("type") in ["Warning", "Normal"]:
                summary["recent_events"].append({
                    "type": event.get("type", ""),
                    "reason": event.get("reason", ""),
                    "message": event.get("message", ""),
                    "count": event.get("count", 1),
                    "last_seen": event.get("lastTimestamp", ""),
                    "object": event.get("involvedObject", {}).get("kind", "") + "/" + 
                             event.get("involvedObject", {}).get("name", ""),
                })
        
        # Check for pod issues
        for pod in pods:
            pod_status = pod.get("status", {})
            pod_name = pod.get("metadata", {}).get("name", "")
            
            # Check container status
            container_statuses = pod_status.get("containerStatuses", [])
            for container in container_statuses:
                waiting = container.get("state", {}).get("waiting", {})
                terminated = container.get("state", {}).get("terminated", {})
                
                if waiting and waiting.get("reason") not in ["ContainerCreating"]:
                    summary["warnings"].append({
                        "type": "PodIssue",
                        "reason": waiting.get("reason", ""),
                        "message": waiting.get("message", ""),
                        "pod": pod_name,
                        "container": container.get("name", ""),
                    })
                
                if terminated and terminated.get("exitCode") != 0:
                    summary["warnings"].append({
                        "type": "PodTerminated",
                        "reason": terminated.get("reason", ""),
                        "message": terminated.get("message", ""),
                        "pod": pod_name,
                        "container": container.get("name", ""),
                        "exit_code": terminated.get("exitCode", 0),
                    })
        
        return summary
    
    def _parse_memory_value(self, memory_str: str) -> float:
        """
        Parse memory value from string to bytes.
        
        Args:
            memory_str: Memory string (e.g., '100Mi', '1.5Gi')
            
        Returns:
            float: Memory value in bytes
        """
        # Remove any non-allowed characters
        memory_str = memory_str.strip()
        
        # Extract numeric part and unit
        if memory_str.endswith("Ki"):
            return float(memory_str[:-2]) * 1024
        elif memory_str.endswith("Mi"):
            return float(memory_str[:-2]) * 1024 * 1024
        elif memory_str.endswith("Gi"):
            return float(memory_str[:-2]) * 1024 * 1024 * 1024
        elif memory_str.endswith("Ti"):
            return float(memory_str[:-2]) * 1024 * 1024 * 1024 * 1024
        elif memory_str.endswith("K") or memory_str.endswith("k"):
            return float(memory_str[:-1]) * 1000
        elif memory_str.endswith("M") or memory_str.endswith("m"):
            return float(memory_str[:-1]) * 1000 * 1000
        elif memory_str.endswith("G") or memory_str.endswith("g"):
            return float(memory_str[:-1]) * 1000 * 1000 * 1000
        else:
            try:
                return float(memory_str)
            except ValueError:
                return 0
    
    def _format_memory_value(self, bytes_value: float) -> str:
        """
        Format memory value in bytes to human-readable format.
        
        Args:
            bytes_value: Memory in bytes
            
        Returns:
            str: Formatted memory string
        """
        if bytes_value < 1000:
            return f"{bytes_value:.0f}B"
        elif bytes_value < 1000 * 1000:
            return f"{bytes_value / 1000:.2f}KB"
        elif bytes_value < 1000 * 1000 * 1000:
            return f"{bytes_value / (1000 * 1000):.2f}MB"
        else:
            return f"{bytes_value / (1000 * 1000 * 1000):.2f}GB"