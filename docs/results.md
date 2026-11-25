# Benchmark results and method

## Summary

| Requests | Prompt tokens | Output tokens | Decode median | Prefill median | TTFT median |
|---:|---:|---:|---:|---:|---:|
| 1 at a time | 64,354 | 256 | **72.9 tok/s** | **741.3 tok/s** | **86.92 s** |

The two individual decode results were 81.99 and 63.88 tok/s. The per-request latency and phase rates are measured by the native Magnitude model service; results are not inferred from wall-clock time around a client. Cold means a new benchmark engine process with prompt-cache reuse disabled; the model weights themselves remain downloaded locally.

## Workload and caveats

- DGX Spark with NVIDIA GB10 and 128 GiB unified system memory; Magnitude engine used CUDA.
- Catalog model `qwen3.8-flash-next:gguf:q2`, ISTA-DASLab GSQ-RCO Q2_0 checkpoint, plus the shared Q8_0 MTP head.
- Official harness template `repeat:64k` rendered to 64,354 input tokens; two sequential, single-request measurements, each with 256 output tokens.
- Greedy output, thinking disabled, MTP drafting enabled. 425 of 502 proposed draft tokens were accepted (84.7%).
- No prose, coding, tool-call, Chinese, or answer-quality scoring was performed in this benchmark. Do not compare these values directly with our TensorFold prose runs or claim quality equivalence.
- Magnitude’s published DGX Spark row reports 83 tok/s decode and 1,185 tok/s prefill for Qwen 3.8 Flash Next. This run measured 72.9 and 741.3 respectively under the harness and tuning state recorded here. The difference is real in this run; it does not establish that either result is universally reproducible.
- Fresh tuning ended with 292/299 units at canonical fallback (97.7%), 7 qualified and 46 expired. The result is a reproducible fresh-tuning baseline, not evidence that every kernel was optimized.
- Process-tree RSS peaked at 50.25 GiB and 50.08 GiB across the two passes. This measures the captured process tree; it is not a claim of total Spark RAM use or GPU-only allocation.

## Reproduce

The run used Magnitude inference source commit `78c92e4f21e38f9528f21e09c5e43936a04b6b0d`, two passes, a fresh tuning cache, CUDA, and the local host backend. The checked-in script pins the commit and invokes the same workload. It requires Git, Rust/Cargo, `uv`, Python tooling declared by Magnitude, and the CUDA/NVRTC runtime provided by the Spark image.

```bash
./scripts/benchmark.sh
```

The command reports the generated run ID and leaves the harness output under `results/<run-id>/bench/`. Keep the raw `report.md`, `result.json`, `summary.json`, events, tuning, and memory records together. Large text captures use lossless gzip. Large traces and the template are gzip-compressed losslessly; see [`raw/bench/ARTIFACTS.md`](../raw/bench/ARTIFACTS.md) for filenames and decompression instructions.

## Provenance

- Benchmark date: 2026-11-25 UTC.
- Magnitude source revision: `78c92e4f21e38f9528f21e09c5e43936a04b6b0d`.
- Model snapshot: ISTA-DASLab repository snapshot `ed59f92082b1e93c0e96d60a8b11aab089b52f09`.
- Shared drafter file SHA-256: `5ff54097406a905cf3a724c709124ceb0e3e10235ee862298969e91c96fa96e6`.
- Combined target shard identity SHA-256: `69820c02ec7d0b45ef2ebb19d6620299db749fe2aded7f39f93c6b88b199b720`.
- Raw report: [`../raw/bench/report.md`](../raw/bench/report.md); raw JSON: [`../raw/bench/result.json`](../raw/bench/result.json), [`../raw/bench/summary.json`](../raw/bench/summary.json).

## Published comparison

Magnitude’s [benchmark page](https://magnitude.dev/benchmarks) lists 83 tok/s decode and 1,185 tok/s prefill for this model on a DGX Spark. The site describes a 64K context, greedy output, one request, a short fixed output budget, speculative decoding, fresh engine processes, and native engine timing. Our harness follows its published repeat-64K approach and records actual prompt length and local environment in raw artifacts. Results can differ with engine revision, model artifact, compiler/kernel tuning, temperature, or test state.
