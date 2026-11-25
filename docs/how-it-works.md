# How Qwen 3.8 Flash Next runs through Magnitude

This guide follows the actual model artifact and serving path in this recipe. It separates the model’s learned computation from the inference engine’s memory-management strategy.

## 1. The model: a sparse mixture of experts

Magnitude’s catalog describes Qwen 3.8 Flash Next as **180B total parameters, about 6B active per token, 512 routed experts, and 10 experts selected per token**. “180B” is the total learned parameter inventory; it does not mean every token runs a dense 180B matrix. At a routed feed-forward block, a gate scores available experts and selects a small top-k set. Those selected expert networks process the token, and their outputs are combined. Shared attention and other shared layers still run for every token.

The 6B-active figure is a useful model-size shorthand, not an exact count of every operation or a promise that only 6B weights need storage. The checkpoint is 66.4 GB on disk. Because expert selection changes from token to token, many of those weights are needed over a request even though only a subset participates in each token.

Qwen’s model card and the associated technical reports are the source of architectural and training claims; Magnitude’s catalog provides the exact MoE counts used by its recipe. See the [Magnitude model listing](https://magnitude.dev/benchmarks), the [checkpoint files](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF/tree/main/Q2_0), and the quantization papers linked from the model repository.

## 2. Quantization: fitting the weight store

This recipe uses ISTA-DASLab’s **GSQ-RCO Q2_0** GGUF checkpoint. Quantization stores model values with fewer bits than their original floating-point representation, reducing file size and data movement at the cost of approximation error. “2-bit” describes the quantization family, not a literal two bits for every file byte: scales, metadata, embeddings, and other tensors add storage.

GSQ and RCO are separate methods described by their authors. GSQ groups weights and uses structured quantization decisions; RCO adds a calibration/optimization procedure intended to reduce output error. The exact published checkpoint is the source of truth for what was loaded here. This recipe does not claim equivalence to the original full-precision checkpoint.

The model’s auxiliary shared MTP head is distributed as **Q8_0**. That head proposes future tokens for speculative decoding; it is not the main 180B parameter model and it does not change the target model’s architecture into a different model.

## 3. Token generation and speculative decoding

For each generation step, the target model computes the next-token distribution. Magnitude’s MTP drafter proposes a short sequence; the target verifies the proposals in a batch. Accepted proposals allow more than one output token to be emitted per verification round, while rejected proposals fall back to ordinary target decoding. The measured run accepted 425 of 502 proposed tokens (84.7%). Acceptance varies with prompt and sampling settings; it is not a fixed speed multiplier.

The benchmark used greedy decoding, which selects the highest-probability token. Thinking was off. Therefore this is a controlled engine-throughput measurement, not a measurement of reasoning quality or a normal interactive prose response.

## 4. Magnitude’s GPU / RAM / SSD tiers

Magnitude’s approach is to keep shared layers and a useful working set of experts close to the GPU, place additional experts in system memory, and keep the remaining expert weights on SSD. The router identifies experts needed by each token. The runtime tries to predict upcoming expert use and prefetch weights through the storage hierarchy so the GPU has the data when it reaches that computation.

The Spark’s GB10 shares a unified memory pool with the CPU. “GPU memory,” “host RAM,” and “SSD” are still useful descriptions of placement and bandwidth, but the first two are not separate 128 GB pools that can simply be added together. Paging an expert from SSD or RAM costs time; cache hits and prefetch accuracy matter. A sparse model can therefore fit in a smaller device than a dense loading strategy would suggest, while its speed remains sensitive to expert locality and storage traffic.

The benchmark’s process-tree RSS peaked near 50 GiB. That is a sampled process memory metric, not a report of all system allocations and not a standalone GPU VRAM reading.

## 5. What the benchmark does and does not prove

The `repeat:64k` test feeds a fixed repeated passage and asks the model to continue with a short greedy completion. It tests long-prompt ingestion and decode in a repeatable way. It does not score answer correctness, code quality, tool use, multilingual ability, or conversation quality. The 72.9 tok/s result should therefore be read as one measured serving configuration under the exact conditions in [results](results.md).

## Sources

- [Magnitude benchmark and catalog](https://magnitude.dev/benchmarks)
- [Magnitude source repository](https://github.com/magnitudedev/magnitude)
- [ISTA-DASLab Q2_0 checkpoint files](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF/tree/main/Q2_0)
- [GSQ paper](https://arxiv.org/abs/2604.18556)
- [RCO paper](https://arxiv.org/abs/2605.00649)
