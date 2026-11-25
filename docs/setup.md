# Install and make a first local request

## Install

On the DGX Spark, install Magnitude using its current [official CLI instructions](https://docs.magnitude.dev/). Keep the CLI version recorded when benchmarking; this recipe’s measured source build was tied to inference commit `78c92e4f21e38f9528f21e09c5e43936a04b6b0d`.

Start the local service in a terminal and leave it running:

```bash
magnitude serve
```

The default local inference API is `127.0.0.1:10100/inference/v1`. Keep that loopback binding. Do not run `magnitude server setup` when you want a local-only service.

In another terminal:

```bash
magnitude models pull qwen3.8-flash-next:gguf:q2
magnitude models load qwen3.8-flash-next:gguf:q2
```

Check that the listener is loopback-only:

```bash
ss -ltnp 'sport = :10100'
```

The listener should show `127.0.0.1:10100`, not `0.0.0.0:10100` or a Tailscale/LAN address.

## First chat smoke test

```bash
curl --fail-with-body http://127.0.0.1:10100/inference/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.8-flash-next:gguf:q2","messages":[{"role":"user","content":"Reply with exactly SPARK_OK."}],"temperature":0,"max_tokens":32}'
```

This is only a connectivity smoke test. It is not part of the published 64K throughput result.

## Stop

Stop the foreground service with `Ctrl-C`. It should not bind a public interface unless a separate remote-server configuration has been explicitly enabled.
