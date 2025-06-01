"""
Deployment manager for Kubernetes deployments.
"""

import os
import sys
import logging
import json
import yaml
import time
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import uuid
import tempfile
from typing import Dict, Any, List, Optional, Union

from k8s_tool.connection.connector import ClusterConnector

logger = logging.getLogger(__name__)

class DeploymentManager:
    """
    DeploymentManager provides functionality to create and manage Kubernetes deployments
    with KEDA-based event-driven scaling.
    """
    
    def __init__(self, connector: ClusterConnector):
        """
        Initialize a new DeploymentManager instance.
        
        Args:
            connector: A connected ClusterConnector instance
        """
        self.connector = connector
    
    def create_deployment(
        self,
        name: str,
        image: str,
        namespace: str = "default",
        replicas: int = 1,
        port: int = None,
        env_vars: Dict[str, str] = None,
        volume_mounts: List[Dict[str, Any]] = None,
        volumes: List[Dict[str, Any]] = None,
        service_type: str = "ClusterIP",
        resource_limits: Dict[str, str] = None,
        resource_requests: Dict[str, str] = None,
        liveness_probe: Dict[str, Any] = None,
        readiness_probe: Dict[str, Any] = None,
        startup_probe: Dict[str, Any] = None,
        annotations: Dict[str, str] = None,
        autoscaling_enabled: bool = False,
        min_replicas: int = 1,
        max_replicas: int = 10,
        cpu_target_percentage: int = 80,
        keda_enabled: bool = False,
        keda_triggers: List[Dict[str, Any]] = None,
        **options
    ) -> Dict[str, Any]:
        """
        Create a deployment with associated service and autoscaling.
        
        Args:
            name: Deployment name
            image: Container image
            namespace: Kubernetes namespace
            replicas: Number of replicas
            port: Container port to expose (if None, no service will be created)
            env_vars: Environment variables as key-value pairs
            volume_mounts: Volume mount configurations
            volumes: Volume configurations
            service_type: Service type (ClusterIP, NodePort, LoadBalancer)
            resource_limits: Resource limits (cpu, memory)
            resource_requests: Resource requests (cpu, memory)
            liveness_probe: Liveness probe configuration
            readiness_probe: Readiness probe configuration
            startup_probe: Startup probe configuration
            annotations: Deployment annotations
            autoscaling_enabled: Whether to enable HPA
            min_replicas: Minimum replicas for HPA
            max_replicas: Maximum replicas for HPA
            cpu_target_percentage: CPU target percentage for HPA
            keda_enabled: Whether to enable KEDA scaling
            keda_triggers: List of KEDA ScaledObject trigger configurations
            **options: Additional options
            
        Returns:
            Dict containing status and resource information
        """
        result = {
            "success": False,
            "message": "",
            "deployment_id": "",
            "deployment": {},
            "service": {},
            "hpa": {},
            "scaled_object": {},
        }
        
        # Ensure resource_limits and resource_requests are always dicts
        resource_limits = resource_limits or {}
        resource_requests = resource_requests or {}
        
        # Generate unique deployment ID
        deployment_id = f"{name}-{str(uuid.uuid4())[:8]}"
        result["deployment_id"] = deployment_id
        
        try:
            # Support both single port (int) and multiple ports (list)
            if isinstance(port, list):
                ports = port if port else [80]
            elif port is not None:
                ports = [port]
            else:
                ports = [80]
            env_vars = env_vars or {}
            labels = options.get("labels", {}) or {}
            
            # Add deployment ID to labels
            labels["deployment-id"] = f"{deployment_id}"
            # Add app label with deployment name
            labels["app"] = name
            
            # Pass probes and all options
            deployment_result = self._create_deployment_resource(
                name=name,
                namespace=namespace,
                image=image,
                replicas=replicas,
                ports=ports,
                env_vars=env_vars,
                volume_mounts=volume_mounts,
                volumes=volumes,
                cpu_request=resource_requests.get('cpu', '100m'),
                cpu_limit=resource_limits.get('cpu', '500m'),
                memory_request=resource_requests.get('memory', '128Mi'),
                memory_limit=resource_limits.get('memory', '512Mi'),
                labels=labels,
                annotations=annotations,
                liveness_probe=liveness_probe,
                readiness_probe=readiness_probe,
                startup_probe=startup_probe,
            )
            
            if not deployment_result["success"]:
                result["message"] = f"Failed to create deployment: {deployment_result['message']}"
                return result
                
            result["deployment"] = deployment_result["resource"]
            
            # Create service if any ports are specified
            if ports:
                service_ports = []
                for p in ports:
                    service_ports.append({
                        "port": p,
                        "targetPort": p,
                        "protocol": "TCP",
                        "name": f"port-{p}"
                    })
                service_result = self._create_service_resource(
                    name=name,
                    namespace=namespace,
                    labels=labels,
                    ports=service_ports,
                    service_type=service_type,
                )
                if not service_result["success"]:
                    result["message"] = f"Created deployment but failed to create service: {service_result['message']}"
                    return result
                    
                result["service"] = service_result["resource"]
                
            # Create HPA or KEDA ScaledObject
            if keda_enabled and keda_triggers:
                # Create KEDA ScaledObject
                scaled_object_result = self._create_keda_scaled_object(
                    name=name,
                    namespace=namespace,
                    labels=labels,
                    min_replicas=min_replicas,
                    max_replicas=max_replicas,
                    deployment_name=name,
                    triggers=keda_triggers,
                )
                
                if not scaled_object_result["success"]:
                    result["message"] = f"Created deployment and service but failed to create KEDA ScaledObject: {scaled_object_result['message']}"
                    return result
                    
                result["scaled_object"] = scaled_object_result["resource"]
                result["message"] = "Deployment, service, and KEDA ScaledObject created successfully"
                
            elif autoscaling_enabled:
                # Create standard HPA
                hpa_result = self._create_hpa_resource(
                    name=name,
                    namespace=namespace,
                    labels=labels,
                    min_replicas=min_replicas,
                    max_replicas=max_replicas,
                    cpu_target_percentage=cpu_target_percentage,
                )
                
                if not hpa_result["success"]:
                    result["message"] = f"Created deployment and service but failed to create HPA: {hpa_result['message']}"
                    return result
                    
                result["hpa"] = hpa_result["resource"]
                result["message"] = "Deployment, service, and HPA created successfully"
                
            else:
                result["message"] = "Deployment and service created successfully"
            
            # Wait for deployment to be ready
            if self._wait_for_deployment_ready(name, namespace):
                result["success"] = True
            else:
                result["message"] = f"{result['message']} (Warning: Deployment is not ready)"
            
            # Prepare result with just the essential information
            result["summary"] = self.get_created_resources_summary(result)
            
            # Clean up the full resource data to keep only essential parts
            if "deployment" in result:
                result["deployment"] = {
                    "name": name,
                    "namespace": namespace,
                    "id": deployment_id
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating deployment: {e}")
            result["message"] = f"Error creating deployment: {str(e)}"
            return result
    
    def _create_deployment_resource(
        self,
        name: str,
        image: str,
        namespace: str,
        ports: List[int],
        replicas: int,
        cpu_request: str,
        cpu_limit: str,
        memory_request: str,
        memory_limit: str,
        env_vars: Dict[str, str],
        labels: Dict[str, str],
        annotations: Dict[str, str],
        volume_mounts: List[Dict[str, Any]] = None,
        volumes: List[Dict[str, Any]] = None,
        liveness_probe: Dict[str, Any] = None,
        readiness_probe: Dict[str, Any] = None,
        startup_probe: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Create a Kubernetes Deployment resource.
        
        Args:
            name: Deployment name
            image: Container image
            namespace: Kubernetes namespace
            ports: List of ports to expose
            replicas: Number of replicas
            cpu_request: CPU request
            cpu_limit: CPU limit
            memory_request: Memory request
            memory_limit: Memory limit
            env_vars: Environment variables
            labels: Labels for the deployment
            annotations: Annotations for the deployment
            volume_mounts: Volume mount configurations
            volumes: Volume configurations
            liveness_probe: Liveness probe configuration
            readiness_probe: Readiness probe configuration
            startup_probe: Startup probe configuration
            
        Returns:
            Dict containing resource creation status and details
        """
        result = {
            "success": False,
            "message": "",
            "resource": {},
        }
        
        try:
            env = [{"name": key, "value": value} for key, value in env_vars.items()]
            container_ports = [{"containerPort": port} for port in ports]
            container = {
                "name": name,
                "image": image,
                "imagePullPolicy": "Always" if "latest" in image else "IfNotPresent",
                "ports": container_ports,
                "resources": {
                    "requests": {
                        "cpu": cpu_request,
                        "memory": memory_request,
                    },
                    "limits": {
                        "cpu": cpu_limit,
                        "memory": memory_limit,
                    }
                },
                "env": env
            }
            if volume_mounts:
                container["volumeMounts"] = volume_mounts
            if liveness_probe:
                container["livenessProbe"] = liveness_probe
            if readiness_probe:
                container["readinessProbe"] = readiness_probe
            if startup_probe:
                container["startupProbe"] = startup_probe
            pod_spec = {
                "containers": [container]
            }
            if volumes:
                pod_spec["volumes"] = volumes
            deployment = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": name,
                    "namespace": namespace,
                    "labels": labels,
                    "annotations": annotations,
                },
                "spec": {
                    "replicas": replicas,
                    "selector": {
                        "matchLabels": labels,
                    },
                    "template": {
                        "metadata": {
                            "labels": labels,
                        },
                        "spec": pod_spec
                    }
                }
            }
            with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w+", delete=False) as temp:
                yaml.dump(deployment, temp)
                temp_path = temp.name
            try:
                apply_cmd = ["apply", "-f", temp_path]
                apply_result = self.connector.run_command(
                    apply_cmd,
                    manifest_data=deployment
                )
                if not apply_result["success"]:
                    result["message"] = f"Failed to apply deployment: {apply_result['error']}"
                    return result
                get_cmd = ["get", "deployment", name, "-n", namespace, "-o", "json"]
                get_result = self.connector.run_command(get_cmd)
                if get_result["success"]:
                    result["resource"] = json.loads(get_result["output"])
                    result["success"] = True
                    result["message"] = "Deployment created successfully"
                else:
                    result["message"] = "Deployment was applied but could not retrieve details"
                    result["success"] = True
                return result
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
        except Exception as e:
            logger.error(f"Error creating deployment: {e}")
            result["message"] = f"Error creating deployment: {str(e)}"
            return result
    
    def _create_service_resource(
        self,
        name: str,
        namespace: str,
        ports: List[Dict[str, Any]],
        labels: Dict[str, str],
        service_type: str,
    ) -> Dict[str, Any]:
        """
        Create a Kubernetes Service resource.
        
        Args:
            name: Service name
            namespace: Kubernetes namespace
            ports: List of ports to expose
            labels: Labels for the service
            service_type: Service type (ClusterIP, NodePort, LoadBalancer)
            
        Returns:
            Dict containing resource creation status and details
        """
        result = {
            "success": False,
            "message": "",
            "resource": {},
        }
        
        try:
            # Create service manifest
            service = {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {
                    "name": name,
                    "namespace": namespace,
                    "labels": labels,
                },
                "spec": {
                    "selector": labels,  # Use the same labels as the deployment
                    "ports": ports,
                    "type": service_type
                }
            }
            
            # Create the service using a temporary file
            with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w+", delete=False) as temp:
                yaml.dump(service, temp)
                temp_path = temp.name
            
            try:
                # Apply the service
                apply_cmd = ["apply", "-f", temp_path]
                apply_result = self.connector.run_command(
                    apply_cmd,
                    manifest_data=service  # Pass manifest data for namespace check
                )
                
                if not apply_result["success"]:
                    result["message"] = f"Failed to apply service: {apply_result['error']}"
                    return result
                
                # Get the created service
                get_cmd = ["get", "service", name, "-n", namespace, "-o", "json"]
                get_result = self.connector.run_command(get_cmd)
                
                if get_result["success"]:
                    result["resource"] = json.loads(get_result["output"])
                    result["success"] = True
                    result["message"] = "Service created successfully"
                else:
                    result["message"] = "Service was applied but could not retrieve details"
                    result["success"] = True  # Still mark as success since the service was created
                
                return result
                
            finally:
                # Clean up the temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
        except Exception as e:
            logger.error(f"Error creating service: {e}")
            result["message"] = f"Error creating service: {str(e)}"
            return result
    
    def _create_hpa_resource(
        self,
        name: str,
        namespace: str,
        min_replicas: int,
        max_replicas: int,
        cpu_target_percentage: int = None,
        memory_utilization: int = None,
        custom_metrics: List[Dict[str, Any]] = None,
        labels: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """
        Create a Horizontal Pod Autoscaler resource.
        
        Args:
            name: Deployment name to scale
            namespace: Kubernetes namespace
            min_replicas: Minimum number of replicas
            max_replicas: Maximum number of replicas
            cpu_target_percentage: Target CPU utilization percentage
            memory_utilization: Target memory utilization percentage
            custom_metrics: List of custom metrics configurations
            labels: Labels to apply to the HPA
            
        Returns:
            Dict containing resource creation status and details
        """
        result = {
            "success": False,
            "message": "",
            "resource": {},
        }
        
        try:
            # Set default labels if not provided
            labels = labels or {}
            
            # Create HPA manifest
            hpa = {
                "apiVersion": "autoscaling/v2",
                "kind": "HorizontalPodAutoscaler",
                "metadata": {
                    "name": f"{name}-hpa",
                    "namespace": namespace,
                    "labels": labels,
                },
                "spec": {
                    "scaleTargetRef": {
                        "apiVersion": "apps/v1",
                        "kind": "Deployment",
                        "name": name
                    },
                    "minReplicas": min_replicas,
                    "maxReplicas": max_replicas,
                    "metrics": []
                }
            }
            
            # Add CPU metric if specified
            if cpu_target_percentage:
                hpa["spec"]["metrics"].append({
                    "type": "Resource",
                    "resource": {
                        "name": "cpu",
                        "target": {
                            "type": "Utilization",
                            "averageUtilization": cpu_target_percentage
                        }
                    }
                })
            
            # Add memory metric if specified
            if memory_utilization:
                hpa["spec"]["metrics"].append({
                    "type": "Resource",
                    "resource": {
                        "name": "memory",
                        "target": {
                            "type": "Utilization",
                            "averageUtilization": memory_utilization
                        }
                    }
                })
                
            # Add custom metrics if specified
            if custom_metrics:
                for metric in custom_metrics:
                    hpa["spec"]["metrics"].append(metric)
            
            # Create the HPA using a temporary file
            with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w+", delete=False) as temp:
                yaml.dump(hpa, temp)
                temp_path = temp.name
            
            try:
                # Apply the HPA
                apply_cmd = ["apply", "-f", temp_path]
                apply_result = self.connector.run_command(
                    apply_cmd,
                    manifest_data=hpa  # Pass manifest data for namespace check
                )
                
                if not apply_result["success"]:
                    result["message"] = f"Failed to apply HPA: {apply_result['error']}"
                    return result
                
                # Get the created HPA
                get_cmd = ["get", "hpa", f"{name}-hpa", "-n", namespace, "-o", "json"]
                get_result = self.connector.run_command(
                    get_cmd,
                    manifest_data=hpa  # Pass manifest data for namespace check
                )
                
                if get_result["success"]:
                    result["resource"] = json.loads(get_result["output"])
                    result["success"] = True
                    result["message"] = "HPA created successfully"
                else:
                    result["message"] = "HPA was applied but could not retrieve details"
                    result["success"] = True  # Still mark as success since the HPA was created
                
                return result
                
            finally:
                # Clean up the temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
        except Exception as e:
            logger.error(f"Error creating HPA: {e}")
            result["message"] = f"Error creating HPA: {str(e)}"
            return result
    
    def _create_keda_scaled_object(
        self,
        name: str,
        namespace: str,
        min_replicas: int,
        max_replicas: int,
        deployment_name: str,
        triggers: List[Dict[str, Any]],
        labels: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """
        Create a KEDA ScaledObject for a deployment.
        
        Args:
            name: ScaledObject name
            namespace: Kubernetes namespace
            min_replicas: Minimum number of replicas
            max_replicas: Maximum number of replicas
            deployment_name: Name of the deployment to scale
            triggers: List of KEDA trigger configurations
            labels: Labels to apply to the ScaledObject
            
        Returns:
            Dict containing resource creation status and details
        """
        result = {
            "success": False,
            "message": "",
            "resource": {},
        }
        
        try:
            # Set default labels if not provided
            labels = labels or {}
            
            # Create ScaledObject manifest
            scaled_object = {
                "apiVersion": "keda.sh/v1alpha1",
                "kind": "ScaledObject",
                "metadata": {
                    "name": name,
                    "namespace": namespace,
                    "labels": labels,
                },
                "spec": {
                    "scaleTargetRef": {
                        "apiVersion": "apps/v1",
                        "kind": "Deployment",
                        "name": deployment_name
                    },
                    "minReplicaCount": min_replicas,
                    "maxReplicaCount": max_replicas,
                    "triggers": triggers
                }
            }
            
            # Create the ScaledObject using a temporary file
            with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w+", delete=False) as temp:
                yaml.dump(scaled_object, temp)
                temp_path = temp.name
            
            try:
                # Apply the ScaledObject
                apply_cmd = ["apply", "-f", temp_path]
                apply_result = self.connector.run_command(
                    apply_cmd,
                    manifest_data=scaled_object  # Pass manifest data for namespace check
                )
                
                if not apply_result["success"]:
                    result["message"] = f"Failed to apply ScaledObject: {apply_result['error']}"
                    return result
                
                # Get the created ScaledObject
                get_cmd = ["get", "scaledobject", name, "-n", namespace, "-o", "json"]
                get_result = self.connector.run_command(
                    get_cmd,
                    manifest_data=scaled_object  # Pass manifest data for namespace check
                )
                
                if get_result["success"]:
                    result["resource"] = json.loads(get_result["output"])
                    result["success"] = True
                    result["message"] = "ScaledObject created successfully"
                else:
                    result["message"] = "ScaledObject was applied but could not retrieve details"
                    result["success"] = True  # Still mark as success since the ScaledObject was created
                
                return result
                
            finally:
                # Clean up the temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
        except Exception as e:
            logger.error(f"Error creating ScaledObject: {e}")
            result["message"] = f"Error creating ScaledObject: {str(e)}"
            return result
    
    def _wait_for_deployment_ready(self, name: str, namespace: str, timeout_seconds: int = 120) -> bool:
        """
        Wait for a deployment to be ready.
        
        Args:
            name: Deployment name
            namespace: Kubernetes namespace
            timeout_seconds: Maximum time to wait in seconds
            
        Returns:
            bool: True if deployment is ready, False otherwise
        """
        logger.info(f"Waiting for deployment {name} to be ready...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            # Get deployment status
            cmd = ["get", "deployment", name, "-n", namespace, "-o", "json"]
            result = self.connector.run_command(cmd)
            
            if result["success"]:
                deployment_data = json.loads(result["output"])
                
                status = deployment_data.get("status", {})
                available_replicas = status.get("availableReplicas")
                replicas = status.get("replicas")
                
                if available_replicas is not None and available_replicas == replicas:
                    logger.info(f"Deployment {name} is ready")
                    return True
            
            time.sleep(5)
        
        logger.error(f"Timed out waiting for deployment {name} to be ready")
        return False
    
    def get_deployment_status(self, deployment_id: str, namespace: str = None) -> Dict[str, Any]:
        """
        Get the status of a deployment by searching all namespaces using either the deployment name or the deployment-id label.

        Args:
            deployment_id: Name or deployment-id label of the deployment
            namespace: Optional namespace to filter deployments

        Returns:
            Dict containing the deployment status information for each namespace
        """
        try:
            found = []
            # If namespace is provided, search for deployment by label in that namespace
            if namespace:
                # Try by name first
                cmd = ["get", "deployment", deployment_id, "-n", namespace, "-o", "json"]
                logging.info(f"Executing command: {' '.join(cmd)}")
                deployment_result = self.connector.run_command(cmd)
                if deployment_result["success"]:
                    deployment = json.loads(deployment_result["output"])
                    found = [deployment]
                # If not found by name, try by label
                if not found:
                    cmd = ["get", "deployments", "-n", namespace, "-l", f"deployment-id={deployment_id}", "-o", "json"]
                    logging.info(f"Executing command: {' '.join(cmd)}")
                    deployment_result = self.connector.run_command(cmd)
                    if deployment_result["success"]:
                        deployments = json.loads(deployment_result["output"])
                        found = deployments.get("items", [])
                if not found:
                    logging.error(f"Deployment with name or label 'deployment-id={deployment_id}' not found in namespace '{namespace}'.")
                    return {"success": False, "message": f"Deployment with name or label 'deployment-id={deployment_id}' not found in namespace '{namespace}'."}
            else:
                # Get all deployments in all namespaces
                cmd = ["get", "deployments", "--all-namespaces", "-o", "json"]
                logging.info(f"Executing command: {' '.join(cmd)}")
                deployments_result = self.connector.run_command(cmd)
                if not deployments_result["success"]:
                    logging.error(f"Failed to get deployments: {deployments_result.get('error', 'Unknown error')}")
                    return {"success": False, "message": f"Failed to get deployments: {deployments_result.get('error', 'Unknown error')}"}
                deployments = json.loads(deployments_result["output"])
                # Find all deployments matching the name or deployment-id label
                found = [item for item in deployments.get("items", []) if item.get("metadata", {}).get("name") == deployment_id or item.get("metadata", {}).get("labels", {}).get("deployment-id") == deployment_id]
                if not found:
                    logging.error(f"Deployment '{deployment_id}' not found in any namespace.")
                    return {"success": False, "message": f"Deployment '{deployment_id}' not found in any namespace."}
            
            all_statuses = []
            for deployment in found:
                deployment_namespace = deployment.get("metadata", {}).get("namespace", "default")
                # Always use the real deployment name from metadata for associated resources
                real_deployment_name = deployment.get("metadata", {}).get("name", "")

                # Get associated service - try multiple naming patterns
                service = None
                service_names = [
                    f"{real_deployment_name}-service",
                    real_deployment_name,
                    f"{real_deployment_name}-svc"
                ]
                
                # First try to get service by label selector
                cmd = ["get", "service", "-l", f"deployment-id={real_deployment_name}-{deployment_id}", "-n", deployment_namespace, "-o", "json"]
                logging.info(f"Executing command: {' '.join(cmd)}")
                service_result = self.connector.run_command(cmd)
                if service_result["success"]:
                    services = json.loads(service_result["output"])
                    if services.get("items"):
                        service = services["items"][0]
                        logging.info(f"Found service by label selector: {service.get('metadata', {}).get('name')}")
                
                # If not found by label, try the naming patterns
                if not service:
                    for service_name in service_names:
                        try:
                            cmd = ["get", "service", service_name, "-n", deployment_namespace, "-o", "json"]
                            logging.info(f"Executing command: {' '.join(cmd)}")
                            service_result = self.connector.run_command(cmd)
                            if service_result["success"]:
                                candidate_service = json.loads(service_result["output"])
                                # Only accept if the service name matches one of the expected names
                                if candidate_service.get("metadata", {}).get("name") in service_names:
                                    service = candidate_service
                                    logging.info(f"Found service: {service_name}")
                                    break
                        except Exception as e:
                            logging.debug(f"Service {service_name} not found: {str(e)}")
                            continue
                # If still not found, do not fallback to any other service (e.g., 'kubernetes')

                # Get associated HPA - try keda-hpa-<name> and <name>
                hpa = None
                hpa_names = [f"keda-hpa-{real_deployment_name}", real_deployment_name]
                for hpa_name in hpa_names:
                    try:
                        cmd = ["get", "hpa", hpa_name, "-n", deployment_namespace, "-o", "json"]
                        logging.info(f"Executing command: {' '.join(cmd)}")
                        hpa_result = self.connector.run_command(cmd)
                        if hpa_result["success"]:
                            hpa = json.loads(hpa_result["output"])
                            logging.info(f"Found HPA: {hpa_name}")
                            logging.debug(f"HPA data: {json.dumps(hpa, indent=2)}")
                            break
                        else:
                            logging.error(f"Failed to get HPA: {hpa_result.get('error', 'Unknown error')}")
                    except Exception as e:
                        logging.error(f"Error getting HPA: {str(e)}")

                # Get associated KEDA ScaledObject - use exact name
                scaled_object = None
                try:
                    cmd = ["get", "scaledobject", real_deployment_name, "-n", deployment_namespace, "-o", "json"]
                    logging.info(f"Executing command: {' '.join(cmd)}")
                    scaled_obj_result = self.connector.run_command(cmd)
                    if scaled_obj_result["success"]:
                        scaled_object = json.loads(scaled_obj_result["output"])
                        logging.info(f"Found ScaledObject: {real_deployment_name}")
                        logging.debug(f"ScaledObject data: {json.dumps(scaled_object, indent=2)}")
                    else:
                        logging.error(f"Failed to get ScaledObject: {scaled_obj_result.get('error', 'Unknown error')}")
                except Exception as e:
                    logging.error(f"Error getting ScaledObject: {str(e)}")

                # Get associated pods
                app_name = deployment.get("metadata", {}).get("name")
                cmd = ["get", "pods", "-n", deployment_namespace, "-l", f"app={app_name}", "-o", "json"]
                logging.info(f"Debug Executing command: {' '.join(cmd)}")
                pods_result = self.connector.run_command(cmd)
                pods = json.loads(pods_result["output"]) if pods_result["success"] else {"items": []}

                # Get pod metrics
                metrics = {}
                try:
                    selector = f"app={app_name}"
                    cmd = ["get", "pods", "-n", deployment_namespace, "-l", selector, "-o", "jsonpath={.items[*].metadata.name}"]
                    pod_names_result = self.connector.run_command(cmd)
                    if pod_names_result["success"] and pod_names_result["output"].strip():
                        pod_names = pod_names_result["output"].split()
                        for pod_name in pod_names:
                            cmd = ["top", "pod", pod_name, "-n", deployment_namespace, "--no-headers"]
                            top_result = self.connector.run_command(cmd)
                            if top_result["success"]:
                                # Parse CPU and memory usage
                                parts = top_result["output"].split()
                                if len(parts) >= 3:
                                    metrics[pod_name] = {
                                        "cpu": parts[1],
                                        "memory": parts[2]
                                    }
                except Exception as e:
                    logging.error(f"Error getting pod metrics: {str(e)}")

                # Get pod events for non-running pods
                events = []
                for pod in pods.get("items", []):
                    pod_name = pod.get("metadata", {}).get("name", "")
                    pod_phase = pod.get("status", {}).get("phase", "")
                    
                    if pod_phase != "Running":
                        cmd = ["get", "events", "-n", deployment_namespace, "--field-selector", f"involvedObject.name={pod_name}", "-o", "json"]
                        logging.info(f"Executing command: {' '.join(cmd)}")
                        events_result = self.connector.run_command(cmd)
                        if events_result["success"]:
                            pod_events = json.loads(events_result["output"])
                            events.extend(pod_events.get("items", []))

                status = {
                    "success": True,
                    "message": f"Deployment '{deployment_id}' found in namespace '{deployment_namespace}'",
                    "namespace": deployment_namespace,
                    "deployment": deployment,
                    "service": service,
                    "hpa": hpa,
                    "scaled_object": scaled_object,
                    "pods": pods,
                    "metrics": metrics,
                    "events": events
                }
                status_summary = self.get_deployment_status_summary(status)
                all_statuses.append(status_summary)
            
            if not all_statuses:
                return {"success": False, "message": f"Deployment with name or label 'deployment-id={deployment_id}' not found in namespace '{namespace}'."}
            
            return {"success": True, "deployments": all_statuses}
        except Exception as e:
            logging.error(f"Error getting deployment status: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def get_created_resources_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a concise summary of created resources from deployment result.
        
        Args:
            result: The full deployment result dictionary
            
        Returns:
            Dictionary containing summarized resource information
        """
        summary = {
            "deployment_id": result.get("deployment_id", ""),
            "resources": [],
            "service_endpoints": [],
            "pod_status": {}
        }
        
        # Add deployment info if exists
        if result.get("deployment") and isinstance(result["deployment"], dict):
            name = result["deployment"].get("metadata", {}).get("name", "unknown")
            summary["resources"].append({
                "kind": "Deployment",
                "name": name,
                "namespace": result["deployment"].get("metadata", {}).get("namespace", "default")
            })
            
            # Get pod status information
            summary["pod_status"] = self._get_pod_status(name, 
                result["deployment"].get("metadata", {}).get("namespace", "default"))
        
        # Add service info if exists
        if result.get("service") and isinstance(result["service"], dict):
            service_data = result["service"]
            name = service_data.get("metadata", {}).get("name", "unknown")
            namespace = service_data.get("metadata", {}).get("namespace", "default")
            service_type = service_data.get("spec", {}).get("type", "ClusterIP")
            
            summary["resources"].append({
                "kind": "Service",
                "name": name,
                "namespace": namespace,
                "type": service_type
            })
            
            # Add service endpoint information
            endpoint = self._get_service_endpoint(name, namespace, service_type)
            if endpoint:
                summary["service_endpoints"].append(endpoint)
        
        # Add HPA info if exists
        if result.get("hpa") and isinstance(result["hpa"], dict):
            summary["resources"].append({
                "kind": "HorizontalPodAutoscaler",
                "name": result["hpa"].get("metadata", {}).get("name", "unknown"),
                "namespace": result["hpa"].get("metadata", {}).get("namespace", "default"),
                "min_replicas": result["hpa"].get("spec", {}).get("minReplicas", 1),
                "max_replicas": result["hpa"].get("spec", {}).get("maxReplicas", 1),
            })
        
        # Add KEDA ScaledObject info if exists
        if result.get("scaled_object") and isinstance(result["scaled_object"], dict):
            summary["resources"].append({
                "kind": "ScaledObject",
                "name": result["scaled_object"].get("metadata", {}).get("name", "unknown"),
                "namespace": result["scaled_object"].get("metadata", {}).get("namespace", "default"),
                "min_replicas": result["scaled_object"].get("spec", {}).get("minReplicaCount", 1),
                "max_replicas": result["scaled_object"].get("spec", {}).get("maxReplicaCount", 1),
            })
            
        return summary
    
    def get_deployment_status_summary(self, status: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a concise summary of deployment status.
        
        Args:
            status: The full deployment status dictionary
            
        Returns:
            Dictionary containing summarized status information
        """
        summary = {
            "success": status.get("success", False),
            "message": status.get("message", ""),
            "deployment_id": "",
            "resources": [],
            "service_endpoints": [],
            "pod_status": {
                "total": 0,
                "ready": 0,
                "status_breakdown": {}
            },
            "metrics": {},
            "events": []
        }
        
        # Add deployment info if exists
        if status.get("deployment") and isinstance(status["deployment"], dict):
            deployment = status["deployment"]
            name = deployment.get("metadata", {}).get("name", "unknown")
            namespace = deployment.get("metadata", {}).get("namespace", "default")
            
            # Set deployment ID
            summary["deployment_id"] = f"{namespace}/{name}"
            
            # Add to resources list
            summary["resources"].append({
                "kind": "Deployment",
                "name": name,
                "namespace": namespace
            })
            
            # Get deployment status details
            replicas = deployment.get("status", {}).get("replicas", 0)
            available_replicas = deployment.get("status", {}).get("availableReplicas", 0)
            
            # Get actual pod count from pods list
            pod_items = status.get("pods", {}).get("items", [])
            actual_pod_count = len(pod_items)
            
            # Count ready pods from pod list
            ready_count = 0
            for pod in pod_items:
                container_statuses = pod.get("status", {}).get("containerStatuses", [])
                if container_statuses and all(c.get("ready", False) for c in container_statuses):
                    ready_count += 1
            
            summary["pod_status"]["total"] = actual_pod_count
            summary["pod_status"]["ready"] = ready_count
        
        # Add service info if exists
        if status.get("service") and isinstance(status["service"], dict):
            service = status["service"]
            service_name = service.get("metadata", {}).get("name", "unknown")
            service_type = service.get("spec", {}).get("type", "ClusterIP")
            namespace = service.get("metadata", {}).get("namespace", "default")
            
            # Add to resources list
            summary["resources"].append({
                "kind": "Service",
                "name": service_name,
                "namespace": namespace,
                "type": service_type
            })
            
            # Get service endpoint using _get_service_endpoint
            endpoint = self._get_service_endpoint(service_name, namespace, service_type)
            if endpoint and endpoint.get("url"):
                summary["service_endpoints"].append(endpoint["url"])
            elif endpoint and endpoint.get("status"):
                summary["service_endpoints"].append(endpoint["status"])
        
        # Add HPA info if exists
        if status.get("hpa") and isinstance(status["hpa"], dict):
            hpa = status["hpa"]
            hpa_name = hpa.get("metadata", {}).get("name", "unknown")
            hpa_namespace = hpa.get("metadata", {}).get("namespace", "default")
            
            # Add to resources list
            summary["resources"].append({
                "kind": "HorizontalPodAutoscaler",
                "name": hpa_name,
                "namespace": hpa_namespace,
                "min_replicas": hpa.get("spec", {}).get("minReplicas", 1),
                "max_replicas": hpa.get("spec", {}).get("maxReplicas", 1),
                "current_replicas": hpa.get("status", {}).get("currentReplicas", 0),
                "target_metrics": [
                    {
                        "type": metric.get("type"),
                        "resource": metric.get("resource", {}).get("name"),
                        "target": metric.get("resource", {}).get("target", {}).get("averageUtilization")
                    }
                    for metric in hpa.get("spec", {}).get("metrics", [])
                ]
            })
        
        # Add KEDA ScaledObject info if exists
        if status.get("scaled_object") and isinstance(status["scaled_object"], dict):
            scaled_obj = status["scaled_object"]
            scaled_obj_name = scaled_obj.get("metadata", {}).get("name", "unknown")
            scaled_obj_namespace = scaled_obj.get("metadata", {}).get("namespace", "default")
            
            # Add to resources list
            summary["resources"].append({
                "kind": "ScaledObject",
                "name": scaled_obj_name,
                "namespace": scaled_obj_namespace,
                "min_replicas": scaled_obj.get("spec", {}).get("minReplicaCount", 1),
                "max_replicas": scaled_obj.get("spec", {}).get("maxReplicaCount", 1),
                "triggers": [
                    {
                        "type": trigger.get("type"),
                        "metadata": trigger.get("metadata", {})
                    }
                    for trigger in scaled_obj.get("spec", {}).get("triggers", [])
                ]
            })
        
        # Add pod status details
        if status.get("pods") and isinstance(status["pods"], dict):
            pod_items = status["pods"].get("items", [])
            logging.debug(f"Pod items retrieved: {json.dumps(pod_items, indent=2)}")
            
            # Count pods by status and ready state
            status_counts = {}
            ready_count = 0
            for pod in pod_items:
                pod_status = pod.get("status", {}).get("phase", "Unknown")
                logging.debug(f"Pod {pod.get('metadata', {}).get('name', 'unknown')} status: {pod_status}")
                
                # Update status counts
                if pod_status not in status_counts:
                    status_counts[pod_status] = 0
                status_counts[pod_status] += 1
                
                # Count ready pods
                container_statuses = pod.get("status", {}).get("containerStatuses", [])
                if container_statuses and all(c.get("ready", False) for c in container_statuses):
                    ready_count += 1
            
            # Update pod status breakdown
            summary["pod_status"]["status_breakdown"] = status_counts
            summary["pod_status"]["total"] = len(pod_items)
            summary["pod_status"]["ready"] = ready_count
        
        # Add pod metrics
        summary["metrics"] = status.get("metrics", {})
        
        # Add events information
        if status.get("events"):
            # Sort events by last timestamp
            sorted_events = sorted(
                status["events"],
                key=lambda x: x.get("lastTimestamp", ""),
                reverse=True
            )
            # Take only the most recent 5 events
            summary["events"] = sorted_events[:5]
        
        return summary
    
    def _create_deployment_object(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a deployment object from the provided configuration.

        Args:
            config: Configuration dictionary for the deployment

        Returns:
            Dict representing the deployment object
        """
        # Extract metadata
        name = config["name"]
        namespace = config.get("namespace", "default")
        labels = config.get("labels", {})
        annotations = config.get("annotations", {})

        # Define deployment object
        deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": name,
                "namespace": namespace,
                "labels": labels,
                "annotations": annotations,
            },
            "spec": {
                "replicas": config.get("replicas", 1),
                "selector": {
                    "matchLabels": {
                        "app": name,
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": name,
                            **labels,
                        }
                    },
                    "spec": {
                        "containers": [{
                            "name": name,
                            "image": config["image"],
                            "imagePullPolicy": "Always" if "latest" in config["image"] else "IfNotPresent",
                            "ports": [{"containerPort": port} for port in config.get("ports", [80])],
                            "resources": {
                                "requests": {
                                    "cpu": config.get("cpu_request", "100m"),
                                    "memory": config.get("memory_request", "128Mi"),
                                },
                                "limits": {
                                    "cpu": config.get("cpu_limit", "500m"),
                                    "memory": config.get("memory_limit", "512Mi"),
                                }
                            },
                            "env": [{"name": key, "value": value} for key, value in config.get("env_vars", {}).items()]
                        }]
                    }
                }
            }
        }
        
        return deployment

    def _create_service_object(
        self,
        name: str,
        selector: Dict[str, str],
        ports: List[Dict[str, Any]],
        service_type: str = "ClusterIP"
    ) -> Dict[str, Any]:
        """
        Create a service object from the provided parameters.

        Args:
            name: Name of the service
            selector: Selector for the service
            ports: List of ports for the service
            service_type: Type of the service (ClusterIP, NodePort, LoadBalancer)

        Returns:
            Dict representing the service object
        """
        # Define service object
        service = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": name,
                "labels": selector,
            },
            "spec": {
                "selector": selector,
                "ports": ports,
                "type": service_type
            }
        }
        
        return service

    def _create_hpa_object(
        self,
        name: str,
        deployment_name: str,
        min_replicas: int,
        max_replicas: int,
        target_cpu_percentage: int
    ) -> Dict[str, Any]:
        """
        Create a Horizontal Pod Autoscaler object from the provided parameters.

        Args:
            name: Name of the HPA
            deployment_name: Name of the deployment to scale
            min_replicas: Minimum number of replicas
            max_replicas: Maximum number of replicas
            target_cpu_percentage: Target CPU utilization percentage

        Returns:
            Dict representing the HPA object
        """
        # Define HPA object
        hpa = {
            "apiVersion": "autoscaling/v2",
            "kind": "HorizontalPodAutoscaler",
            "metadata": {
                "name": name,
            },
            "spec": {
                "scaleTargetRef": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "name": deployment_name
                },
                "minReplicas": min_replicas,
                "maxReplicas": max_replicas,
                "metrics": [
                    {
                        "type": "Resource",
                        "resource": {
                            "name": "cpu",
                            "target": {
                                "type": "Utilization",
                                "averageUtilization": target_cpu_percentage
                            }
                        }
                    }
                ]
            }
        }
        
        return hpa
    
    def _get_service_endpoint(self, service_name: str, namespace: str = "default", service_type: str = "ClusterIP") -> Dict[str, str]:
        """
        Get endpoint information for a service.
        
        Args:
            service_name: Name of the service
            namespace: Kubernetes namespace
            service_type: Type of the service (ClusterIP, LoadBalancer, NodePort)
            
        Returns:
            Dictionary containing service endpoint information
        """
        endpoint = {
            "name": service_name,
            "type": service_type,
            "url": None
        }
        
        try:
            # Get service information
            cmd = ["get", "service", service_name, "-n", namespace, "-o", "json"]
            service_result = self.connector.run_command(cmd)
            
            if not service_result["success"]:
                endpoint["status"] = f"Error: Service not found"
                return endpoint
                
            service = json.loads(service_result["output"])
            
            if service_type == "LoadBalancer":
                # Fetch external IP for LoadBalancer
                ingress = service.get("status", {}).get("loadBalancer", {}).get("ingress", [])
                if ingress:
                    if ingress[0].get("ip"):
                        port = service.get("spec", {}).get("ports", [{}])[0].get("port", 80)
                        endpoint["url"] = f"http://{ingress[0]['ip']}:{port}"
                    elif ingress[0].get("hostname"):
                        port = service.get("spec", {}).get("ports", [{}])[0].get("port", 80)
                        endpoint["url"] = f"http://{ingress[0]['hostname']}:{port}"
                else:
                    endpoint["url"] = "pending"
                    endpoint["status"] = "External IP pending"
                    
            elif service_type == "NodePort":
                # Fetch NodePort information
                ports = service.get("spec", {}).get("ports", [])
                if ports:
                    node_port = ports[0].get("nodePort")
                    if node_port:
                        # Try to get a node IP to construct the URL
                        node_cmd = ["get", "nodes", "-o", "json"]
                        node_result = self.connector.run_command(node_cmd)
                        if node_result["success"]:
                            nodes = json.loads(node_result["output"])
                            if nodes.get("items"):
                                for addr in nodes["items"][0].get("status", {}).get("addresses", []):
                                    if addr.get("type") == "ExternalIP":
                                        endpoint["url"] = f"http://{addr['address']}:{node_port}"
                                        break
                                if not endpoint["url"] and nodes["items"][0].get("status", {}).get("addresses"):
                                    # Fallback to first available address
                                    addr = nodes["items"][0]["status"]["addresses"][0]
                                    endpoint["url"] = f"http://{addr['address']}:{node_port}"
                        if not endpoint["url"]:
                            endpoint["url"] = f"http://NODE_IP:{node_port}"
                            endpoint["status"] = "Use any node IP"
                        
            elif service_type == "ClusterIP":
                # Get ClusterIP information
                cluster_ip = service.get("spec", {}).get("clusterIP")
                ports = service.get("spec", {}).get("ports", [])
                if cluster_ip and ports:
                    port = ports[0].get("port", 80)
                    endpoint["url"] = f"http://{cluster_ip}:{port}"
                    endpoint["status"] = "Only accessible within cluster"
        except Exception as e:
            logging.error(f"Error getting service endpoint: {str(e)}")
            endpoint["status"] = f"Error: {str(e)}"
            
        return endpoint
        
    def _get_pod_status(self, deployment_name: str, namespace: str = "default") -> Dict[str, Any]:
        """
        Get status information about pods in a deployment.
        Args:
            deployment_name: Name of the deployment
            namespace: Kubernetes namespace
        Returns:
            Dictionary containing pod status information
        """
        status = {
            "total": 0,
            "ready": 0,
            "running": 0,
            "pending": 0,
            "failed": 0,
            "pods": []
        }
        try:
            # Get deployment to check desired replicas and deployment-id
            cmd = ["get", "deployment", deployment_name, "-n", namespace, "-o", "json"]
            deployment_result = self.connector.run_command(cmd)
            if not deployment_result["success"]:
                status["error"] = deployment_result.get("error", "Failed to get deployment")
                return status
            deployment = json.loads(deployment_result["output"])
            status["desired"] = deployment.get("spec", {}).get("replicas", 1)
            
            # Get deployment-id and app name from labels
            deployment_id = deployment.get("metadata", {}).get("labels", {}).get("deployment-id")
            app_name = deployment.get("metadata", {}).get("name")
            print("Debug - deployment_id", deployment_id)
            if not deployment_id:
                status["error"] = "Deployment ID not found in labels"
                return status
            
            # List pods with both deployment-id and app labels
            cmd = ["get", "pods", "-n", namespace, "-l", f"deployment-id={deployment_id},app={app_name}", "-o", "json"]
            pods_result = self.connector.run_command(cmd)
            if not pods_result["success"]:
                status["error"] = pods_result.get("error", "Failed to get pods")
                return status
            pods = json.loads(pods_result["output"])
            status["total"] = len(pods.get("items", []))
            
            # Process individual pod information
            for pod in pods.get("items", []):
                pod_status = {
                    "name": pod.get("metadata", {}).get("name", ""),
                    "status": pod.get("status", {}).get("phase", "Unknown"),
                    "ready": False,
                    "restarts": 0,
                    "age": ""
                }
                # Check container statuses for ready state
                container_statuses = pod.get("status", {}).get("containerStatuses", [])
                if container_statuses:
                    pod_status["ready"] = all(c.get("ready", False) for c in container_statuses)
                    pod_status["restarts"] = sum(c.get("restartCount", 0) for c in container_statuses)
                # Count by status
                if pod_status["status"] == "Running":
                    status["running"] += 1
                    if pod_status["ready"]:
                        status["ready"] += 1
                elif pod_status["status"] == "Pending":
                    status["pending"] += 1
                elif pod_status["status"] == "Failed":
                    status["failed"] += 1
                # Calculate age
                creation_ts = pod.get("metadata", {}).get("creationTimestamp")
                if creation_ts:
                    from datetime import datetime, timezone
                    # Handle timezone offset in timestamp
                    if "+" in creation_ts:
                        created = datetime.strptime(creation_ts, "%Y-%m-%dT%H:%M:%S%z")
                    else:
                        created = datetime.strptime(creation_ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    age_delta = now - created
                    days = age_delta.days
                    hours, remainder = divmod(age_delta.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    if days > 0:
                        pod_status["age"] = f"{days}d{hours}h"
                    elif hours > 0:
                        pod_status["age"] = f"{hours}h{minutes}m"
                    else:
                        pod_status["age"] = f"{minutes}m"
                status["pods"].append(pod_status)
        except Exception as e:
            logging.error(f"Error getting pod status: {str(e)}")
            status["error"] = str(e)
        return status
    
    def _get_service_endpoints(self, service_data: Dict[str, Any]) -> List[str]:
        """
        Extract endpoint information from a service object.
        
        Args:
            service_data: Kubernetes service object data
            
        Returns:
            List of endpoint strings
        """
        endpoints = []
        
        if not service_data:
            return endpoints
            
        name = service_data.get("metadata", {}).get("name", "unknown")
        namespace = service_data.get("metadata", {}).get("namespace", "default")
        service_type = service_data.get("spec", {}).get("type", "ClusterIP")
        ports = service_data.get("spec", {}).get("ports", [])
        
        # Handle different service types
        if service_type == "LoadBalancer":
            # Get external IP if available
            ingress = service_data.get("status", {}).get("loadBalancer", {}).get("ingress", [])
            if ingress:
                for ing in ingress:
                    ip = ing.get("ip")
                    hostname = ing.get("hostname")
                    if ip:
                        for port in ports:
                            port_num = port.get("port")
                            port_name = port.get("name", "")
                            protocol = port.get("protocol", "TCP")
                            endpoint = f"{ip}:{port_num} ({port_name}, {protocol})"
                            endpoints.append(endpoint)
                    elif hostname:
                        for port in ports:
                            port_num = port.get("port")
                            port_name = port.get("name", "")
                            protocol = port.get("protocol", "TCP")
                            endpoint = f"{hostname}:{port_num} ({port_name}, {protocol})"
                            endpoints.append(endpoint)
            else:
                # If external IP not yet assigned
                endpoints.append(f"LoadBalancer IP pending for {namespace}/{name}")
                
        elif service_type == "NodePort":
            # List node ports
            for port in ports:
                node_port = port.get("nodePort")
                port_name = port.get("name", "")
                protocol = port.get("protocol", "TCP")
                if node_port:
                    endpoints.append(f"NodePort {node_port} ({port_name}, {protocol})")
                    
        elif service_type == "ExternalName":
            # External name services
            external_name = service_data.get("spec", {}).get("externalName")
            if external_name:
                endpoints.append(f"ExternalName: {external_name}")
                
        else:  # ClusterIP
            cluster_ip = service_data.get("spec", {}).get("clusterIP")
            if cluster_ip and cluster_ip != "None":
                for port in ports:
                    port_num = port.get("port")
                    port_name = port.get("name", "")
                    protocol = port.get("protocol", "TCP")
                    endpoints.append(f"ClusterIP: {cluster_ip}:{port_num} ({port_name}, {protocol})")
            
        return endpoints
