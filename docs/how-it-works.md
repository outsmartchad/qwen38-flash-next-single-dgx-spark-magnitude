# How Qwen3.8 Flash Next runs on one DGX Spark

This recipe combines Qwen's model architecture, ISTA-DASLab's quantized weights, and Magnitude's CUDA execution. The architecture defines the math. The checkpoint stores approximations of the learned numbers. The engine schedules that math and chooses where those numbers and the conversation state live on the Spark.

## 1. From a message to one new token

1. The chat template converts messages and roles into model input. The tokenizer breaks that input into token IDs. An embedding table turns each ID into a vector.
2. **Prefill** processes the input tokens in chunks. Each decoder block mixes information from prior tokens and transforms each token's vector. The engine retains the history or recurrent state each block needs.
3. At the end of prefill, the output projection gives a score for each possible next token. The sampler selects a token from those scores. Greedy decoding selects the highest scoring token.
4. **Decode** uses that output to generate the next token and updates the state. Reusing state makes the next step much cheaper than running the whole conversation again. With MTP, one verification round can emit several tokens.

TTFT measures the wait before any generated token arrives. Decode tok/s describes how quickly generation proceeds after the prompt has been processed. Faster decode does little to shorten a long wait if the prompt itself dominates TTFT.

## 2. What 180B total and 6B active mean

| Part | What it does |
| --- | --- |
| 125B language trunk, about 6B active | Applies 48 decoder blocks and selects experts for each token. |
| 51B n-gram embedding weights | Looks up learned features for short token sequences. A few rows are read per lookup. |
| 4B MTP weights in the original model | Predicts additional likely tokens so the target can verify a group together. |

The roughly 180B label includes the trunk, n-gram embeddings and the original MTP component. It counts weights that can be useful across requests. At a routed feed-forward block, a learned router ranks **512 routed experts**, selects **10**, and combines their outputs with one shared expert. An expert is a small neural network for a token's vector. Routing changes with the token and the layer. The shared mixer, normalization, router and output projection still do work each step. [Qwen model card](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)

The n-gram component adds learned lookups for a token and nearby tokens. A hash maps bigrams and trigrams into a large table. The retrieved rows are gated into the residual streams near the beginning of the network. This scales stored knowledge differently from adding more dense matrix multiplications.

## 3. The 48 decoder blocks

There are 12 groups of four blocks. Each group has three **Gated DeltaNet** blocks and one **Qwen Sparse Attention (QSA)** block. Every block follows its mixer with a mixture-of-experts feed-forward network.

- **Gated DeltaNet** compresses prior information into a recurrent state per layer. A learned gate decays old information, and a delta update writes what the current token adds. Decode can update that summary without reading every earlier token's key and value. Chunked kernels process blocks of prompt tokens during prefill.
- **QSA** keeps a history that a new token can query directly. A smaller indexer scores blocks of prior tokens and selects a subset for the expensive attention calculation. Qwen's config uses a 512-block budget, equivalent to 2,048 tokens. The engine still stores history so later queries can choose different blocks.
- **Gated residual streams** carry four parallel paths between sublayers. Learned gates choose what each mixer or feed-forward block reads and writes. A residual path allows information to survive while the block computes an update.

The KV cache belongs to the attention layers. The recurrent layers keep a different form of session state. The engine also reserves memory for temporary buffers and room in the context for generated tokens, which is why a model's advertised maximum context and our engine setting are different values. The official checkpoint has a vision encoder. This recipe launches with `--no-projector` to match the text benchmark. [Original configuration](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/main/config.json) · [Magnitude family implementation](https://github.com/magnitudedev/magnitude/blob/78c92e4f21e38f9528f21e09c5e43936a04b6b0d/inference/engine/families/qwen4exp/src/lib.rs)

## 4. What Q2_0 and Q8_0 change

The served target is ISTA-DASLab **GSQ-RCO Q2_0** in split GGUF files. GGUF is the container for tensor data, tensor types, architecture metadata and tokenizer information. The quant label primarily describes the cheap weight representation used by large parts of the model. Other tensors, block scales and file metadata contribute to the actual size.

- **GSQ** fits quantized values and group scales to limit the error from low precision.
- **RCO** optimizes assignments under a fixed compression budget. It helps decide where spending extra bits does the most good in a mixed-precision checkpoint.
- **Q8_0** is the quantization of this recipe's separate shared MTP head. The head uses target features to draft likely subsequent tokens. The engine verifies proposals with the Q2_0 target. On this repeat workload 425 of 502 timed proposals were accepted. The number depends on prompt and sampling.

Both our [TensorFold recipe](https://github.com/outsmartchad/qwen38-flash-next-single-dgx-spark-tensorfold) and this recipe serve the same Qwen model family, about 6B active language parameters per token. TensorFold uses NVIDIA's NVFP4 weights, another inference engine and a different chat benchmark. A throughput comparison between them gives no basis for a quality score. [Target checkpoint](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF/tree/ed59f92082b1e93c0e96d60a8b11aab089b52f09/Q2_0) · [GSQ paper](https://arxiv.org/abs/2604.18556) · [RCO paper](https://arxiv.org/abs/2605.00649)

## 5. How Magnitude places the model on GB10

The Spark's CPU and GPU share a 128 GB physical memory pool. GPU kernels still need the tensors in a usable layout and memory placement. Magnitude can keep the shared blocks resident, allocate an expert bank for commonly needed weights, and stage missing experts from the host or the SSD. The layer router's top-k decision tells the engine which expert weights the token needs. Magnitude can overlap some reads and staging work with compute.

GPU work, prompt state, n-gram tables and the expert bank all need space. The engine budget can change how much fits while the model runs. In this Qwen run, the sampled expert bank stayed at **512 slots** and reported **zero disk-resident expert bytes** in the recorded allocation snapshots. The measurements demonstrate local inference with this placement policy. They do not isolate a benefit from SSD paging. [Allocation samples](../raw/bench/allocations.jsonl) · [Raw report](../raw/bench/report.md)

## 6. How this recipe starts and measures it

`prepare` acquires the pinned target and drafter through the same catalog that the benchmark uses. It builds the pinned native engine and stages NVRTC, the NVIDIA runtime compiler Magnitude uses to form CUDA kernels. `serve` sends the GGUF shards and the draft file to that binary, limits the served context to 64,768 tokens and binds to loopback. `smoke` checks readiness and reads a generated reply through the local OpenAI-compatible API.

The benchmark uses its own native server on a temporary loopback port. It evaluates a cold 64K repeat prompt with thinking off and reports 256 generated tokens. We published both valid passes, memory samples and the tuning trace. The large number of default kernel fallbacks is an observation about this run. [Setup](setup.md) · [Benchmark method and results](results.md) · [Troubleshooting](troubleshooting.md)
