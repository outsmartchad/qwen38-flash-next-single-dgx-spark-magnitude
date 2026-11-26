#!/usr/bin/env python3
"""Prepare and run the pinned Magnitude text recipe on one DGX Spark."""

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request


MODEL = "qwen3.8-flash-next:gguf:q2"
SNAPSHOT = "ed59f92082b1e93c0e96d60a8b11aab089b52f09"
SHARD_COUNT = 2
TARGET_ID = "69820c02ec7d0b45ef2ebb19d6620299db749fe2aded7f39f93c6b88b199b720"
DRAFT_ID = "5ff54097406a905cf3a724c709124ceb0e3e10235ee862298969e91c96fa96e6"
SOURCE = "https://github.com/magnitudedev/magnitude.git"
REVISION = "78c92e4f21e38f9528f21e09c5e43936a04b6b0d"
CONTEXT_TOKENS = 64_768
OUTPUT_TOKENS = 256

NVRTC_ARCHIVE = "cuda_nvrtc-linux-sbsa-12.9.86-archive"
NVRTC_URL = (
    "https://developer.download.nvidia.com/compute/cuda/redist/cuda_nvrtc/"
    f"linux-sbsa/{NVRTC_ARCHIVE}.tar.xz"
)
NVRTC_SHA256 = "fb2d50c791465f333fc2236d2419170cf7a7886f48dd9b967a10f8233c686029"
NVRTC_FILES = {
    "lib/libnvrtc.so.12.9.86": "libnvrtc.so.12",
    "lib/libnvrtc-builtins.so.12.9.86": "libnvrtc-builtins.so.12.9",
    "LICENSE": "NVRTC-LICENSE.txt",
}

CACHE = Path(
    os.environ.get("MAGNITUDE_RECIPE_CACHE") or Path.home() / ".cache/magnitude-spark-recipes"
).expanduser().resolve()
MODEL_STORE = Path.home() / ".magnitude/models"
CHECKOUT = CACHE / f"magnitude-{REVISION[:12]}"
INFERENCE = CHECKOUT / "inference"
BUILD = CACHE / f"target-{REVISION[:12]}"
BIN = BUILD / "release"
PROFILE = CACHE / "qwen38-q2"
ARTIFACTS = PROFILE / "artifacts.json"
HOST = "127.0.0.1"
RECIPE = Path(__file__).resolve().parent.parent


def require(*commands):
    missing = [command for command in commands if not shutil.which(command)]
    if missing:
        raise ValueError(f"Install the required tools listed in docs/setup.md: {', '.join(missing)}")


def require_spark():
    if platform.system() != "Linux" or platform.machine() != "aarch64":
        raise ValueError("Run this command on the DGX Spark (Linux aarch64).")


def doctor():
    require_spark()
    require("git", "cargo", "cc", "pkg-config", "curl", "ss", "nvidia-smi", "uv")
    subprocess.run(
        ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"], check=True
    )
    with Path("/proc/meminfo").open() as info:
        for line in info:
            if line.startswith(("MemTotal:", "MemAvailable:")):
                print(line.strip())
    print(f"Cache directory: {CACHE}")
    print(f"Model store: {MODEL_STORE}")
    subprocess.run(["df", "-h", str(CACHE.parent if CACHE.parent.is_dir() else Path.home())], check=True)


def checkout_source():
    if not CHECKOUT.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="source-", dir=CACHE) as staging:
            repo = Path(staging) / "checkout"
            subprocess.run(["git", "init", "--quiet", repo], check=True)
            subprocess.run(
                ["git", "-C", repo, "remote", "add", "origin", SOURCE], check=True
            )
            subprocess.run(
                ["git", "-C", repo, "fetch", "--no-tags", "--depth", "1", "origin", REVISION],
                check=True,
            )
            subprocess.run(
                ["git", "-C", repo, "checkout", "--quiet", "--detach", REVISION], check=True
            )
            try:
                repo.rename(CHECKOUT)
            except FileExistsError:
                pass
    found = subprocess.check_output(["git", "-C", CHECKOUT, "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(
        ["git", "-C", CHECKOUT, "status", "--porcelain", "--", "inference", "rust-toolchain.toml"],
        text=True,
    ).strip()
    if found != REVISION or dirty:
        raise ValueError(f"Expected the pinned clean source at {CHECKOUT}. Use a fresh recipe cache.")


def nvrtc_directory(install=False):
    configured = os.environ.get("SEISMIC_NVRTC_DIRECTORY")
    root = Path(configured).expanduser().resolve() if configured else CACHE / "nvrtc-12.9.86"
    libraries = ("libnvrtc.so.12", "libnvrtc-builtins.so.12.9")
    if all((root / name).is_file() for name in libraries):
        return root
    if configured:
        raise ValueError(f"NVRTC 12.9 and its matching builtins library are required in {root}.")
    if not install:
        raise ValueError("Run prepare to stage NVRTC, or set SEISMIC_NVRTC_DIRECTORY.")
    CACHE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nvrtc-", dir=CACHE) as staging:
        temp = Path(staging)
        archive = temp / "nvrtc.tar.xz"
        subprocess.run(
            ["curl", "-fLSs", "--retry", "2", "--output", archive, NVRTC_URL], check=True
        )
        with archive.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != NVRTC_SHA256:
            raise ValueError("NVIDIA NVRTC archive SHA-256 did not match the pinned release.")
        ready = temp / "runtime"
        ready.mkdir()
        with tarfile.open(archive, "r:xz") as bundle:
            for member, name in NVRTC_FILES.items():
                member_stream = bundle.extractfile(f"{NVRTC_ARCHIVE}/{member}")
                if member_stream is None:
                    raise ValueError(f"Missing NVRTC archive member {member}")
                with member_stream, (ready / name).open("wb") as output:
                    shutil.copyfileobj(member_stream, output)
        try:
            ready.rename(root)
        except FileExistsError:
            if not all((root / name).is_file() for name in libraries):
                raise ValueError(f"Please use a fresh cache. NVRTC installation is incomplete at {root}.")
    return root


def artifacts(data):
    if data["model"] != MODEL or data["target_sha256"] != TARGET_ID:
        raise ValueError("Target identity differs from the saved benchmark.")
    shards = [Path(path) for path in data["target_files"]]
    if len(shards) != SHARD_COUNT or shards[0] != Path(data["target"]):
        raise ValueError(f"Expected {SHARD_COUNT} ordered GGUF target shards.")
    if any(SNAPSHOT not in p.parts or not p.is_file() for p in shards):
        raise ValueError("A target shard is missing or points outside the pinned snapshot. Run prepare.")
    drafter = data["drafter"]
    draft = Path(drafter["path"])
    if drafter["method"] != "mtp" or drafter["sha256"] != DRAFT_ID or not draft.is_file():
        raise ValueError("MTP artifact differs from the measured profile or is missing.")
    return shards, draft


def prepare():
    doctor()
    checkout_source()
    nvrtc_directory(install=True)
    cargo = ["cargo", "build", "--release", "--locked", "--target-dir", BUILD]
    subprocess.run(
        [
            *cargo, "--no-default-features",
            "-p", "magnitude-engine-cli", "-p", "magnitude-engine", "-p", "magnitude-harness",
            "--bin", "magnitude-engine", "--bin", "magnitude-assess", "--bin", "magnitude-render",
        ],
        cwd=INFERENCE,
        check=True,
    )
    subprocess.run(
        [*cargo, "-p", "magnitude-service-catalog-tool"], cwd=INFERENCE, check=True
    )
    acquired = subprocess.check_output(
        [BIN / "magnitude-service-catalog-tool", "acquire", "--model", MODEL, "--model-store", MODEL_STORE],
        text=True,
    )
    artifacts(json.loads(acquired))
    PROFILE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="model-", dir=PROFILE) as staging:
        record = Path(staging) / "artifacts.json"
        record.write_text(acquired)
        record.replace(ARTIFACTS)
    print(f"Prepared {MODEL}. Launch with ./scripts/recipe.py serve.")


def listeners(port):
    require("ss")
    return subprocess.check_output(["ss", "-H", "-ltn", f"sport = :{port}"], text=True).splitlines()


def request(port, path, payload=None):
    # Call only the local interface, even when a shell proxy is configured.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        f"http://{HOST}:{port}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with opener.open(req, timeout=90 if payload is not None else 5) as response:
        return json.load(response)


def serve(port):
    require_spark()
    if listeners(port):
        raise ValueError(f"TCP port {port} is already in use. Choose another --port or stop its owner.")
    if not (BIN / "magnitude-engine").is_file() or not ARTIFACTS.is_file():
        raise ValueError("Run ./scripts/recipe.py prepare first.")
    shards, draft = artifacts(json.loads(ARTIFACTS.read_text()))
    env = {**os.environ, "SEISMIC_NVRTC_DIRECTORY": str(nvrtc_directory())}
    command = [str(BIN / "magnitude-engine")]
    for path in shards:
        command.extend(["--model", str(path)])
    command.extend(
        [
            "--host", HOST, "--port", str(port), "--served-model", MODEL, "--device", "cuda",
            "--context-tokens", str(CONTEXT_TOKENS), "--output-capacity", str(OUTPUT_TOKENS),
            "--method", "mtp", "--no-projector", "--cache-dir", str(PROFILE / "kernels"),
        ]
    )
    if draft != shards[0]:
        command.extend(["--draft", str(draft)])
    os.execve(command[0], command, env)


def status(port):
    rows = listeners(port)
    if not rows or {row.split()[3] for row in rows} != {f"{HOST}:{port}"}:
        raise ValueError(f"Expected a loopback-only listener on {HOST}:{port}.")
    health = request(port, "/health")
    if (
        health.get("ready") is not True
        or health.get("model") != MODEL
        or health.get("context_tokens") != CONTEXT_TOKENS
        or health.get("drafting", {}).get("method") != "mtp"
    ):
        raise ValueError(f"Server readiness or profile differs from the recipe: {health}")
    print(json.dumps(health, indent=2))


def smoke(port):
    status(port)
    result = request(
        port,
        "/v1/chat/completions",
        {
            "model": MODEL,
            "messages": [{"role": "user", "content": "Reply with exactly SPARK_OK."}],
            "temperature": 0,
            "reasoning_effort": "none",
            "max_tokens": 64,
        },
    )
    choices = result.get("choices", [])
    answer = choices[0]["message"].get("content", "") if choices else ""
    if (answer or "").strip() != "SPARK_OK":
        raise ValueError(f"Expected SPARK_OK from local chat. Received {answer!r}.")
    print(answer.strip())


def benchmark():
    doctor()
    checkout_source()
    if not ARTIFACTS.is_file() or not all(
        (BIN / name).is_file() for name in ("magnitude-engine", "magnitude-assess", "magnitude-render")
    ):
        raise ValueError("Run ./scripts/recipe.py prepare before benchmarking.")
    artifacts(json.loads(ARTIFACTS.read_text()))
    env = {**os.environ, "SEISMIC_NVRTC_DIRECTORY": str(nvrtc_directory())}

    runs = RECIPE / "runs"
    runs.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = Path(tempfile.mkdtemp(prefix=f"{stamp}-", dir=runs))
    kernels = run / "kernels"
    kernels.mkdir()
    template = run / "repeat-64k.json"
    with gzip.open(RECIPE / "raw/bench/templates/f67f31e10d8a2109.json.gz", "rb") as src:
        with template.open("wb") as dst:
            shutil.copyfileobj(src, dst)
    build_identity = run / "build.json"
    build_identity.write_text(json.dumps({"commit": REVISION, "dirty_digest": None}) + "\n")

    print(f"Benchmark artifacts: {run / 'bench'}", flush=True)
    with (run / "topology.log").open("w") as log:
        subprocess.run(
            [BIN / "magnitude-assess", "--device", "cuda", "--kernels", kernels, "--topology"],
            cwd=INFERENCE,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )
    subprocess.run(
        [
            "uv", "run", "--locked", "--project", "evaluation", "--package", "magnitude-bench",
            "magnitude-bench", "job", "--inference", INFERENCE, "--model", MODEL,
            "--engine", "magnitude", "--magnitude-device", "cuda",
            "--magnitude-binary", BIN / "magnitude-engine", "--harness", BIN / "magnitude-render",
            "--template", template, "--section", "context", "--passes", "2",
            "--drafting", "on", "--fresh-tuning", "--magnitude-cache-dir", kernels,
            "--artifacts", ARTIFACTS, "--build-identity", build_identity, "--output", run / "bench",
        ],
        cwd=INFERENCE,
        env=env,
        check=True,
    )

    summary = json.loads((run / "bench/summary.json").read_text())
    if summary.get("outcomes", {}).get("valid") != 2:
        raise ValueError(f"Expected two eligible measurements. See {run / 'bench/report.md'}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("doctor", "prepare", "serve", "status", "smoke", "benchmark"))
    parser.add_argument("--port", type=int, default=10100, help="loopback port for serve, status, and smoke")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    actions = {
        "doctor": doctor,
        "prepare": prepare,
        "serve": lambda: serve(args.port),
        "status": lambda: status(args.port),
        "smoke": lambda: smoke(args.port),
        "benchmark": benchmark,
    }
    try:
        actions[args.action]()
    except KeyboardInterrupt:
        sys.exit(130)
    except (ValueError, OSError, subprocess.CalledProcessError, KeyError, tarfile.TarError) as error:
        sys.exit(f"recipe: {error}")


if __name__ == "__main__":
    main()
