# From a clean clone to the first chat reply

This recipe builds the Magnitude CUDA engine from the same [source revision](https://github.com/magnitudedev/magnitude/tree/78c92e4f21e38f9528f21e09c5e43936a04b6b0d) as the measured run and downloads the same catalog checkpoint. Its text API uses `127.0.0.1:10100/v1`.

## 1. Check the Spark

Use a GB10 DGX Spark running ARM64 Linux with a working NVIDIA driver. Reserve about **100 GB** of SSD space for the model packages, Rust builds and caches. The measured peak process-tree RSS was **50.25 GiB**. Pause other models when you are ready to load this one.

Install Git, curl, Python 3.11+, the standard Ubuntu build tools, [Rust via rustup](https://rustup.rs/) and [uv](https://docs.astral.sh/uv/getting-started/installation/). On Ubuntu, these are the system packages if you need them:

```bash
sudo apt install git curl python3 build-essential pkg-config libssl-dev iproute2
```

The checkout selects its Rust toolchain through `rust-toolchain.toml`. The benchmark harness uses Python 3.12 or newer, which uv can install. Verify that `cargo` and `uv` are on your shell's `PATH`.

```bash
git clone https://github.com/outsmartchad/qwen38-flash-next-single-dgx-spark-magnitude.git
cd qwen38-flash-next-single-dgx-spark-magnitude
./scripts/recipe.py doctor
```

## 2. Prepare the engine and model

```bash
./scripts/recipe.py prepare
```

The first run fetches Magnitude `78c92e4`, verifies NVIDIA's ARM64 SBSA NVRTC 12.9.86 archive, builds the native server and the two benchmark helper binaries, and acquires the catalog package through Magnitude's pinned catalog tool. It checks the acquired target and MTP identities against the run record. It can reuse a previously downloaded package in `~/.magnitude/models`.

- **Catalog ID**: `qwen3.8-flash-next:gguf:q2`
- **Target snapshot**: [`ed59f92`](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF/tree/ed59f92082b1e93c0e96d60a8b11aab089b52f09)
- **Draft model**: [Shared Q8_0 MTP head](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF/tree/084c631ac221016019d6e0a863afe92d90edd3b0/MTP), SHA-256 `5ff54097406a905cf3a724c709124ceb0e3e10235ee862298969e91c96fa96e6`
- **Recipe state**: `~/.cache/magnitude-spark-recipes`. Set `MAGNITUDE_RECIPE_CACHE` to the same absolute directory across commands to store the build elsewhere.
- **Build tools**: the pinned engine needs NVRTC 12.9 and its matching builtins. The default `prepare` stages both locally. You can also point `SEISMIC_NVRTC_DIRECTORY` at an existing copy.

## 3. Serve and make a local request

```bash
./scripts/recipe.py serve
```

Wait for Magnitude to print its serving URL. The foreground server uses CUDA, a 64,768-token context pool, 256 output tokens of request capacity, MTP, and text input. In a second Spark terminal, from the same checkout:

```bash
./scripts/recipe.py smoke
```

The smoke command checks the actual listener and asks `/health` for the expected model, context and draft method. It prints `SPARK_OK` only if the local model returns that text in a chat completion.

Clients can use the catalog ID above and the base URL `http://127.0.0.1:10100/v1`. Example:

```bash
curl --noproxy '*' --fail-with-body -sS http://127.0.0.1:10100/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.8-flash-next:gguf:q2","messages":[{"role":"user","content":"Explain unified memory in two sentences."}],"reasoning_effort":"none","temperature":0,"max_tokens":128}'
```

For an occupied port, use `serve --port 18907` and `smoke --port 18907`. The same option applies to `status`. To use the API from a different machine via SSH, forward a port to the loopback listener, then point your client at its local forwarded port.

## 4. Reproduce the measured run

Press Ctrl-C in the server terminal first. The benchmark owns its own temporary local model server.

```bash
./scripts/benchmark.sh
```

This runs the upstream native measurement job with the checked-in 64K template. It prices the GPU topology, prepares a fresh tuning cache, and launches two timed passes. Results land under `runs/<run-id>/bench/` and the topology record is beside that directory. Begin on an idle Spark. The original experiment also used the rig's thermal gate. See [results and raw data](results.md) for eligibility and timing formulas. Restart your usual inference service when finished.
