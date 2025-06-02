"""
Test cases for DeploymentManager class
"""
import pytest
from unittest.mock import Mock, patch
from k8s_tool.deployment.manager import DeploymentManager

@pytest.mark.usefixtures("setup_test_env")
class TestDeploymentManager:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.connector = Mock()
        self.manager = DeploymentManager(self.connector)

    def test_create_deployment_basic(self):
        """Test basic deployment creation"""
        self.connector.run_command.return_value = True
        with patch.object(self.manager, '_create_deployment_resource') as mock_create, \
             patch.object(self.manager, '_create_service_resource') as mock_service, \
             patch.object(self.manager, '_wait_for_deployment_ready') as mock_wait:
            mock_create.return_value = {
                "success": True,
                "message": "Deployment created successfully",
                "resource": {"name": "test-app"}
            }
            mock_service.return_value = {
                "success": True,
                "message": "Service created successfully",
                "resource": {"name": "test-app"}
            }
            mock_wait.return_value = True
            result = self.manager.create_deployment(
                name="test-app",
                image="nginx:latest",
                replicas=1
            )
            assert result["success"]
            assert "deployment_id" in result
            assert "message" in result
            assert "deployment" in result

    def test_create_deployment_with_service(self):
        """Test deployment creation with service"""
        self.connector.run_command.return_value = True
        with patch.object(self.manager, '_create_deployment_resource') as mock_create_deployment, \
             patch.object(self.manager, '_create_service_resource') as mock_create_service, \
             patch.object(self.manager, '_wait_for_deployment_ready') as mock_wait:
            mock_create_deployment.return_value = {
                "success": True,
                "message": "Deployment created successfully",
                "resource": {"name": "test-app"}
            }
            mock_create_service.return_value = {
                "success": True,
                "message": "Service created successfully",
                "resource": {"name": "test-app"}
            }
            mock_wait.return_value = True
            result = self.manager.create_deployment(
                name="test-app",
                image="nginx:latest",
                service_type="ClusterIP",
                ports=[80]
            )
            assert result["success"]
            assert "deployment_id" in result
            assert "message" in result
            assert "deployment" in result
            assert "service" in result

    def test_create_deployment_with_hpa(self):
        """Test deployment creation with HPA"""
        self.connector.run_command.return_value = True
        with patch.object(self.manager, '_create_deployment_resource') as mock_create_deployment, \
             patch.object(self.manager, '_create_hpa_resource') as mock_create_hpa, \
             patch.object(self.manager, '_create_service_resource') as mock_create_service, \
             patch.object(self.manager, '_wait_for_deployment_ready') as mock_wait:
            mock_create_deployment.return_value = {
                "success": True,
                "message": "Deployment created successfully",
                "resource": {"name": "test-app"}
            }
            mock_create_hpa.return_value = {
                "success": True,
                "message": "HPA created successfully",
                "resource": {"name": "test-app"}
            }
            mock_create_service.return_value = {
                "success": True,
                "message": "Service created successfully",
                "resource": {"name": "test-app"}
            }
            mock_wait.return_value = True
            result = self.manager.create_deployment(
                name="test-app",
                image="nginx:latest",
                autoscaling_enabled=True,
                cpu_target_percentage=80
            )
            assert result["success"]
            assert "deployment_id" in result
            assert "message" in result
            assert "deployment" in result
            assert "hpa" in result

    def test_create_deployment_with_keda(self):
        """Test deployment creation with KEDA"""
        self.connector.run_command.return_value = True
        with patch.object(self.manager, '_create_deployment_resource') as mock_create_deployment, \
             patch.object(self.manager, '_create_keda_scaled_object') as mock_create_keda, \
             patch.object(self.manager, '_create_service_resource') as mock_create_service, \
             patch.object(self.manager, '_wait_for_deployment_ready') as mock_wait:
            mock_create_deployment.return_value = {
                "success": True,
                "message": "Deployment created successfully",
                "resource": {"name": "test-app"}
            }
            mock_create_keda.return_value = {
                "success": True,
                "message": "KEDA ScaledObject created successfully",
                "resource": {"name": "test-app"}
            }
            mock_create_service.return_value = {
                "success": True,
                "message": "Service created successfully",
                "resource": {"name": "test-app"}
            }
            mock_wait.return_value = True
            result = self.manager.create_deployment(
                name="test-app",
                image="nginx:latest",
                keda_enabled=True,
                keda_triggers=[{
                    "type": "cpu",
                    "metadata": {
                        "type": "Utilization",
                        "value": "80"
                    }
                }]
            )
            assert result["success"]
            assert "deployment_id" in result
            assert "message" in result
            assert "deployment" in result
            assert "scaled_object" in result

    def test_create_deployment_with_resources(self):
        """Test deployment creation with resource limits"""
        self.connector.run_command.return_value = True
        with patch.object(self.manager, '_create_deployment_resource') as mock_create, \
             patch.object(self.manager, '_create_service_resource') as mock_service, \
             patch.object(self.manager, '_wait_for_deployment_ready') as mock_wait:
            mock_create.return_value = {
                "success": True,
                "message": "Deployment created successfully",
                "resource": {"name": "test-app"}
            }
            mock_service.return_value = {
                "success": True,
                "message": "Service created successfully",
                "resource": {"name": "test-app"}
            }
            mock_wait.return_value = True
            result = self.manager.create_deployment(
                name="test-app",
                image="nginx:latest",
                resource_limits={
                    "cpu": "500m",
                    "memory": "512Mi"
                }
            )
            assert result["success"]
            assert "deployment_id" in result
            assert "message" in result
            assert "deployment" in result 