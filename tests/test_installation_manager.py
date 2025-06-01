"""
Test cases for InstallationManager class
"""
import unittest
from unittest.mock import Mock, patch
from k8s_tool.installation.manager import InstallationManager

class TestInstallationManager(unittest.TestCase):
    def setUp(self):
        self.connector = Mock()
        self.manager = InstallationManager(self.connector)

    def test_install_helm(self):
        """Test Helm installation"""
        self.connector.run_command.return_value = True
        with patch.object(self.manager, '_check_helm_installed') as mock_check:
            mock_check.return_value = (True, "v3.16.3")
            result = self.manager.install_helm()
            self.assertTrue(result["success"])
            self.assertEqual(result["version"], "v3.16.3")
            self.assertIn("message", result)

    def test_install_keda(self):
        """Test KEDA installation"""
        self.connector.run_command.return_value = True
        with patch.object(self.manager, '_check_keda_installed') as mock_check, \
             patch.object(self.manager, '_ensure_namespace_exists') as mock_ns, \
             patch.object(self.manager, '_verify_keda_installation') as mock_verify, \
             patch('subprocess.run') as mock_subproc:
            # First call: not installed, Second call: installed
            mock_check.side_effect = [(False, ""), (True, "v2.12.0")]
            mock_ns.return_value = None
            mock_verify.return_value = True
            mock_subproc.return_value = Mock(returncode=0)
            result = self.manager.install_keda()
            self.assertTrue(result["success"])
            self.assertEqual(result["version"], "v2.12.0")
            self.assertIn("message", result)

    def test_install_metrics_server(self):
        """Test metrics-server installation"""
        self.connector.run_command.return_value = {"success": True}
        self.connector.get_api_version = Mock(return_value="v1.27.0")
        with patch.object(self.manager, '_check_metrics_server_installed') as mock_check, \
             patch.object(self.manager, '_verify_metrics_server_installation') as mock_verify, \
             patch.object(self.manager, '_find_metrics_server_namespace') as mock_ns, \
             patch('subprocess.run') as mock_subproc:
            # First call: not installed, Second call: installed
            mock_check.side_effect = [(False, ""), (True, "v0.6.4")]
            mock_verify.return_value = True
            mock_ns.return_value = "kube-system"
            mock_subproc.return_value = Mock(returncode=0)
            result = self.manager.install_metrics_server()
            self.assertTrue(result["success"])
            self.assertEqual(result["version"], "v0.6.4")
            self.assertIn("message", result)

    def test_verify_connection(self):
        """Test cluster connection verification"""
        self.connector.run_command.return_value = True
        result = self.connector.run_command(["get", "nodes"])
        self.assertTrue(result)
        self.connector.run_command.assert_called_once_with(["get", "nodes"])

if __name__ == '__main__':
    unittest.main() 