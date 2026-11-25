#!/usr/bin/env bash
set -euo pipefail

# Reproduce this recipe's single-request, cold 64K Magnitude benchmark.
MODEL='qwen3.8-flash-next:gguf:q2'
REV='78c92e4f21e38f9528f21e09c5e43936a04b6b0d'
REPO='https://github.com/magnitudedev/magnitude.git'
WORKDIR="${MAGNITUDE_WORKDIR:-$HOME/.cache/magnitude-qwen38-bench-$(date -u +%Y%m%dT%H%M%SZ)}"

command -v git >/dev/null || { echo 'git is required' >&2; exit 1; }
command -v uv >/dev/null || { echo 'Install uv first: https://docs.astral.sh/uv/' >&2; exit 1; }
command -v cargo >/dev/null || { echo 'Install Rust/Cargo first: https://rustup.rs/' >&2; exit 1; }

mkdir -p "$(dirname "$WORKDIR")"
git clone --filter=blob:none "$REPO" "$WORKDIR"
git -C "$WORKDIR" checkout --detach "$REV"

export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$HOME/.cache/uv}"
if [[ -d "$HOME/.magnitude/releases/artifacts" ]]; then
  nvrtc="$(find "$HOME/.magnitude/releases/artifacts" -type f -name 'libnvrtc.so.12' -print -quit 2>/dev/null || true)"
  if [[ -n "$nvrtc" ]]; then
    export SEISMIC_NVRTC_DIRECTORY="$(dirname "$nvrtc")"
  fi
fi

cd "$WORKDIR/inference"
uv run --project evaluation --package magnitude-rig mrig bench \
  --backend cuda \
  --host local \
  --model "$MODEL" \
  --template repeat:64k \
  --purpose 'Reproduce the Qwen 3.8 Flash Next 64K DGX Spark Magnitude benchmark' \
  --estimate 25m \
  --section context \
  --passes 2 \
  --drafting on \
  --fresh-tuning
