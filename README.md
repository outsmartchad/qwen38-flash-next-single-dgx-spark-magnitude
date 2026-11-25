# Qwen 3.8 Flash Next on one DGX Spark with Magnitude

Run the 180B-total / 6B-active Qwen 3.8 Flash Next locally with Magnitude's GPU, RAM, and SSD expert paging. This is a separate recipe from our TensorFold setup.

## Measured on DGX Spark

| Workload | Prompt | Output | Prefill | TTFT | Decode |
|---|---:|---:|---:|---:|---:|
| One request, cold 64K repeat prompt | 64,354 tokens | 256 tokens | **741.3 tok/s** | **86.92 s** | **72.9 tok/s median** |

Two valid greedy decode passes measured 81.99 and 63.88 tok/s. Thinking was off; this is a repeat-prompt throughput test, not a prose, coding, or quality evaluation. The fresh tuning report left 97.7% of kernel units on canonical fallback, so this is a baseline, not a tuned ceiling. Magnitude publishes 83 tok/s for its own stated setup; the measured gap and method are documented below.

## Run it locally

Install Magnitude from its [official guide](https://docs.magnitude.dev/), start the local service with magnitude serve, then run magnitude models pull qwen3.8-flash-next:gguf:q2 and magnitude models load qwen3.8-flash-next:gguf:q2. Keep the API bound to loopback; do not run magnitude server setup.

## Guides and data

- [How it works](docs/how-it-works.md)
- [Setup and first chat](docs/setup.md)
- [Benchmark method and results](docs/results.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Raw benchmark artifacts](raw/bench/)

The prompt template and large traces are losslessly gzip-compressed; see the raw artifact notes. Benchmarks ran on one GB10 DGX Spark with Q2_0 target weights and a shared Q8_0 MTP drafter.

## Sources

- [Magnitude benchmarks](https://magnitude.dev/benchmarks) · [Magnitude source](https://github.com/magnitudedev/magnitude)
- [Q2_0 checkpoint](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF/tree/main/Q2_0)
- [GSQ paper](https://arxiv.org/abs/2604.18556) · [RCO paper](https://arxiv.org/abs/2605.00649)
