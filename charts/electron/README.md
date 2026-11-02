# Electron on Kubernetes

Electron is smallest.ai's voice-agent LLM. This chart runs it on your own GPUs: one engine per GPU, a router in front of them that your apps call (an OpenAI-compatible API), and a license-proxy that checks your licence with smallest.ai and reports the tokens served.

## What you need

- GPU nodes with H100, H200 or RTX PRO 6000 GPUs, one type per install, and the NVIDIA device plugin (or GPU Operator), so pods can ask for `nvidia.com/gpu`. Those GPUs must be Kubernetes's alone: a GPU that something outside the cluster also uses can be handed to an engine, which then waits, logging that another process is using its GPU.
- Memory on each GPU node: about 100 GB per H100/H200 engine, 90 GB per RTX PRO 6000 engine. The model is decrypted into RAM while it loads, one engine per node at a time, then deleted.
- Disk for the model: 70 GB (44 GB for RTX PRO 6000) wherever it is kept, for the release running and the one before it, see Storage.
- Outbound HTTPS from the cluster to `api.smallest.ai` and to the model's download host.
- A licence key, from the smallest.ai console: Settings, then Licenses. Your organization's plan must include Electron on-prem.
- quay.io credentials from smallest.ai (`global.imageCredentials`), or the images mirrored to your own registry (`images.registry`).

## Install

```bash
cat > electron.yaml <<EOF
global:
  licenseKey: "<your licence key>"
  imageCredentials:
    username: "<quay username>"
    password: "<quay password>"
engines:
  count: 4          # one per GPU
  gpu: H200
EOF
helm repo add smallest-self-host https://smallest-inc.github.io/smallest-self-host
helm install electron smallest-self-host/electron -n electron --create-namespace -f electron.yaml
```

The first start downloads the model and loads it, which takes 15 to 20 minutes. The notes Helm prints show how to watch it, read your API key, and send a first request; `helm test electron -n electron` sends one.

Your apps call `http://electron-router.electron.svc:8000/v1/chat/completions` with `Authorization: Bearer <API key>`, as they would the OpenAI API, with `"model": "electron"`.

## Storage

Where the model is kept decides how often it is downloaded. Set `engines.storage.mode`:

| Mode | For | Downloads |
| --- | --- | --- |
| `node` (default) | Nodes with several GPUs | Once per node, into `engines.storage.node.path` on the node |
| `perEngine` | One GPU per node | Once per engine, into a volume from `engines.storage.perEngine.storageClass` (100 GiB by default) |
| `shared` | A ReadWriteMany volume all GPU nodes mount: EFS, NFSv4, CephFS | Once in all, onto `engines.storage.shared.claimName`, a PVC you create |

The shared volume's file locks must work, so not NFS mounted with `nolock`. Whatever the mode, the engines on a node load one at a time (`engines.loadLock`), so its RAM never holds two decrypted copies; nodes load in parallel.

`node` mode, the load lock and the router's session handover use directories on the node (hostPath), and short init steps that run as root to hand them to their user. Where your cluster's policy forbids that (Pod Security `restricted`), use `perEngine` or `shared` with `engines.loadLock.enabled: false` and `router.sessionHandover.enabled: false`, and give each node room for every engine on it loading at once. On an NFS export with `root_squash` (the default), the init step can't hand over the shared volume: export it with the engine's user (uid 10001) owning the directory.

A StatefulSet's volume claims can't be edited in place, so `engines.storage.perEngine.*` and `licenseProxy.storage.*` are fixed once installed; to change them, delete the StatefulSet (its volumes stay), then upgrade.

## The API key

Left empty, `apiKey` is generated at install and kept across upgrades and uninstalls. To choose it, set `apiKey`. If you deploy with a tool that renders the chart without reading the cluster (Argo CD), create the keys Secret yourself, under a name of your own, and set `keysSecretRef`; otherwise every sync would generate new keys:

```bash
kubectl -n electron create secret generic electron-api-keys \
  --from-literal=api-key="$(openssl rand -hex 24)" \
  --from-literal=vllm-api-key="$(openssl rand -hex 24)" \
  --from-literal=proxy-token="$(openssl rand -hex 24)"
```

Pods read the keys when they start. A change to `apiKey` or `global.licenseKey` restarts the pod that uses it; after changing a Secret you made yourself (`keysSecretRef`, `global.licenseKeySecretRef`), restart them. Rotate only `api-key` (and the licence key): a new `vllm-api-key` or `proxy-token` stops the engines answering until every one of them has restarted.

```bash
kubectl -n electron rollout restart deployment/electron-router statefulset/electron-engine statefulset/electron-license-proxy
```

## Reaching it from outside the cluster

`router.service.type: LoadBalancer`, or `router.ingress.enabled: true`. Replies can take minutes under load and stream for as long, so raise the idle and read timeouts of whatever sits in front: for ingress-nginx, `nginx.ingress.kubernetes.io/proxy-read-timeout: "600"` and `proxy-send-timeout: "600"`; for an AWS load balancer, an idle timeout of 600 seconds.

## Upgrades

Each chart version installs one Electron release. To upgrade, update the repository and upgrade to the newest chart, or name one with `--version`; going back is the same command with the older version:

```bash
helm repo update
helm upgrade electron smallest-self-host/electron -n electron --reset-then-reuse-values
```

An upgrade restarts only what the release changed: the router when its image is new, the engines when their image, model or settings are new, and the license-proxy every time (seconds; serving carries on). A new model is downloaded by each engine as it restarts, so read the release notes for its size. `--reset-then-reuse-values` (Helm 3.14 and later) keeps your values and takes the new chart's defaults for the rest; `--reuse-values` would also keep the old defaults, which a newer chart may not work with. With values in a file, `-f electron.yaml` works the same.

The engines are replaced one at a time, so the others keep serving; each reloads in a few minutes. With one engine the API stops serving while it reloads. Changing `engines.storage.mode` to or from `perEngine` changes the engines' volume claims, which Kubernetes won't edit in place: delete the engine StatefulSet first (`kubectl -n electron delete statefulset electron-engine`), then upgrade. Engines stop meanwhile; the model stays where it was kept. The router is replaced without dropping a request: the new router starts and is serving before the old one leaves, the old one finishes its live replies (up to 10 minutes), and conversations keep their engine and its cache. For that, the router saves its sessions in `router.sessionHandover.path` on its node, and the new router is placed on the same node when there is room.

## When it doesn't serve

The router answers with a code saying why:

| Code | Meaning |
| --- | --- |
| `licence_starting` | The licence is being checked with smallest.ai; a minute at most |
| `licence_suspended`, `licence_expired`, `licence_invalid` | The licence can't be used; engines unload |
| `licence_not_entitled` | Your organization's plan doesn't include Electron on-prem |
| `no_credits` | Out of credits: top up in the console. Engines unload after 24 hours |
| `licence_unreachable` | smallest.ai hasn't been reachable for an hour: check outbound HTTPS |
| `licence_unavailable` | The license-proxy pod isn't answering |
| `usage_unbilled` | smallest.ai hasn't been able to bill this install's usage for a day: contact smallest.ai |
| `service_unavailable` | No engine is ready yet: they are downloading or loading |

`GET /status` on the router (with the API key) shows the licence and how many engines are ready.

The license-proxy is one pod with a volume (its install id and the usage not yet billed). If its node fails, Kubernetes leaves it terminating, and the router refuses requests about 2 minutes later with `licence_unavailable`. Run it on a stable node (`licenseProxy.nodeSelector`, not spot). To move it off a dead node: `kubectl -n electron delete pod electron-license-proxy-0 --force`, after the node is really gone, or with Kubernetes's non-graceful node shutdown.

## Uninstall

`helm uninstall electron -n electron` leaves the keys Secret and the volumes: the license-proxy's holds usage not yet billed, so keep it until the license-proxy has reported (or reinstall to send it). Models kept on the nodes (`engines.storage.node.path`) are files you remove yourself.

## Monitoring

The install has one scrape target with no key: the `<release>-metrics` Service, port 9090, `/metrics`. It is separate from the API Service, so exposing the API doesn't expose it; keep it inside your network.

| Metrics | From |
| --- | --- |
| `electron_licence_*`: `serving`, `state{status,reason}`, `credits`, `credit_hours_left`, `last_answer_age_seconds`, `grace_left_seconds` | The license-proxy: the licence as smallest.ai last answered |
| `electron_usage_*`: `tokens_total{kind}`, `requests_total`, `unbilled_age_seconds`, `batches_pending` | The license-proxy: what the engines reported for billing, and whether smallest.ai has charged it |
| `electron_router_*`: requests by status, time to first token, request duration, tokens, engines ready and expected, requests in flight per engine | The router |
| `vllm:*`, labelled `electron_engine` with the engine's name: requests running and waiting, KV-cache use, prefix-cache hits, tokens | Each engine's vLLM |
| `electron_scrape_up{source}` | 1 for each part the router could read; 0 means that engine or the license-proxy didn't answer |

With the Prometheus Operator (kube-prometheus-stack), set `metrics.serviceMonitor.enabled: true` and give `metrics.serviceMonitor.labels` what your Prometheus selects ServiceMonitors by, often `release: <its release name>`. Otherwise add a scrape job for `electron-metrics.electron.svc:9090`.

For Grafana, import `grafana/dashboards/electron-dashboard.json` from this repository and pick your Prometheus: the licence and billing, traffic, and each engine, with each panel saying what it shows and what to do about it. With several installs, choose one by its scrape job at the top.

Worth alerting on: `electron_licence_serving == 0` (the install is refusing requests: `electron_licence_state` says why), `electron_licence_credit_hours_left < 24`, `electron_licence_last_answer_age_seconds > 1800` (this server can't reach smallest.ai; it stops serving after an hour), `electron_usage_unbilled_age_seconds > 43200` (engines stop after a day), `electron_router_decode_pods_ready < electron_router_decode_pods_desired`, and `electron_scrape_up == 0`.

Logs (`kubectl logs`): the router writes one JSON line per request (its id, timings, tokens, status and the engine that served it), and the engines and the license-proxy write plain lines about loading, the licence and billing. None of them logs message content, API keys or the licence key.

## Values

| Value | Default | |
| --- | --- | --- |
| `global.licenseKey`, `global.licenseKeySecretRef` | | Your licence key, or a Secret holding it as `license-key` |
| `global.imageCredentials`, `global.imageCredentialsSecretRef` | | quay.io credentials, or a `kubernetes.io/dockerconfigjson` Secret |
| `images.registry` | | A registry you mirror the images to, like `registry.example.com/smallestinc`; every image keeps its name, tag and digest, the init image's too |
| `images.init` | busybox, pinned | The router's init step, which prepares its session directory |
| `apiKey`, `keysSecretRef` | generated | See The API key |
| `engines.count` | 1 | Engines, one per GPU |
| `engines.gpu` | H200 | H100, H200 or RTX PRO 6000 |
| `engines.nodeSelector`, `tolerations`, `affinity`, `runtimeClassName` | | Where engines run |
| `engines.resources` | sized from the GPU | Memory and CPU per engine (the decrypted model plus 32 GiB requested); the GPU is always one |
| `engines.storage.*` | `node` | See Storage |
| `engines.loadLock.*` | enabled | See Storage |
| `router.service.*`, `router.ingress.*` | ClusterIP on 8000 | See Reaching it from outside the cluster |
| `router.discovery` | `kubernetes` | `kubernetes`: the router watches the engine pods, through a Role that reads pods and StatefulSets in this namespace. `static`: a fixed list of the engines, with no Role |
| `router.sessionHandover.*` | enabled | See Upgrades |
| `metrics.serviceMonitor.*` | disabled | See Monitoring |
| `licenseProxy.storage.*` | 1 GiB | The license-proxy's state: the install's id and usage not yet acknowledged |
