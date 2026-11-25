# Troubleshooting

## The model is not in the model list

Start `magnitude serve` first, then run the exact catalog ID:

```bash
magnitude models pull qwen3.8-flash-next:gguf:q2
magnitude models list
```

If the current catalog no longer recognizes the ID, check Magnitude’s [benchmark page](https://magnitude.dev/benchmarks) and model catalog, then record the changed ID and checkpoint revision before benchmarking.

## CUDA or NVRTC initialization fails

Confirm the Spark driver and CUDA runtime are healthy (`nvidia-smi`). The benchmark engine needs the NVRTC libraries supplied by the Magnitude runtime. If building the pinned upstream source manually, make the runtime library directory discoverable to the build/run process; see `scripts/benchmark.sh`.

## High memory pressure

Qwen’s quantized checkpoint is still about 66.4 GB on disk, and runtime memory includes expert caches, activations, context/KV state, and the operating system. Close other model servers before measuring. Do not treat the model file size as a full memory estimate.

## Local API does not respond

```bash
ss -ltnp 'sport = :10100'
curl --fail-with-body http://127.0.0.1:10100/inference/v1/models
```

Start `magnitude serve` if the local port is absent. Keep API calls on `127.0.0.1`; do not use `magnitude server setup` for a loopback-only run.

## Benchmark is much slower than the published 83 tok/s

First verify the checkpoint, engine revision, prompt size, empty prompt cache, output budget, drafting mode, and thermal state. This recipe measured 72.9 tok/s median over two valid 256-token generations. The harness reported 97.7% canonical tuning fallback. Compare raw run artifacts before attributing a difference to the model or hardware.

## An individual run fails

Read the run’s `events.jsonl`, `logs/`, and `summary.json`. Invalid requests are retained by the harness but excluded from timing. Preserve the run directory when filing an issue; do not report only the fastest pass.
