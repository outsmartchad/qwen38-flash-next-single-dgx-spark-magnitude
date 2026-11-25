# Qwen 3.8 Flash Next on one DGX Spark with Magnitude

Run the 180B-total / 6B-active Qwen 3.8 Flash Next locally with Magnitude’s GPU/RAM/SSD expert paging. This is a separate recipe from the TensorFold setup.

## Measured result

Measured on one NVIDIA DGX Spark (GB10, 128 GB unified memory) on 2026-11-25 with Magnitude’s CUDA engine, Q2_0 model, shared Q8_0 MTP head, and a fresh 64K-context benchmark process:

| Workload | Prompt | Output | Prefill | TTFT | Decode |
|---|---:|---:|---:|---:|---:|
| One request, cold 64K repeat prompt | 64,354 tokens | 256 tokens | **741.3 tok/s** | **86.92 s** | **72.9 tok/s median** |

Decode is the median of two valid requests (81.99 and 63.88 tok/s). Both requests used the same prompt digest. This is Magnitude’s repeat-prompt throughput workload, not a prose or coding-quality evaluation. Thinking was off; output was greedy and capped at 256 tokens. The benchmark’s tuning report warns that **292/299 (97.7%)** kernel units fell back to canonical defaults, so treat this as a fresh-tuning baseline rather than a fully tuned ceiling.

Magnitude’s published DGX Spark figure is 83 tok/s for its stated workload. Our measured median was lower; see [results and method](docs/results.md) for the exact comparison and raw data.

## Quick start

Install the current Magnitude CLI using its [official installation guide](https://docs.magnitude.dev/). Start its local service in the foreground:

```bash
magnitude serve
```

In another terminal, download and load this catalog model:

```bash
magnitude models pull qwen3.8-flash-next:gguf:q2
magnitude models load qwen3.8-flash-next:gguf:q2
```

Keep the service bound to loopback. Do **not** run `magnitude server setup` for this recipe; that command configures remote access. See [first chat and local API](docs/setup.md).

## Reproduce the benchmark

The exact run used Magnitude’s pinned inference source and the official harness. From this repository on the Spark:

```bash
./scripts/benchmark.sh
```

It uses a cold `repeat:64k` prompt, one request, greedy sampling, two valid measurements, speculative drafting enabled, and fresh kernel tuning. It writes a new run directory under `results/`. The upstream harness needs Git, Rust/Cargo, `uv`, and a working CUDA/NVRTC runtime; see [benchmark setup](docs/results.md#reproduce).

## What is in this repo

- [How it works](docs/how-it-works.md): model structure, quantization, MTP, and Magnitude’s memory tiers.
- [First chat and setup](docs/setup.md): install, loopback-only API smoke test, and request example.
- [Results and raw data](docs/results.md): methodology, per-pass data, tuning caveat, provenance, and reproduction command.
- [Troubleshooting](docs/troubleshooting.md): download, CUDA, memory pressure, API binding, and benchmark issues.
- [`raw/bench/`](raw/bench/): source benchmark report and machine-readable result files. Large captured JSONL files and the rendered prompt template are stored as lossless gzip; see [`raw/bench/ARTIFACTS.md`](raw/bench/ARTIFACTS.md).

## Sources

- [Magnitude benchmark page](https://magnitude.dev/benchmarks)
- [Magnitude source and docs](https://github.com/magnitudedev/magnitude)
- [ISTA-DASLab Q2_0 checkpoint](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF/tree/main/Q2_0)
- [GSQ paper](https://arxiv.org/abs/2604.18556) · [RCO paper](https://arxiv.org/abs/2605.00649)
