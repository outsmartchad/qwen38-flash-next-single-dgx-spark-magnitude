# Benchmark results

## Measured on November 25, 2026

One NVIDIA DGX Spark, GB10 CUDA, 128 GB unified memory (121.69 GiB visible to Linux). These are two separate single-request passes of Magnitude's `repeat:64k` *Moby Dick* fixture. Both used **64,354 actual input tokens, zero cached input tokens and 256 generated tokens** with greedy decoding and thinking off.

| Eligible pass | Decode tok/s | Prefill tok/s | Client TTFT | Peak process-tree RSS |
| --- | ---: | ---: | ---: | ---: |
| 1 | 81.99 | 739.0 | 87.18 s | 50.25 GiB |
| 2 | 63.88 | 743.6 | 86.65 s | 50.08 GiB |
| Median | 72.94 | 741.3 | 86.92 s | — |

The two medians summarize the repeatability of the workload. The card uses the fastest valid **decode** pass and pairs it with that pass's prefill and TTFT. Full traces retain the warmups and individual completions. [Per-request records](../raw/bench/results.jsonl) · [Upstream summary](../raw/bench/summary.json) · [RSS by pass](../raw/bench/footprints.jsonl)

## What the benchmark measures

1. **Prompt and engine setup.** The native harness renders a repeat instruction using the model's chat template. The selected context class is 65,536 tokens. The harness served a 64,768-token capacity with one request at a time and disabled prompt-prefix reuse. The model files were already downloaded, and each pass launched a fresh native inference process and ran a warmup before the timed prompt.
2. **Prefill.** Magnitude reports input tokens processed divided by native prompt computation time. TTFT is measured by the client from sending the request until the first generated token arrives. TTFT also includes transport and processing outside the native prefill timer.
3. **Decode.** The rig divides its native `predicted_n` by `predicted_ms / 1000`. The stream's convenience field `predicted_per_second` uses a slightly different convention. Use the rig's formula to reproduce the table from `results.jsonl`.
4. **RAM.** RSS sums sampled resident memory of the engine process tree, including load. Some memory can be shared and some GPU, file-cache and system allocations are accounted for separately. RSS entries are suitable for comparing the recorded footprint under this workload. They are separate from installed capacity and a runtime allocation limit.

**MTP.** The shared Q8_0 head proposed 252 tokens and the target accepted 219 in pass 1. Pass 2 accepted 206 of 250. Across the two timed requests this is **425/502 (84.7%)**.

The run used a fresh tuning cache. The report recorded **292/299 (97.7%)** dispatch units falling back to default configurations. This documents one installation and workload. Kernel tuning, prompt, concurrency, quantization, or engine changes can move the numbers. [Native report and tuning breakdown](../raw/bench/report.md)

## Reproduce

Follow [the setup instructions](setup.md), then run `./scripts/benchmark.sh` on the Spark with only this inference workload active. Inspect `runs/<run-id>/bench/report.md` for **2 eligible timed passes**. The rig excludes invalid outcomes and marks captured warmups separately. Keep `summary.json`, `results.jsonl`, `requests.jsonl`, logs, tuning, memory and allocation traces with any measurement you share. [Raw archive map](../raw/bench/ARTIFACTS.md)

| Provenance | Observed setting |
| --- | --- |
| Engine source | [`78c92e4f21e38f9528f21e09c5e43936a04b6b0d`](https://github.com/magnitudedev/magnitude/tree/78c92e4f21e38f9528f21e09c5e43936a04b6b0d) |
| Catalog target | `qwen3.8-flash-next:gguf:q2` at `ed59f92082b1e93c0e96d60a8b11aab089b52f09` |
| Catalog target identity | `69820c02ec7d0b45ef2ebb19d6620299db749fe2aded7f39f93c6b88b199b720` |
| Drafter | [Shared Q8_0 MTP head](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF/tree/084c631ac221016019d6e0a863afe92d90edd3b0/MTP), SHA-256 `5ff54097406a905cf3a724c709124ceb0e3e10235ee862298969e91c96fa96e6` |
| CUDA runtime compiler | NVIDIA NVRTC 12.9 |
| Mode | Loopback HTTP, text only, prefix cache disabled |
| Record | [`result.json`](../raw/bench/result.json) · [`host.json`](../raw/bench/host.json) · [`magnitude-runtime.json`](../raw/bench/magnitude-runtime.json) |

Magnitude's [published Spark benchmark](https://magnitude.dev/benchmarks) lists **83 tok/s decode** for this model with a 64K context and speculative decoding. The local passes are the numbers above. There is enough information to compare the workload class and quant, while the engine revision, tuning cache and exact run conditions can still differ. This workload measures inference throughput. It provides no answer-quality score or interactive prose or concurrency result for this quant.

## Earlier local chat run with Q4

We also ran thinking-on prose and 32K/128K cold prefill on this same Spark on November 22 with **Magnitude 0.2.17**, catalog `qwen3.8-flash-next:gguf:q4` and MTP. It used a different checkpoint and workload from the Q2_0 card. These decode rows use the highest aggregate of three waves at each concurrency, with TTFT and median per-request rates taken from the same wave. Repeated short prompts could hit a cached prefix. TTFT includes the first streamed reasoning or answer token.

| Concurrent users | Aggregate decode tok/s | Median per user tok/s | TTFT |
| ---: | ---: | ---: | ---: |
| 1 | 41.06 | 41.06 | 59 ms |
| 2 | 49.27 | 25.60 | 112 ms |
| 3 | 54.78 | 18.38 | 176 ms |
| 4 | 48.47 | 12.51 | 199 ms |
| 5 | 49.00 | 10.19 | 251 ms |

| Cold prefill | Actual prompt tokens | Prefill tok/s | TTFT |
| --- | ---: | ---: | ---: |
| 32K | 32,767 | 840.94 | 39.06 s |
| 128K | 131,056 | 665.85 | 196.99 s |

Both long prompts reported zero cached input tokens and returned the expected audit code. [Archived Q4 request and timing data](../raw/q4-chat-2026-11-22.json)
