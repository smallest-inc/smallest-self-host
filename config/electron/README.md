# Electron with Docker Compose

Electron, smallest.ai's voice-agent LLM, on one GPU server. It serves the OpenAI-compatible Chat Completions API (`model: "electron"`) from one port: a router in front of one engine per GPU. Prompts and answers stay on your server.

## Before you start

- A licence key: create one in the smallest.ai console, under Settings, then Licenses
- Registry credentials from smallest.ai, with this server logged in: `docker login quay.io`
- RTX Pro 6000, H100 or H200 GPUs (one type per server)
- The NVIDIA driver, Docker with Compose v2, and the NVIDIA Container Toolkit
- RAM: about 32 GB per engine, plus one decrypted model while an engine loads: 22 GB (RTX) or 34 GB (H100/H200)
- Disk under Docker's data folder for two versions of the model (the one running, and the next during an upgrade) and vLLM's compile cache: about 55 GB (RTX) or 80 GB (H100/H200)
- Outbound HTTPS to smallest.ai: the licence is checked every 2 minutes, and the model downloads once per version

## Install

Get this folder at a release, then run setup in it:

```bash
git clone --depth 1 --branch electron-<version> https://github.com/smallest-inc/smallest-self-host.git
cd smallest-self-host/config/electron
./electron setup
```

It checks the server, picks the free GPUs and a free port (asking when there's a choice), takes your licence key and sets your API key, checks the licence with smallest.ai, writes the configuration, and offers to start. Starting shows each engine's progress until the API is ready; the first start downloads the model once.

## Use it

Point any OpenAI client at the server:

| | |
|---|---|
| base URL | `http://<server>:8000/v1` (the port `setup` chose) |
| API key | `ELECTRON_API_KEY` in `.env` |
| model | `electron` |

## Commands

| Command | |
|---|---|
| `./electron setup` | Check the server and write the configuration. Rerun it after adding or removing GPUs; it keeps your keys. |
| `./electron start` | Start, and watch the engines load. Engines load one at a time, a few minutes each. |
| `./electron status` | The API address and each engine's state; a problem shows its reason. `--watch` keeps it live. |
| `./electron test` | Send a test request through the API. |
| `./electron logs` | Follow the logs; `./electron logs engine-0` for one engine. |
| `./electron upgrade` | Move to the latest release; `./electron upgrade 1.0` moves to that one, to go back. |
| `./electron stop` | Stop. The model and its cache are kept, so the next start is quicker. |

`./electron <command> --help` shows a command's options, such as `setup --gpus 0,1` to use only some GPUs and `setup --yes` for scripted installs. It is all plain Docker Compose underneath: `docker compose ps`, `logs` and `down` work too. Never `down -v`: it deletes the model and the licence volume, which holds usage not yet billed.

## Upgrades

```bash
./electron upgrade
```

It downloads the newest release's files into this folder, shows what the release changes, and asks before upgrading. Your settings and keys in `.env` are kept. Only what the release changed restarts:

- the router, when the release has a new one: it finishes the replies in progress (up to 2 minutes), then the API pauses for a few seconds
- the engines, when the release has a new engine or model: a new model is downloaded first while the engines keep serving, then the engines reload one at a time, each waiting for the one before to serve again (with one engine, the API pauses while it reloads)
- the license-proxy, every time, in seconds; serving carries on

If an upgrade stops partway (a download fails, an engine doesn't come back), fix the cause and run the same command again: it finishes what it hadn't restarted. To go back, name the version you were on: `./electron upgrade 1.0`. The model you were on is kept on disk, so going back doesn't download it again. The releases and their notes are at https://github.com/smallest-inc/smallest-self-host/releases.

## When something is wrong

`./electron status` names the problem. An engine that can't start because of the server, such as the wrong GPU or too little RAM, says why and waits instead of restarting over and over. Fix the cause, then run `./electron start`.

The licence is checked every 2 minutes. While it is suspended or expired, or out of credits, requests get a 403 that says why. Out of credits, engines stay loaded for 24 hours so serving resumes as soon as you top up; otherwise they unload, and load again on their own once the licence is valid. If this server can't reach smallest.ai, it keeps serving for an hour.

## Monitoring

The install has one scrape target with no key: `http://<server>:9090/metrics` (the port `setup` chose, `ELECTRON_METRICS_PORT` in `.env`; `./electron status` shows it). Keep that port inside your network: Docker's published ports bypass ufw and firewalld, so to keep it to this server set `ELECTRON_METRICS_HOST=127.0.0.1` in `.env` and `./electron start`. Add it to your Prometheus:

```yaml
scrape_configs:
  - job_name: electron
    static_configs:
      - targets: ["<server>:9090"]
```

| Metrics | From |
| --- | --- |
| `electron_licence_*`: `serving`, `state{status,reason}`, `credits`, `credit_hours_left`, `last_answer_age_seconds`, `grace_left_seconds` | The license-proxy: the licence as smallest.ai last answered |
| `electron_usage_*`: `tokens_total{kind}`, `requests_total`, `unbilled_age_seconds`, `batches_pending` | The license-proxy: what the engines reported for billing, and whether smallest.ai has charged it |
| `electron_router_*`: requests by status, time to first token, request duration, tokens, engines ready and expected, requests in flight per engine | The router |
| `vllm:*`, labelled `electron_engine` with the engine's name: requests running and waiting, KV-cache use, prefix-cache hits, tokens | Each engine's vLLM |
| `electron_scrape_up{source}` | 1 for each part the router could read; 0 means that engine or the license-proxy didn't answer |

For Grafana, import `grafana/dashboards/electron-dashboard.json` from this repository and pick your Prometheus.

Worth alerting on: `electron_licence_serving == 0` (the install is refusing requests: `electron_licence_state` says why), `electron_licence_credit_hours_left < 24`, `electron_licence_last_answer_age_seconds > 1800` (this server can't reach smallest.ai; it stops serving after an hour), `electron_usage_unbilled_age_seconds > 43200` (engines stop after a day), `electron_router_decode_pods_ready < electron_router_decode_pods_desired`, and `electron_scrape_up == 0`.

Logs (`./electron logs`): the router writes one JSON line per request (its id, timings, tokens, status and the engine that served it), and the engines and the license-proxy write plain lines about loading, the licence and billing. None of them logs message content, API keys or the licence key.

## What runs

| Service | |
|---|---|
| `router` | The API, and the install's metrics on their own port. Checks the API key and keeps each conversation on the engine that holds it. |
| `engine-N` | vLLM on one GPU. Gets its key from the license-proxy, downloads the model once per server, decrypts it into RAM, loads it, then deletes the decrypted copy. |
| `license-proxy` | Checks the licence with smallest.ai and reports the tokens served. The only part that holds the licence key or talks to smallest.ai. |

| File | |
|---|---|
| `compose.yaml`, `engine.yaml` | The services. Don't edit them; `setup` writes what is specific to this server. |
| `release.env` | The release this folder holds: its images and model. `setup` and `upgrade` copy it into `.env`. |
| `.env` | Settings and keys (licence, API and internal keys), written by `setup`. Keep it private. |
| `compose.override.yaml` | This server's engines, one per GPU, written by `setup`. |
