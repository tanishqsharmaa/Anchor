#!/usr/bin/env python3
"""
convert_models.py — OpenVINO INT8 Model Conversion Pipeline for PROJECT ANCHOR

Converts:
1. BAAI/bge-m3 -> OpenVINO INT8 (Dense/Sparse Embedder, ~600 MB)
2. BAAI/bge-reranker-large -> OpenVINO INT8 (Cross-Encoder Reranker, ~600 MB)
3. cross-encoder/nli-deberta-v3-base -> OpenVINO INT8 (NLI Verification Gate, ~240 MB)

All models and HF caches are strictly placed on the E: drive (via F:\\Navi_build\\Build\\models)
to respect the 16 GB RAM and partition limits.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Set environment variables for E: drive caching before any HF imports
CACHE_DIR = Path("E:/anchor-models/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ["HF_HOME"] = str(CACHE_DIR)
os.environ["TRANSFORMERS_CACHE"] = str(CACHE_DIR)
os.environ["HF_HUB_CACHE"] = str(CACHE_DIR)

MODELS_DIR = Path("F:/Navi_build/Build/models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)

MODELS_TO_CONVERT = [
    {
        "name": "bge-m3",
        "model_id": "BAAI/bge-m3",
        "task": "feature-extraction",
        "output_dir": MODELS_DIR / "bge-m3-int8-ov",
        "weight_format": "int8",
    },
    {
        "name": "bge-reranker-large",
        "model_id": "BAAI/bge-reranker-large",
        "task": "text-classification",
        "output_dir": MODELS_DIR / "bge-reranker-large-int8-ov",
        "weight_format": "int8",
    },
    {
        "name": "deberta-v3-nli",
        "model_id": "cross-encoder/nli-deberta-v3-base",
        "task": "text-classification",
        "output_dir": MODELS_DIR / "deberta-v3-nli-int8-ov",
        "weight_format": "int8",
    },
]


def convert_model(model_info: dict, force: bool = False) -> bool:
    output_dir = model_info["output_dir"]
    model_xml = output_dir / "openvino_model.xml"

    if model_xml.exists() and not force:
        print(f"[SKIP] {model_info['name']} already exists at {output_dir}")
        return True

    print(f"\n{'='*60}")
    print(f"Converting {model_info['name']} ({model_info['model_id']}) to OpenVINO {model_info['weight_format']}...")
    print(f"Output Directory: {output_dir}")
    print(f"{'='*60}\n")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Use optimum-cli export openvino
    cmd = [
        sys.executable,
        "-m",
        "optimum.commands.optimum_cli",
        "export",
        "openvino",
        "--model",
        model_info["model_id"],
        "--task",
        model_info["task"],
        "--weight-format",
        model_info["weight_format"],
        str(output_dir),
    ]

    try:
        env = os.environ.copy()
        env["HF_HOME"] = str(CACHE_DIR)
        result = subprocess.run(cmd, check=True, env=env)
        print(f"[SUCCESS] Converted {model_info['name']} to {output_dir}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to convert {model_info['name']}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Convert HuggingFace models to OpenVINO INT8 IR format")
    parser.add_argument("--model", type=str, choices=["all", "bge-m3", "bge-reranker-large", "deberta-v3-nli"], default="all", help="Specific model to convert")
    parser.add_argument("--force", action="store_true", help="Force overwrite existing exported models")
    args = parser.parse_args()

    targets = MODELS_TO_CONVERT if args.model == "all" else [m for m in MODELS_TO_CONVERT if m["name"] == args.model]

    success_count = 0
    for model_info in targets:
        if convert_model(model_info, force=args.force):
            success_count += 1

    print(f"\n{'='*60}")
    print(f"Conversion Summary: {success_count}/{len(targets)} models ready.")
    print(f"{'='*60}\n")

    if success_count < len(targets):
        sys.exit(1)


if __name__ == "__main__":
    main()
