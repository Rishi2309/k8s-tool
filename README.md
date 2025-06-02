# k8s-tool

A command-line tool for managing Kubernetes deployments and installations created with collaborating LLM coding agents.

## Design Overview

`k8s-tool` is designed to simplify the management of Kubernetes deployments and installations. It provides a user-friendly command-line interface built with Click framework to perform common tasks such as installing Helm and KEDA, and creating deployments with various configurations. The tool is built using Python and relies on the `kubectl` command-line tool to interact with Kubernetes clusters, ensuring compatibility and ease of use.

## Design Implementation

The implementation of `k8s-tool` is structured around several key components:

- **CLI Interface**: The command-line interface is built using the Click framework, providing a modern and intuitive command-line experience. It supports:
  - Command groups for organizing related functionality (install, deployment)
  - Rich command-line options with type validation
  - Support for both YAML and JSON output formats
  - Interactive feedback and progress indicators
  - Comprehensive help messages and documentation

- **Connection Management**: The tool uses a dedicated `KubectlConnector` class that:
  - Manages connections to Kubernetes clusters using kubectl CLI commands
  - Handles kubeconfig and context management
  - Provides methods for executing kubectl commands through subprocess
  - Includes error handling and logging
  - Supports namespace management

- **Installation Management**: The `InstallationManager` handles:
  - Installation of Helm and KEDA
  - Version management for installed components
  - Verification of installations
  - Cluster information retrieval
  - Metrics server installation and configuration

- **Deployment Management**: The `DeploymentManager` provides:
  - Creation of deployments with various configurations
  - Support for different service types (ClusterIP, NodePort, LoadBalancer)
  - Resource limit and request management
  - Environment variable and label configuration
  - Health probe configuration (liveness, readiness, startup)
  - Integration with KEDA for event-driven autoscaling
  - Support for multiple scaling triggers (CPU, Memory, Prometheus, Kafka, Redis, RabbitMQ)

- **Error Handling and Logging**: The tool includes:
  - Comprehensive error handling for all operations
  - Detailed logging using Python's logging framework
  - User-friendly error messages
  - Command execution status tracking
  - Validation of user inputs

- **Testing**: The tool is supported by:
  - Unit tests using Python's unittest framework
  - Mock-based testing for external dependencies
  - Test coverage for CLI commands
  - Test coverage for core functionality
  - Integration tests for end-to-end scenarios

## CI/CD Implementation

### Continuous Integration (CI)
- **PR Validation**: Every pull request must pass all test cases before merging
  - Automated test suite runs on every PR creation and update
  - Test coverage includes CLI commands, deployment management, and installation procedures
  - PR cannot be merged until all tests pass successfully
  - Branch protection rules enforce test passing as a mandatory check

### Continuous Deployment (CD)
- **Version Management**:
  - Automatic tag creation on every push to master branch
  - Version format: v0.1, v0.2, v0.3, etc.
  - Users can install specific versions using the tag version
  - Example: `pip install git+https://github.com/your-repo.git@v0.1`

- **Branch Protection**:
  - Master branch is protected against direct pushes
  - Changes to master must come through pull requests
  - PR requires at least one review approval
  - All CI checks must pass before merging

### Workflow Automation
- **CI Pipeline**:
  - Runs on every PR and push
  - Executes test suite
  - Validates code quality
  - Ensures consistent behavior across environments

- **CD Pipeline**:
  - Triggers on successful merges to master
  - Creates new version tags automatically
  - Maintains version history
  - Enables version-specific installations

### Running Tests Locally
To run the test suite locally, use the following command:

```bash
# Run all tests
pytest tests -v

# Run specific test file
pytest tests/test_cli.py -v

# Run specific test case
pytest tests/test_cli.py::TestCLI::test_install_helm_command -v
```

### Troubleshooting

#### KEDA Image Pull Issues
When using Podman with Kind cluster for local testing, you might encounter TLS verification errors while pulling images. This is a common issue with Podman's default TLS verification settings.

**Error Example:**
```
Error: error pulling image "registry.k8s.io/metrics-server/metrics-server:v0.5.2": 
Error initializing source docker://registry.k8s.io/metrics-server/metrics-server:v0.5.2: 
error pinging docker registry registry.k8s.io: Get "https://registry.k8s.io/v2/": 
x509: certificate signed by unknown authority
```

**Solution:**
1. Pull the image locally without TLS verification:
```bash
podman pull --tls-verify=false registry.k8s.io/metrics-server/metrics-server:v0.5.2
```

2. Load the image into your Kind cluster:
```bash
kind load docker-image registry.k8s.io/metrics-server/metrics-server:v0.5.2 --name {cluster-name}
```

Replace `{cluster-name}` with your Kind cluster name. This workaround allows you to use the image in your local development environment while maintaining security in production environments.

## Prerequisites

- Python 3.7 or higher
- pip3
- Git
- kubectl installed and configured
- Access to a Kubernetes cluster

## Installation

You can install `k8s-tool` using pip3 directly from the Git repository:

```bash
# Install from main branch
pip3 install git+https://github.com/Rishi2309/k8s-tool.git

# Or install from a specific branch
pip3 install git+https://github.com/Rishi2309/k8s-tool.git@branch_name

# Or install a specific version
pip3 install git+https://github.com/Rishi2309/k8s-tool.git@v0.1.0
```

This will automatically install all required Python dependencies:
- click>=8.0.0 (Command line interface creation kit)
- pyyaml>=5.1 (YAML parser and emitter)
- pytest>=7.0.0 (Testing framework)

After installation, the `k8s-tool` command will be available in your terminal.

## Command Reference

### Global Options

- `--kubeconfig PATH`: Path to kubeconfig file (default: ~/.kube/config)
- `--context NAME`: Kubernetes context to use
- `--namespace NAME`: Kubernetes namespace to use (default: default)
- `--output-format FORMAT`: Output format (yaml/json, default: yaml)

### Connection Commands

#### `k8s-tool connect`
Verify connection to the Kubernetes cluster and display basic cluster information.

#### `k8s-tool cluster-info`
Display detailed information about the Kubernetes cluster.

### Installation Commands

#### `k8s-tool install helm`
Install Helm in the cluster.

Options:
- `--version VERSION`: Specific Helm version to install (default: latest)

#### `k8s-tool install keda`
Install KEDA in the cluster.

Options:
- `--version VERSION`: Specific KEDA version to install (default: latest)
- `--namespace NAME`: Namespace to install KEDA in (default: keda)

#### `k8s-tool install metrics-server`
Install metrics-server in the cluster.

Options:
- `--version VERSION`: Specific metrics-server version to install (default: latest)
- `--namespace NAME`: Namespace to install metrics-server in (default: kube-system)

### Deployment Commands

#### `k8s-tool deployment create`
Create a new deployment.

Required Options:
- `--name NAME`: Name of the deployment
- `--image IMAGE`: Container image to use

Optional Options:
- `--namespace NAME`: Kubernetes namespace
- `--port PORT`: Port to expose (can be specified multiple times)
- `--replicas COUNT`: Number of replicas (default: 1)
- `--cpu-request VALUE`: CPU request (default: 100m)
- `--cpu-limit VALUE`: CPU limit (default: 500m)
- `--memory-request VALUE`: Memory request (default: 128Mi)
- `--memory-limit VALUE`: Memory limit (default: 512Mi)
- `--env KEY=VALUE`: Environment variable (can be specified multiple times)
- `--label KEY=VALUE`: Label (can be specified multiple times)
- `--service-type TYPE`: Service type (ClusterIP/NodePort/LoadBalancer, default: ClusterIP)
- `--enable-autoscaling`: Enable HPA-based autoscaling
- `--min-replicas COUNT`: Minimum replicas for autoscaling (default: 1)
- `--max-replicas COUNT`: Maximum replicas for autoscaling (default: 10)
- `--cpu-target-percentage VALUE`: Target CPU percentage for autoscaling (default: 80)
- `--enable-keda`: Enable KEDA-based event-driven autoscaling
- `--liveness-probe JSON`: Liveness probe configuration in JSON format
- `--readiness-probe JSON`: Readiness probe configuration in JSON format
- `--startup-probe JSON`: Startup probe configuration in JSON format

KEDA Trigger Options:
- CPU Trigger:
  - `--keda-cpu-trigger`: Enable KEDA CPU-based scaling
  - `--keda-cpu-threshold VALUE`: CPU threshold percentage (default: 50)

- Memory Trigger:
  - `--keda-memory-trigger`: Enable KEDA memory-based scaling
  - `--keda-memory-threshold VALUE`: Memory threshold percentage (default: 80)

- Prometheus Trigger:
  - `--keda-prometheus-trigger`: Enable KEDA Prometheus-based scaling
  - `--keda-prometheus-server URL`: Prometheus server URL
  - `--keda-prometheus-query QUERY`: Prometheus query
  - `--keda-prometheus-threshold VALUE`: Threshold value for query

- Kafka Trigger:
  - `--keda-kafka-trigger`: Enable KEDA Kafka-based scaling
  - `--keda-kafka-bootstrap-servers SERVERS`: Kafka bootstrap servers
  - `--keda-kafka-consumer-group GROUP`: Kafka consumer group
  - `--keda-kafka-topic TOPIC`: Kafka topic
  - `--keda-kafka-lag-threshold VALUE`: Lag threshold (default: 10)

- Redis Trigger:
  - `--keda-redis-trigger`: Enable KEDA Redis-based scaling
  - `--keda-redis-address ADDRESS`: Redis address
  - `--keda-redis-list-name NAME`: Redis list name
  - `--keda-redis-stream-name NAME`: Redis stream name
  - `--keda-redis-threshold VALUE`: List/stream length threshold (default: 10)

- RabbitMQ Trigger:
  - `--keda-rabbitmq-trigger`: Enable KEDA RabbitMQ-based scaling
  - `--keda-rabbitmq-host HOST`: RabbitMQ host
  - `--keda-rabbitmq-queue-name NAME`: RabbitMQ queue name
  - `--keda-rabbitmq-queue-length VALUE`: Queue length threshold (default: 10)

- Generic Trigger:
  - `--keda-trigger JSON`: Generic KEDA trigger in JSON format (can be specified multiple times)

#### `k8s-tool deployment status`
Check the status of a deployment.

Required Arguments:
- `DEPLOYMENT_ID`: ID of the deployment or name to check

Optional Options:
- `--namespace NAME`: Kubernetes namespace

## Usage

`k8s-tool` provides several commands to manage Kubernetes deployments and installations.

### Connect to Cluster

To connect to a Kubernetes cluster, use the following command:

```bash
k8s-tool connect
```

This will verify the connection to your Kubernetes cluster and display basic cluster information.

### Get Cluster Information

To get detailed information about your Kubernetes cluster, use:

```bash
k8s-tool cluster-info
```

This command provides information about:
- API Version
- Current Context
- Number of Nodes
- Available Namespaces
- Helm Version
- KEDA Installation Status

### Install Components

#### Install Helm

To install Helm, use the following command:

```bash
k8s-tool install helm
```

This will install the latest version of Helm.

#### Install KEDA

To install KEDA, use the following command:

```bash
k8s-tool install keda
```

This will install KEDA in the `keda` namespace.

#### Install Metrics Server

To install the metrics-server, use the following command:

```bash
k8s-tool install metrics-server
```

The metrics-server is a crucial component that:
- Collects resource metrics from Kubelets
- Provides resource usage data for pods and nodes
- Enables the Horizontal Pod Autoscaler (HPA) to work
- Required for viewing pod resource usage in deployment status
- Essential for KEDA's CPU and memory-based scaling

### Create a Deployment

To create a basic deployment, use the following command:

```bash
k8s-tool deployment create --name <deployment-name> --image <image-name>
```

Replace `<deployment-name>` and `<image-name>` with your desired values.

### Check Deployment Status

To check the status of a deployment, use:

```bash
k8s-tool deployment status <deployment-id>
```

This command provides:
- Deployment status across all namespaces
- Pod status (ready/total)
- Pod status breakdown
- Service endpoints (if available)
- Resource usage metrics for each pod:
  - CPU usage
  - Memory usage

Note: Resource usage metrics are only available if the metrics-server is installed in your cluster.

### Create a Deployment with Service

To create a deployment with a service, use the following command:

```bash
k8s-tool deployment create --name <deployment-name> --image <image-name> --service-type ClusterIP --port 80
```

### Create a Deployment with HPA

To create a deployment with Horizontal Pod Autoscaling (HPA), use the following command:

```bash
k8s-tool deployment create --name <deployment-name> --image <image-name> --enable-autoscaling --cpu-target-percentage 80
```

### Create a Deployment with KEDA

To create a deployment with KEDA enabled, use the following command:

```bash
k8s-tool deployment create --name <deployment-name> --image <image-name> --enable-keda --keda-cpu-trigger --keda-cpu-threshold 80
```

### Create a Deployment with Resource Limits

To create a deployment with resource limits, use the following command:

```bash
k8s-tool deployment create --name <deployment-name> --image <image-name> --cpu-limit 500m --memory-limit 512Mi
```

Sample snapshots
<img width="1439" alt="Screenshot 2025-06-02 at 12 28 17 PM" src="https://github.com/user-attachments/assets/c8870a39-355a-4c54-b245-c5f2abdc5a56" />
<img width="1440" alt="Screenshot 2025-06-02 at 12 29 01 PM" src="https://github.com/user-attachments/assets/c14d2124-b301-41db-99a9-18df74616739" />
<img width="1440" alt="Screenshot 2025-06-02 at 12 29 13 PM" src="https://github.com/user-attachments/assets/dc595b78-9da8-4e46-8dc0-98c128a2f028" />
<img width="1437" alt="Screenshot 2025-06-02 at 12 29 31 PM" src="https://github.com/user-attachments/assets/7ecedd11-967f-4f91-b40c-44c6094d2563" />
<img width="1440" alt="Screenshot 2025-06-02 at 12 29 44 PM" src="https://github.com/user-attachments/assets/fd51dcd2-bfac-4239-9123-3208db699230" />
<img width="1440" alt="Screenshot 2025-06-02 at 12 29 49 PM" src="https://github.com/user-attachments/assets/bd59c6f3-0320-423b-aaae-64bdbc832fc1" />
<img width="1440" alt="Screenshot 2025-06-02 at 12 29 53 PM" src="https://github.com/user-attachments/assets/a2ba8e25-4088-4a64-a69c-3491eb706d05" />
<img width="1440" alt="Screenshot 2025-06-02 at 12 30 05 PM" src="https://github.com/user-attachments/assets/01b10ee7-acff-4135-8837-0a06b47f6cf8" />
<img width="1440" alt="Screenshot 2025-06-02 at 12 30 11 PM" src="https://github.com/user-attachments/assets/e83edebb-11e2-4add-84fd-c1cea9db922f" />
<img width="1247" alt="Screenshot 2025-06-02 at 12 27 53 PM" src="https://github.com/user-attachments/assets/11023923-a859-41c9-96f4-d88b3e9a0197" />
<img width="1438" alt="Screenshot 2025-06-02 at 12 28 49 PM" src="https://github.com/user-attachments/assets/a290040c-4260-4c07-9cbb-ec1e3881c3e8" />
<img width="1438" alt="Screenshot 2025-06-02 at 12 28 38 PM" src="https://github.com/user-attachments/assets/4d5b0073-28e3-4ba7-b931-258aca293d2a" />
<img width="1438" alt="Screenshot 2025-06-02 at 12 28 27 PM" src="https://github.com/user-attachments/assets/c08700cf-12f8-4de1-a598-333324b31bee" />
<img width="1430" alt="Screenshot 2025-06-02 at 12 28 02 PM" src="https://github.com/user-attachments/assets/577a1de9-3e66-457f-a641-03c321a4781f" />


