# Smallest Self-Host Helm Chart

Helm chart for deploying Smallest AI's Speech-to-Text (STT) and Text-to-Speech (TTS) models on Kubernetes with GPU acceleration.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Components](#components)
- [Configuration](#configuration)
  - [Credentials](#credentials)
  - [Scaling](#scaling)
  - [GPU Configuration](#gpu-configuration)
  - [Resource Allocation](#resource-allocation)
  - [Redis Configuration](#redis-configuration)
  - [Service Configuration](#service-configuration)
- [Monitoring](#monitoring)
- [Cluster Autoscaler](#cluster-autoscaler-aws-eks)
- [Upgrade and Uninstall](#upgrade-and-uninstall)
- [Troubleshooting](#troubleshooting)
- [Getting Help](#getting-help)

## Overview

The Smallest Self-Host Helm chart enables you to deploy high-performance speech recognition and synthesis models in your own Kubernetes environment. This chart includes all necessary components for a production-ready deployment with autoscaling, monitoring, and GPU support.

**Chart Information:**

- Version: 0.1.0
- App Version: 1.16.0
- Type: Application

## Prerequisites

Before installing this chart, ensure you have:

- Kubernetes cluster (version 1.19 or higher)
- Helm 3.0 or higher
- kubectl configured to access your cluster
- GPU nodes with NVIDIA drivers (for Lightning ASR)
- Valid license key from Smallest.ai
- Container registry credentials (provided by Smallest.ai)

## Getting Started

### Step 1: Obtain Credentials

Contact **support@smallest.ai** to receive:

- License key
- Container registry credentials (username, password, email)

### Step 2: Configure Values

Edit the `smallest-self-host/values.yaml` file with your credentials:

```yaml
global:
  licenseKey: "your-license-key-here"
  imageCredentials:
    username: "your-registry-username"
    password: "your-registry-password"
```

### Step 3: Add Helm Repository

Add the Smallest Self-Host Helm repository:

```bash
helm repo add smallest-self-host https://smallest-inc.github.io/smallest-self-host
helm repo update
```

View available chart versions:

```bash
helm search repo smallest-self-host
```

### Step 4: Install the Chart

Install from the Helm repository:

```bash
helm install smallest-self-host smallest-self-host/smallest-self-host
```

Or with a custom namespace:

```bash
helm install smallest-self-host smallest-self-host/smallest-self-host --namespace smallest --create-namespace
```

Alternatively, install from local chart source:

```bash
cd charts/smallest-self-host
helm dependency update
helm install smallest-self-host ./
```

### Step 5: Verify Installation

Check that all pods are running:

```bash
kubectl get pods
kubectl get services
```

Access the API server using the service endpoint or configure an ingress controller for external access.

### Installation with Custom Values

Install with a custom values file:

```bash
helm install smallest-self-host smallest-self-host/smallest-self-host -f custom-values.yaml
```

## Components

### Core Services

**API Server**

- Main API gateway for speech services
- Port: 7100
- Handles request routing and load balancing

**Lightning ASR**

- GPU-accelerated automatic speech recognition
- Port: 2269
- Requires NVIDIA GPU nodes

**License Proxy**

- License validation and management
- Port: 3369
- Validates license keys for all services

### Dependencies

The chart includes the following optional dependencies:

- **Redis**: Caching and state management (v24.0.0)
- **Kube-Prometheus-Stack**: Monitoring and metrics collection (v60.5.0)
- **Prometheus-Adapter**: Custom metrics for HPA (v4.14.2)
- **Cluster-Autoscaler**: Node-level autoscaling for AWS EKS (v9.52.1)
- **GPU-Operator**: NVIDIA GPU management (v24.9.2)

## Configuration

### Credentials

#### Using Existing Secrets

If you prefer to manage secrets externally:

```yaml
global:
  licenseKey: ""
  licenseKeySecretRef: "your-license-secret"
  imageCredentials:
    create: false
  imageCredentialsSecretRef: "your-registry-secret"
```

### Scaling

#### Manual Scaling

Set fixed replica counts:

```yaml
scaling:
  replicas:
    lightningAsr: 2
    licenseProxy: 1
```

#### Horizontal Pod Autoscaling (HPA)

Enable automatic scaling based on metrics:

```yaml
scaling:
  auto:
    enabled: true
    apiServer:
      hpa:
        enabled: true
        minReplicas: 1
        maxReplicas: 10
        lightningAsrToApiServerRatio: 2
        scaleUpStabilizationWindowSeconds: 30
        scaleDownStabilizationWindowSeconds: 60
    lightningAsr:
      hpa:
        enabled: true
        minReplicas: 1
        maxReplicas: 10
        targetActiveRequests: 5
        scaleUpStabilizationWindowSeconds: 0
        scaleDownStabilizationWindowSeconds: 300
```

### GPU Configuration

Lightning ASR requires GPU nodes. Configure node selection and tolerations:

```yaml
lightningAsr:
  nodeSelector:
    node.kubernetes.io/instance-type: g5.xlarge
  tolerations:
    - key: gpu
      operator: Equal
      value: "true"
      effect: NoSchedule
    - key: nvidia.com/gpu
      operator: Exists
      effect: NoSchedule
```

Adjust the `instance-type` to match your GPU node type (e.g., `g5.xlarge`, `g5.2xlarge`, `p3.2xlarge`).

### Resource Allocation

#### API Server Resources

```yaml
apiServer:
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 512Mi
```

#### Lightning ASR Resources

```yaml
lightningAsr:
  resources:
    requests:
      memory: 10Gi
    limits:
      memory: 12Gi
```

### Redis Configuration

#### Using Embedded Redis

Enable the included Redis instance:

```yaml
redis:
  enabled: true
  auth:
    enabled: true
    password: "your-secure-password"
  master:
    persistence:
      enabled: true
      size: 8Gi
```

#### Using External Redis

Connect to an external Redis instance:

```yaml
redis:
  enabled: false
  externalHost: "redis.example.com"
  port: 6379
  ssl: false
  auth:
    enabled: true
    password: "your-redis-password"
```

### Service Configuration

#### Expose Services Externally

Change the API server service type to LoadBalancer:

```yaml
apiServer:
  service:
    type: LoadBalancer
    loadBalancerSourceRanges:
      - "10.0.0.0/8"
    externalTrafficPolicy: "Local"
```

#### Custom Base URLs

Configure custom base URLs for services:

```yaml
apiServer:
  baseUrl: "https://api.example.com"

lightningAsr:
  baseUrl: "http://asr-internal.example.com"
```

## Monitoring

### Accessing Grafana

If the Prometheus stack is enabled, access Grafana:

```bash
kubectl port-forward svc/smallest-prometheus-stack-grafana 3000:80
```

Open http://localhost:3000 in your browser.

**Default Credentials:**

- Username: `admin`
- Password: `prom-operator`

### Enable ServiceMonitor

Enable Prometheus metrics scraping for Lightning ASR:

```yaml
scaling:
  auto:
    enabled: true
    lightningAsr:
      servicemonitor:
        enabled: true
```

### Custom Metrics

The chart includes custom Prometheus metrics for autoscaling:

- `asr_active_requests`: Active requests per Lightning ASR pod
- `lightning_asr_replica_count`: Current replica count

## Cluster Autoscaler (AWS EKS)

Enable cluster-level autoscaling for AWS EKS:

### Step 1: Create IAM Role

Create an IAM role with the Cluster Autoscaler policy and configure IRSA (IAM Roles for Service Accounts).

### Step 2: Configure Chart

```yaml
cluster-autoscaler:
  enabled: true
  rbac:
    serviceAccount:
      name: cluster-autoscaler-sa
      annotations:
        eks.amazonaws.com/role-arn: "arn:aws:iam::123456789012:role/cluster-autoscaler-role"
  autoDiscovery:
    clusterName: "your-eks-cluster-name"
  awsRegion: "us-east-1"
```

Replace the ARN and cluster name with your actual values.

## Upgrade and Uninstall

### Upgrade Chart

First, update the Helm repository:

```bash
helm repo update
```

Then upgrade the chart:

```bash
helm upgrade smallest-self-host smallest-self-host/smallest-self-host
```

Or with a specific values file:

```bash
helm upgrade smallest-self-host smallest-self-host/smallest-self-host -f custom-values.yaml
```

If installing from local source:

```bash
helm upgrade smallest-self-host ./smallest-self-host
```

### Uninstall Chart

Remove the deployment:

```bash
helm uninstall smallest-self-host
```

If deployed in a custom namespace:

```bash
helm uninstall smallest-self-host --namespace smallest
```

## Troubleshooting

### Check Pod Status

View all pods:

```bash
kubectl get pods
```

### View Pod Logs

Check logs for specific services:

```bash
kubectl logs -l app=api-server
kubectl logs -l app=lightning-asr
kubectl logs -l app=license-proxy
```

Follow logs in real-time:

```bash
kubectl logs -l app=lightning-asr -f
```

### Check Service Status

```bash
kubectl get svc
kubectl describe svc api-server
```

### Verify GPU Availability

Check GPU resources on nodes:

```bash
kubectl describe nodes | grep -A 5 "nvidia.com/gpu"
```

List GPU-enabled pods:

```bash
kubectl get pods -o json | jq '.items[] | select(.spec.containers[].resources.limits."nvidia.com/gpu" != null) | .metadata.name'
```

### Common Issues

**Pods stuck in Pending state:**

- Check if GPU nodes are available
- Verify node selectors and tolerations match your cluster configuration
- Check resource availability with `kubectl describe pod <pod-name>`

**ImagePullBackOff errors:**

- Verify image credentials are correct
- Ensure the pull secret is created properly
- Check network connectivity to the registry

**License validation failures:**

- Confirm license key is valid and not expired
- Check license-proxy logs for detailed error messages
- Verify network connectivity to license validation endpoint

## Getting Help

### Support Channels

For issues, questions, or feature requests:

**Email Support:**

- support@smallest.ai

**Before Contacting Support:**

- Ensure you have a valid license key
- Verify image credentials are correct
- Collect relevant logs and pod status information

### Useful Information to Provide

When reporting issues, include:

- Kubernetes version (`kubectl version`)
- Helm version (`helm version`)
- Chart version
- Pod status and logs
- Error messages or unexpected behavior

---

_For more information about Smallest AI's products and services, visit [smallest.ai](https://smallest.ai)_
