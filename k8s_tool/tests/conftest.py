"""
Test configuration and fixtures for k8s-tool tests.
"""
import os
import pytest
import tempfile

@pytest.fixture(scope="session")
def dummy_kubeconfig():
    """Create a dummy kubeconfig file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
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
        return f.name

@pytest.fixture(autouse=True)
def setup_test_env(dummy_kubeconfig):
    """Set up test environment variables."""
    os.environ['KUBECONFIG'] = dummy_kubeconfig
    yield
    # Cleanup
    if os.path.exists(dummy_kubeconfig):
        os.unlink(dummy_kubeconfig) 