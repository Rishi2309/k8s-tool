"""
CLI module for the K8s automation tool.
Provides command line interface for interacting with the K8s automation tool.
"""

import os
import sys
import logging
import json
import yaml
import click

from k8s_tool.connection.connector import ClusterConnector
from k8s_tool.installation.manager import InstallationManager
from k8s_tool.deployment.manager import DeploymentManager
from k8s_tool.monitoring.service import MonitoringService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Helper function to pretty print dict as YAML
def print_yaml(data):
    """Print data as YAML."""
    print(yaml.dump(data, default_flow_style=False))

# Helper function to pretty print dict as JSON
def print_json(data, indent=2):
    """Print data as JSON."""
    print(json.dumps(data, indent=indent))

@click.group()
@click.option(
    '--kubeconfig', 
    type=click.Path(exists=True),
    default=os.path.expanduser('~/.kube/config'),
    help='Path to kubeconfig file'
)
@click.option(
    '--context', 
    help='Kubernetes context to use'
)
@click.option(
    '--namespace', 
    default='default',
    help='Kubernetes namespace to use'
)
@click.option(
    '--output-format', 
    type=click.Choice(['yaml', 'json']), 
    default='yaml',
    help='Output format: yaml or json'
)
@click.pass_context
def cli(ctx, kubeconfig, context, namespace, output_format):
    """
    Kubernetes automation tool for managing deployments with KEDA.
    
    This tool provides functionality to connect to a Kubernetes cluster,
    install necessary components like Helm and KEDA, create deployments
    with event-driven scaling, and monitor deployment health.
    """
    # Initialize the context object
    ctx.ensure_object(dict)
    
    # Store the parameters in the context
    ctx.obj['kubeconfig'] = kubeconfig
    ctx.obj['context'] = context
    ctx.obj['namespace'] = namespace
    ctx.obj['output_format'] = output_format
    
    # Create connector (but don't connect yet)
    connector = ClusterConnector(
        kubeconfig=kubeconfig,
        context=context,
        namespace=namespace
    )
    
    # Store the connector in the context
    ctx.obj['connector'] = connector

# Connect command
@cli.command()
@click.pass_context
def connect(ctx):
    """
    Connect to the Kubernetes cluster.
    Verifies connection and shows cluster information.
    """
    connector = ctx.obj['connector']
    output_format = ctx.obj['output_format']
    
    click.echo("Connecting to Kubernetes cluster...")
    
    if connector.connect():
        click.echo("Successfully connected to Kubernetes cluster")
        
        # Get API version
        api_version = connector.get_api_version()
        click.echo(f"API Version: {api_version}")
        
        # Get current context
        current_context = connector.get_current_context()
        click.echo(f"Current Context: {current_context}")
        
        # Get namespaces count
        namespaces = connector.get_namespaces()
        click.echo(f"Available Namespaces: {len(namespaces)}")
        
        # Return success and connection details
        result = {
            "success": True,
            "message": "Connected to Kubernetes cluster",
            "api_version": api_version,
            "context": current_context,
            "namespace": ctx.obj['namespace'],
            "method": "client",
            "namespaces_count": len(namespaces),
        }
        
        if output_format == 'json':
            print_json(result)
        else:
            print_yaml(result)
    else:
        click.echo("Failed to connect to Kubernetes cluster", err=True)
        sys.exit(1)

# Install command group
@cli.group()
@click.pass_context
def install(ctx):
    """
    Install tools and components in the Kubernetes cluster.
    """
    # Connect to the cluster if not already connected
    connector = ctx.obj['connector']
    
    if not connector._connector:
        click.echo("Connecting to Kubernetes cluster...")
        if not connector.connect():
            click.echo("Failed to connect to Kubernetes cluster", err=True)
            sys.exit(1)
    
    # Create installation manager and store it in the context
    ctx.obj['installation_manager'] = InstallationManager(connector)

# Install Helm command
@install.command()
@click.option('--version', default='latest', help='Helm version to install')
@click.pass_context
def helm(ctx, version):
    """
    Install Helm in the cluster.
    """
    installation_manager = ctx.obj['installation_manager']
    output_format = ctx.obj['output_format']
    
    click.echo(f"Installing Helm{' version ' + version if version != 'latest' else ''}...")
    
    result = installation_manager.install_helm(version)
    
    if result["success"]:
        click.echo(f"Helm installed successfully: {result['version']}")
    else:
        click.echo(f"Failed to install Helm: {result['message']}", err=True)
    
    if output_format == 'json':
        print_json(result)
    else:
        print_yaml(result)

# Install KEDA command
@install.command()
@click.option('--version', default='latest', help='KEDA version to install')
@click.option('--namespace', default='keda', help='Namespace to install KEDA into')
@click.pass_context
def keda(ctx, version, namespace):
    """
    Install KEDA (Kubernetes Event-Driven Autoscaling) in the cluster.
    """
    installation_manager = ctx.obj['installation_manager']
    output_format = ctx.obj['output_format']
    
    click.echo(f"Installing KEDA{' version ' + version if version != 'latest' else ''} to namespace '{namespace}'...")
    
    result = installation_manager.install_keda(version, namespace)
    
    if result["success"]:
        click.echo(f"KEDA installed successfully: {result['version']}")
    else:
        click.echo(f"Failed to install KEDA: {result['message']}", err=True)
    
    if output_format == 'json':
        print_json(result)
    else:
        print_yaml(result)

# Install metrics-server command
@install.command()
@click.option('--version', default='latest', help='metrics-server version to install')
@click.option('--namespace', default='kube-system', help='Namespace to install metrics-server into')
@click.pass_context
def metrics_server(ctx, version, namespace):
    """
    Install metrics-server in the cluster.
    """
    installation_manager = ctx.obj['installation_manager']
    output_format = ctx.obj['output_format']
    
    click.echo(f"Installing metrics-server{' version ' + version if version != 'latest' else ''} to namespace '{namespace}'...")
    
    result = installation_manager.install_metrics_server(version, namespace)
    
    if result["success"]:
        click.echo(f"metrics-server installed successfully: {result['version']}")
    else:
        click.echo(f"Failed to install metrics-server: {result['message']}", err=True)
    
    if output_format == 'json':
        print_json(result)
    else:
        print_yaml(result)

# Cluster info command
@cli.command()
@click.pass_context
def cluster_info(ctx):
    """
    Get information about the connected Kubernetes cluster.
    """
    connector = ctx.obj['connector']
    output_format = ctx.obj['output_format']
    
    # Connect to the cluster if not already connected
    if not connector._connector:
        click.echo("Connecting to Kubernetes cluster...")
        if not connector.connect():
            click.echo("Failed to connect to Kubernetes cluster", err=True)
            sys.exit(1)
    
    # Create installation manager
    installation_manager = InstallationManager(connector)
    
    click.echo("Retrieving cluster information...")
    
    info = installation_manager.get_cluster_info()
    
    # Print summary
    click.echo("Cluster Information:")
    click.echo(f"API Version: {info['api_version']}")
    click.echo(f"Current Context: {info['context']}")
    click.echo(f"Nodes: {len(info['nodes'])}")
    click.echo(f"Namespaces: {len(info['namespaces'])}")
    click.echo(f"Helm Version: {info['helm_version']}")
    click.echo(f"KEDA Installed: {info['keda_installed']}")
    if info['keda_installed']:
        click.echo(f"KEDA Version: {info['keda_version']}")
    
    # Print full details
    if output_format == 'json':
        print_json(info)
    else:
        print_yaml(info)

# Deployment commands group
@cli.group()
@click.pass_context
def deployment(ctx):
    """
    Manage Kubernetes deployments.
    """
    # Connect to the cluster if not already connected
    connector = ctx.obj['connector']
    
    if not connector._connector:
        click.echo("Connecting to Kubernetes cluster...")
        if not connector.connect():
            click.echo("Failed to connect to Kubernetes cluster", err=True)
            sys.exit(1)
    
    # Create deployment manager and store it in the context
    ctx.obj['deployment_manager'] = DeploymentManager(connector)

# Create deployment command
@deployment.command()
@click.option('--name', required=True, help='Deployment name')
@click.option('--image', required=True, help='Container image (e.g., nginx:latest)')
@click.option('--namespace', help='Kubernetes namespace')
@click.option('--port', multiple=True, type=int, help='Port to expose (can be specified multiple times)')
@click.option('--replicas', type=int, default=1, help='Number of replicas')
@click.option('--cpu-request', default='100m', help='CPU request')
@click.option('--cpu-limit', default='500m', help='CPU limit')
@click.option('--memory-request', default='128Mi', help='Memory request')
@click.option('--memory-limit', default='512Mi', help='Memory limit')
@click.option('--env', multiple=True, help='Environment variable in format KEY=VALUE')
@click.option('--label', multiple=True, help='Label in format KEY=VALUE')
@click.option('--service-type', type=click.Choice(['ClusterIP', 'NodePort', 'LoadBalancer']), default='ClusterIP', help='Service type')
@click.option('--enable-autoscaling/--no-autoscaling', default=False, help='Enable HPA-based autoscaling')
@click.option('--min-replicas', type=int, default=1, help='Minimum replicas for autoscaling')
@click.option('--max-replicas', type=int, default=10, help='Maximum replicas for autoscaling')
@click.option('--cpu-target-percentage', type=int, default=80, help='Target CPU percentage for autoscaling')
@click.option('--enable-keda/--no-keda', default=False, help='Enable KEDA-based event-driven autoscaling')
@click.option('--liveness-probe', help='Liveness probe configuration in JSON format')
@click.option('--readiness-probe', help='Readiness probe configuration in JSON format')
@click.option('--startup-probe', help='Startup probe configuration in JSON format')
# KEDA CPU trigger options
@click.option('--keda-cpu-trigger', is_flag=True, help='Enable KEDA CPU-based scaling')
@click.option('--keda-cpu-threshold', type=int, default=50, help='CPU threshold percentage for KEDA scaling')
# KEDA memory trigger options
@click.option('--keda-memory-trigger', is_flag=True, help='Enable KEDA memory-based scaling')
@click.option('--keda-memory-threshold', type=int, default=80, help='Memory threshold percentage for KEDA scaling')
# KEDA Prometheus trigger options
@click.option('--keda-prometheus-trigger', is_flag=True, help='Enable KEDA Prometheus-based scaling')
@click.option('--keda-prometheus-server', help='Prometheus server URL (required for Prometheus trigger)')
@click.option('--keda-prometheus-query', help='Prometheus query (required for Prometheus trigger)')
@click.option('--keda-prometheus-threshold', type=float, help='Threshold value for Prometheus query')
# KEDA Kafka trigger options
@click.option('--keda-kafka-trigger', is_flag=True, help='Enable KEDA Kafka-based scaling')
@click.option('--keda-kafka-bootstrap-servers', help='Kafka bootstrap servers (required for Kafka trigger)')
@click.option('--keda-kafka-consumer-group', help='Kafka consumer group (required for Kafka trigger)')
@click.option('--keda-kafka-topic', help='Kafka topic (required for Kafka trigger)')
@click.option('--keda-kafka-lag-threshold', type=int, default=10, help='Kafka lag threshold')
# KEDA Redis trigger options
@click.option('--keda-redis-trigger', is_flag=True, help='Enable KEDA Redis-based scaling')
@click.option('--keda-redis-address', help='Redis address (required for Redis trigger)')
@click.option('--keda-redis-list-name', help='Redis list name (for list length trigger)')
@click.option('--keda-redis-stream-name', help='Redis stream name (for stream trigger)')
@click.option('--keda-redis-threshold', type=int, default=10, help='Redis list/stream length threshold')
# KEDA RabbitMQ trigger options
@click.option('--keda-rabbitmq-trigger', is_flag=True, help='Enable KEDA RabbitMQ-based scaling')
@click.option('--keda-rabbitmq-host', help='RabbitMQ host (required for RabbitMQ trigger)')
@click.option('--keda-rabbitmq-queue-name', help='RabbitMQ queue name (required for RabbitMQ trigger)')
@click.option('--keda-rabbitmq-queue-length', type=int, default=10, help='RabbitMQ queue length threshold')
# Generic KEDA trigger (for advanced use cases)
@click.option('--keda-trigger', multiple=True, help='Generic KEDA trigger in JSON format')
@click.pass_context
def create(ctx, name, image, namespace, port, replicas, cpu_request, cpu_limit, memory_request, memory_limit, env, label, 
           service_type, enable_autoscaling, min_replicas, max_replicas, cpu_target_percentage, enable_keda, 
           liveness_probe, readiness_probe, startup_probe,
           keda_cpu_trigger, keda_cpu_threshold, keda_memory_trigger, keda_memory_threshold, 
           keda_prometheus_trigger, keda_prometheus_server, keda_prometheus_query, keda_prometheus_threshold, 
           keda_kafka_trigger, keda_kafka_bootstrap_servers, keda_kafka_consumer_group, keda_kafka_topic, keda_kafka_lag_threshold,
           keda_redis_trigger, keda_redis_address, keda_redis_list_name, keda_redis_stream_name, keda_redis_threshold,
           keda_rabbitmq_trigger, keda_rabbitmq_host, keda_rabbitmq_queue_name, keda_rabbitmq_queue_length,
           keda_trigger):
    """
    Create a new deployment in the Kubernetes cluster.
    """
    deployment_manager = ctx.obj['deployment_manager']
    output_format = ctx.obj['output_format']
    namespace = namespace or ctx.obj['namespace']
    
    # Parse environment variables
    env_vars = {}
    for e in env:
        key, value = e.split('=', 1)
        env_vars[key] = value
    
    # Parse labels
    labels = {}
    for l in label:
        key, value = l.split('=', 1)
        labels[key] = value
    
    # Parse ports
    ports = list(port) or [80]
    
    # Parse probes
    probes = {}
    if liveness_probe:
        try:
            probes['liveness_probe'] = json.loads(liveness_probe)
        except json.JSONDecodeError as e:
            click.echo(f"Error parsing liveness probe JSON: {e}", err=True)
            return
    if readiness_probe:
        try:
            probes['readiness_probe'] = json.loads(readiness_probe)
        except json.JSONDecodeError as e:
            click.echo(f"Error parsing readiness probe JSON: {e}", err=True)
            return
    if startup_probe:
        try:
            probes['startup_probe'] = json.loads(startup_probe)
        except json.JSONDecodeError as e:
            click.echo(f"Error parsing startup probe JSON: {e}", err=True)
            return
    
    # Parse KEDA triggers if enabled
    keda_triggers = []
    
    # Add CPU trigger if enabled
    if enable_keda and keda_cpu_trigger:
        keda_triggers.append({
            "type": "cpu",
            "metadata": {
                "type": "Utilization",
                "value": str(keda_cpu_threshold)
            }
        })
    
    # Add Memory trigger if enabled
    if enable_keda and keda_memory_trigger:
        keda_triggers.append({
            "type": "memory",
            "metadata": {
                "type": "Utilization",
                "value": str(keda_memory_threshold)
            }
        })
    
    # Add Prometheus trigger if enabled
    if enable_keda and keda_prometheus_trigger and keda_prometheus_server and keda_prometheus_query:
        trigger = {
            "type": "prometheus",
            "metadata": {
                "serverAddress": keda_prometheus_server,
                "metricName": "prometheus-metric",
                "query": keda_prometheus_query,
            }
        }
        if keda_prometheus_threshold is not None:
            trigger["metadata"]["threshold"] = str(keda_prometheus_threshold)
        keda_triggers.append(trigger)
    
    # Add Kafka trigger if enabled
    if enable_keda and keda_kafka_trigger and keda_kafka_bootstrap_servers and keda_kafka_consumer_group and keda_kafka_topic:
        keda_triggers.append({
            "type": "kafka",
            "metadata": {
                "bootstrapServers": keda_kafka_bootstrap_servers,
                "consumerGroup": keda_kafka_consumer_group,
                "topic": keda_kafka_topic,
                "lagThreshold": str(keda_kafka_lag_threshold)
            }
        })
    
    # Add Redis trigger if enabled
    if enable_keda and keda_redis_trigger and keda_redis_address:
        redis_trigger = {
            "type": "redis",
            "metadata": {
                "address": keda_redis_address,
                "threshold": str(keda_redis_threshold)
            }
        }
        # Add list name if provided
        if keda_redis_list_name:
            redis_trigger["metadata"]["listName"] = keda_redis_list_name
        # Add stream name if provided
        elif keda_redis_stream_name:
            redis_trigger["metadata"]["streamName"] = keda_redis_stream_name
            
        keda_triggers.append(redis_trigger)
    
    # Add RabbitMQ trigger if enabled
    if enable_keda and keda_rabbitmq_trigger and keda_rabbitmq_host and keda_rabbitmq_queue_name:
        keda_triggers.append({
            "type": "rabbitmq",
            "metadata": {
                "host": keda_rabbitmq_host,
                "queueName": keda_rabbitmq_queue_name,
                "queueLength": str(keda_rabbitmq_queue_length)
            }
        })
    
    # Parse generic KEDA triggers
    for trigger_json in keda_trigger:
        try:
            trigger = json.loads(trigger_json)
            keda_triggers.append(trigger)
        except json.JSONDecodeError as e:
            click.echo(f"Error parsing KEDA trigger JSON: {e}", err=True)
            click.echo("Skipping invalid trigger", err=True)
    
    click.echo(f"Creating deployment '{name}' with image '{image}'...")
    
    result = deployment_manager.create_deployment(
        name=name,
        image=image,
        namespace=namespace,
        ports=ports,
        replicas=replicas,
        cpu_request=cpu_request,
        cpu_limit=cpu_limit,
        memory_request=memory_request,
        memory_limit=memory_limit,
        env_vars=env_vars,
        labels=labels,
        service_type=service_type,
        autoscaling_enabled=enable_autoscaling and not enable_keda,
        min_replicas=min_replicas,
        max_replicas=max_replicas,
        cpu_target_percentage=cpu_target_percentage,
        keda_enabled=enable_keda,
        keda_triggers=keda_triggers,
        liveness_probe=probes.get('liveness_probe'),
        readiness_probe=probes.get('readiness_probe'),
        startup_probe=probes.get('startup_probe'),
    )
    
    if result["success"]:
        click.echo(f"Successfully created deployment: {result['message']}")
        click.echo(f"Deployment ID: {result['deployment_id']}")
        
        # Print resource endpoint if available
        if service_type in ["NodePort", "LoadBalancer"] and "service" in result:
            service = result["service"]
            ports = service.get("spec", {}).get("ports", [])
            external_ip = None
            
            if service_type == "LoadBalancer":
                external_ip = service.get("status", {}).get("loadBalancer", {}).get("ingress", [{}])[0].get("ip")
                if external_ip:
                    click.echo(f"Service external IP: {external_ip}")
            elif service_type == "NodePort":
                for port_info in ports:
                    if "nodePort" in port_info:
                        click.echo(f"Service NodePort: {port_info['nodePort']} (maps to {port_info['port']})")
    else:
        click.echo(f"Failed to create deployment: {result['message']}", err=True)
    
    if output_format == 'json':
        print_json(result)
    else:
        print_yaml(result)

# Get deployment status command
@deployment.command()
@click.argument('deployment_id')
@click.option('--namespace', help='Kubernetes namespace')
@click.pass_context
def status(ctx, deployment_id, namespace):
    """
    Get the status of a deployment by its ID (searches all namespaces).
    """
    deployment_manager = ctx.obj['deployment_manager']
    output_format = ctx.obj['output_format']
    
    click.echo(f"Getting status for deployment ID: {deployment_id}...")
    
    result = deployment_manager.get_deployment_status(deployment_id, namespace)
    
    if result["success"]:
        deployments = result.get("deployments", [])
        if not deployments:
            click.echo(f"Deployment '{deployment_id}' not found in any namespace.")
        for dep in deployments:
            ns = dep.get("resources", [{}])[0].get("namespace", "unknown")
            click.echo(f"Found deployment '{deployment_id}' in namespace '{ns}'")
            # Print concise status info
            pod_status = dep.get("pod_status", {})
            click.echo(f"Pods: {pod_status.get('ready', 0)}/{pod_status.get('total', 0)} ready")
            click.echo(f"Pod status breakdown: {pod_status.get('status_breakdown', {})}")
            if dep.get("service_endpoints"):
                click.echo(f"Service endpoints: {dep['service_endpoints']}")
            click.echo("")
    else:
        click.echo(f"Failed to get deployment status: {result['message']}", err=True)
    
    if output_format == 'json':
        print_json(result)
    else:
        print_yaml(result)

def main():
    """Entry point for the CLI."""
    cli(obj={})

if __name__ == '__main__':
    main()