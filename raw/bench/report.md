# Serving bench

Host: spark-6154 · Cortex-X925 + Cortex-A725 · 121.688 GiB RAM · Linux 7.0.0-1025-nvidia

Status: **completed**

```sh
magnitude-bench job --inference /home/outsmartchad/.cache/magnitude-evaluation/outputs/d5bb3a407c23d17f-0bd87f38c1ce149e/src --model qwen3.8-flash-next:gguf:q2 --passes 2 --fresh-tuning --magnitude-device cuda --magnitude-binary /home/outsmartchad/.cache/magnitude-evaluation/outputs/d5bb3a407c23d17f-0bd87f38c1ce149e/target/release/magnitude-engine --magnitude-cache-dir /home/outsmartchad/.cache/magnitude-evaluation/runs/20261125T082049Z-bench-1eaa61/kernels --harness /home/outsmartchad/.cache/magnitude-evaluation/outputs/d5bb3a407c23d17f-0bd87f38c1ce149e/target/release/magnitude-render --template /home/outsmartchad/.cache/magnitude-evaluation/runs/20261125T082049Z-bench-1eaa61/inputs/f67f31e10d8a2109.json --artifacts /home/outsmartchad/.cache/magnitude-evaluation/runs/20261125T082049Z-bench-1eaa61/artifacts.json --output /home/outsmartchad/.cache/magnitude-evaluation/runs/20261125T082049Z-bench-1eaa61/bench --build-identity /home/outsmartchad/.cache/magnitude-evaluation/runs/20261125T082049Z-bench-1eaa61/bench/build.json
```

Recorded 2 / 2 planned measurements.

Outcomes: {'valid': 2}

| Target | Section | Concurrency | Template | Actual prompt tokens | Eligible / recorded | TTFT ms | Completion ms | Prefill tok/s | Decode tok/s | Drafts accepted |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| magnitude | context | 1 | repeat:64k | 64354 | 2 / 2 | 86,915.0 | 90,480.3 | 741.3 | 72.9 | 425/502 (84.7%) |

Latencies and phase rates above are medians; nearest-rank p95 latency is in summary.json.

Moby Dick repeat: each request repeats a Moby Dick passage back; no answer-quality scoring. EOS or reaching the output budget ends a valid measurement; actual lengths are in summary.json.

Truncation, protocol errors, timeouts and cancellation are excluded from latency and rates, and retained in outcome counts and accuracy.

MLX-VLM generation timing measures server token emission. Its phase rates are shown for inspection and must not be interpreted as native model-service ratios against other engines.

product comparison of each engine's serving of one catalog model

disabled; shared session history does not imply retained prefix reuse

Raw request streams, per-process memory samples, source identities and engine logs are retained alongside this report.

Process-tree RSS (includes loading; not isolated GPU allocation):

| Target | Pass | Ready GiB | Peak GiB |
| --- | ---: | ---: | ---: |
| magnitude | 1 | 38.55 | 50.25 |
| magnitude | 2 | 38.34 | 50.08 |

Elastic expert bank (experts' slots, from the engine's memory observations while serving):

| Target | Pass | Slots first → last | Range | Floor | Ceiling | Resizes seen | Latest resize |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| magnitude | block-0 | 512 → 512 | 512–512 | 14 | 512 | none | none |
| magnitude | block-1 | 512 → 512 | 512–512 | 14 | 512 | none | none |

## Tuning health

> **WARNING: High tuning fallback rate** — 292/299 (97.7%) units fell back to canonical default (7/299 qualified, 46 expired).

Worst `default` vs. `tuned` gaps (>1.25×; 1 total):

| Unit | Default µs | Best µs | Ratio | Status |
| --- | ---: | ---: | ---: | --- |
| `stream_mix_up [UW=bf16,NW=bf16,A=bf16,M=65..]` | 572.9 | 341.7 | 1.68× | qualified |

Slowest untuned / fallback units:

| Unit | Reason | Median µs | Weight | Weighted ms |
| --- | --- | ---: | ---: | ---: |
| `stream_mix_down [NW=bf16,DW=bf16,IW=bf16,A=bf16,C=1,M=65..]` | Expired | 555.7 | 198.5 | 110.30 |
| `gated_delta_chunk [RN=bf16,A=bf16]` | Canonical | 93.9 | 844.3 | 79.28 |
| `routed_gate_up [EGW=q2g64@mma16,EUW=q2g64@mma16,A=bf16,M=4..17]` | Canonical | 160.2 | 434.1 | 69.56 |
| `routed_gate_up_part [EGW=q2g64@mma16,EUW=q2g64@mma16,A=bf16,M=4..17]` | Expired | 156.8 | 434.1 | 68.06 |
| `stream_mix_up [UW=bf16,NW=bf16,A=bf16,M=1..9]` | Canonical | 35.4 | 1,891.3 | 66.87 |
