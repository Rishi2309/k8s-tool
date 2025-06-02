"""
Test configuration and fixtures for k8s-tool tests.
"""
import os
import pytest
import tempfile

@pytest.fixture(scope="session")
def dummy_kubeconfig():
    """Create a dummy kubeconfig file for testing."""
    # Create in /tmp to ensure it's writable in CI
    temp_dir = tempfile.gettempdir()
    kubeconfig_path = os.path.join(temp_dir, 'dummy-kubeconfig')
    
    # Create the file if it doesn't exist
    if not os.path.exists(kubeconfig_path):
        with open(kubeconfig_path, 'w') as f:
            f.write("""
apiVersion: v1
kind: Config
clusters:
- cluster:
    server: https://dummy-server:6443
  name: dummy-cluster
contexts:
- context:
    cluster: dummy-cluster
    user: dummy-user
  name: dummy-context
current-context: dummy-context
users:
- name: dummy-user
  user:
    token: dummy-token
""")
        print(f"Created dummy kubeconfig at: {kubeconfig_path}")
    
    # Ensure the file exists and is readable
    assert os.path.exists(kubeconfig_path), f"Kubeconfig file not created at {kubeconfig_path}"
    assert os.access(kubeconfig_path, os.R_OK), f"Kubeconfig file not readable at {kubeconfig_path}"
    
    return kubeconfig_path

@pytest.fixture(autouse=True)
def setup_test_env(dummy_kubeconfig):
    """Set up test environment variables."""
    print(f"Setting KUBECONFIG to: {dummy_kubeconfig}")
    os.environ['KUBECONFIG'] = dummy_kubeconfig
    yield
    # Don't clean up the kubeconfig file between tests
    # It will be cleaned up at the end of the session 