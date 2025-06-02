"""
Test cases for CLI commands
"""
import os
import pytest
from unittest.mock import Mock, patch
from k8s_tool.cli.cli import main

@pytest.mark.usefixtures("setup_test_env")
class TestCLI:
    def setup_method(self):
        """Setup method to verify kubeconfig is set."""
        print(f"KUBECONFIG environment variable: {os.environ.get('KUBECONFIG')}")

    @patch('k8s_tool.cli.cli.InstallationManager')
    def test_install_helm_command(self, mock_installation_manager):
        """Test install helm command"""
        mock_manager = Mock()
        mock_installation_manager.return_value = mock_manager
        mock_manager.install_helm.return_value = {
            "success": True,
            "message": "Helm installed successfully",
            "version": "v3.16.3"
        }

        with patch('sys.argv', ['k8s-tool', '--kubeconfig', os.environ['KUBECONFIG'], 'install', 'helm']), \
             patch('sys.exit') as mock_exit:
            main()
            mock_manager.install_helm.assert_called_once()
            mock_exit.assert_called_once_with(0)

    @patch('k8s_tool.cli.cli.InstallationManager')
    def test_install_keda_command(self, mock_installation_manager):
        """Test install keda command"""
        mock_manager = Mock()
        mock_installation_manager.return_value = mock_manager
        mock_manager.install_keda.return_value = {
            "success": True,
            "message": "KEDA installed successfully",
            "version": "v2.12.0"
        }

        with patch('sys.argv', ['k8s-tool', '--kubeconfig', os.environ['KUBECONFIG'], 'install', 'keda']), \
             patch('sys.exit') as mock_exit:
            main()
            mock_manager.install_keda.assert_called_once()
            mock_exit.assert_called_once_with(0)

    @patch('k8s_tool.cli.cli.DeploymentManager')
    def test_deployment_create_command(self, mock_deployment_manager):
        """Test deployment create command"""
        mock_manager = Mock()
        mock_deployment_manager.return_value = mock_manager
        mock_manager.create_deployment.return_value = {
            "success": True,
            "message": "Deployment created successfully",
            "deployment_id": "test-app-123"
        }

        with patch('sys.argv', ['k8s-tool', '--kubeconfig', os.environ['KUBECONFIG'], 'deployment', 'create', '--name', 'test-app', '--image', 'nginx:latest']), \
             patch('sys.exit') as mock_exit:
            main()
            mock_manager.create_deployment.assert_called_once()
            mock_exit.assert_called_once_with(0)

    @patch('k8s_tool.cli.cli.DeploymentManager')
    def test_deployment_create_with_keda(self, mock_deployment_manager):
        """Test deployment create with KEDA"""
        mock_manager = Mock()
        mock_deployment_manager.return_value = mock_manager
        mock_manager.create_deployment.return_value = {
            "success": True,
            "message": "Deployment created successfully",
            "deployment_id": "test-app-123"
        }

        with patch('sys.argv', ['k8s-tool', '--kubeconfig', os.environ['KUBECONFIG'], 'deployment', 'create', 
                               '--name', 'test-app', 
                               '--image', 'nginx:latest',
                               '--enable-keda',
                               '--keda-cpu-trigger',
                               '--keda-cpu-threshold', '80']), \
             patch('sys.exit') as mock_exit:
            main()
            mock_manager.create_deployment.assert_called_once()
            mock_exit.assert_called_once_with(0) 