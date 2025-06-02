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
    return kubeconfig_path

@pytest.fixture(autouse=True)
def setup_test_env(dummy_kubeconfig):
    """Set up test environment variables."""
    print(f"Setting KUBECONFIG to: {dummy_kubeconfig}")
    os.environ['KUBECONFIG'] = dummy_kubeconfig
    yield
    # Cleanup
    if os.path.exists(dummy_kubeconfig):
        print(f"Cleaning up kubeconfig at: {dummy_kubeconfig}")
        os.unlink(dummy_kubeconfig) 