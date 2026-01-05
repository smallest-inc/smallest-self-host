# Smallest Self-Host Helm Chart

Deploy Smallest AI's Speech-to-Text (STT) models on Kubernetes with GPU acceleration.

## Quick Start

### Prerequisites

- Kubernetes cluster (v1.19+)
- Helm 3.0+
- GPU nodes with NVIDIA drivers
- License key from [Smallest.ai](https://smallest.ai)

### Installation

1. **Add Helm repository**:

```bash
helm repo add smallest-self-host https://smallest-inc.github.io/smallest-self-host
helm repo update
```

2. **Configure values**:

```bash
cat > values.yaml <<EOF
global:
  licenseKey: "your-license-key-here"
  imageCredentials:
    username: "your-username"
    password: "your-password"
    email: "your-email"

models:
  asrModelUrl: "your-model-url"

lightningAsr:
  nodeSelector:
    node.kubernetes.io/instance-type: g5.xlarge
  tolerations:
    - key: nvidia.com/gpu
      operator: Exists
      effect: NoSchedule
EOF
```

3. **Install the chart**:

```bash
helm install smallest-self-host smallest-self-host/smallest-self-host \
  -f values.yaml \
  --namespace smallest \
  --create-namespace
```

4. **Verify installation**:

```bash
kubectl get pods -n smallest
kubectl port-forward -n smallest svc/api-server 7100:7100
curl http://localhost:7100/health
```

## Documentation

For comprehensive documentation, visit: **[docs.smallest.ai](https://docs.smallest.ai)** (coming soon)

**Key topics**:
- [Kubernetes Setup Guide](../docs/kubernetes/quick-start.mdx)
- [AWS EKS Deployment](../docs/kubernetes/aws/eks-setup.mdx)
- [Autoscaling Configuration](../docs/kubernetes/autoscaling/hpa-configuration.mdx)
- [Storage & PVC Setup](../docs/kubernetes/storage/efs-configuration.mdx)
- [API Reference](../docs/api-reference/authentication.mdx)
- [Troubleshooting](../docs/troubleshooting/common-issues.mdx)

## Getting Credentials

Contact **support@smallest.ai** to obtain:

- License key
- Container registry credentials
- Model download URLs

## Key Features

- ✅ GPU-accelerated speech recognition
- ✅ Horizontal pod autoscaling (HPA)
- ✅ Cluster autoscaling (AWS EKS)
- ✅ Prometheus monitoring
- ✅ Grafana dashboards
- ✅ High availability with replicas
- ✅ Shared model storage (EFS)

## Components

| Component | Description | Port |
|-----------|-------------|------|
| API Server | Main API gateway | 7100 |
| Lightning ASR | GPU-accelerated STT engine | 2269 |
| License Proxy | License validation | 3369 |
| Redis | Caching and state | 6379 |

## Upgrade

```bash
helm repo update
helm upgrade smallest-self-host smallest-self-host/smallest-self-host \
  -f values.yaml \
  --namespace smallest
```

## Uninstall

```bash
helm uninstall smallest-self-host --namespace smallest
```

## Support

- **Email**: support@smallest.ai
- **Website**: [smallest.ai](https://smallest.ai)
- **Issues**: [GitHub Issues](https://github.com/smallest-inc/smallest-self-host/issues)

## License

Copyright © 2024 Smallest AI. All rights reserved.

---

**Chart Version**: 0.1.1 | **App Version**: 1.16.0
