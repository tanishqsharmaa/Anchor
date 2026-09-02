#!/usr/bin/env python3
r"""
download_and_convert.py — Robust Model Downloader and OpenVINO INT8 Exporter

1. Downloads weights to E:/anchor-models/cache with hf-transfer / multi-threading and visible progress.
2. Exports models to OpenVINO INT8 in F:/Navi_build/Build/models (E:/anchor-models):
   - bge-m3-int8-ov
   - bge-reranker-large-int8-ov
   - deberta-v3-nli-int8-ov
"""

import os
import sys
import time
from pathlib import Path

# Enable fast HF transfer and specify cache directory
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
CACHE_DIR = Path("E:/anchor-models/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ["HF_HOME"] = str(CACHE_DIR)
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from huggingface_hub import snapshot_download
from optimum.intel.openvino import OVModelForFeatureExtraction, OVModelForSequenceClassification
from transformers import AutoTokenizer

MODELS_DIR = Path("F:/Navi_build/Build/models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)


def process_deberta_nli():
    print(f"\n{'='*60}\n[1/3] Processing DeBERTa-v3-NLI (cross-encoder/nli-deberta-v3-base)...\n{'='*60}")
    repo_id = "cross-encoder/nli-deberta-v3-base"
    out_dir = MODELS_DIR / "deberta-v3-nli-int8-ov"

    if (out_dir / "openvino_model.xml").exists():
        print(f"[SKIP] {out_dir} already exists!")
        return

    print("Step 1: Downloading model snapshot with hf-transfer...")
    local_model_path = snapshot_download(
        repo_id=repo_id,
        cache_dir=str(CACHE_DIR),
        local_files_only=False,
    )
    print(f"Downloaded snapshot to: {local_model_path}")

    print("Step 2: Exporting to OpenVINO INT8 format...")
    t0 = time.perf_counter()
    model = OVModelForSequenceClassification.from_pretrained(
        local_model_path,
        export=True,
        weight_format="int8",
        compile=False,
    )
    tokenizer = AutoTokenizer.from_pretrained(local_model_path)

    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))
    print(f"✓ DeBERTa-v3-NLI exported in {time.perf_counter()-t0:.2f}s to {out_dir}")
    del model, tokenizer


def process_bge_reranker():
    print(f"\n{'='*60}\n[2/3] Processing BGE-Reranker-Large (BAAI/bge-reranker-large)...\n{'='*60}")
    repo_id = "BAAI/bge-reranker-large"
    out_dir = MODELS_DIR / "bge-reranker-large-int8-ov"

    if (out_dir / "openvino_model.xml").exists():
        print(f"[SKIP] {out_dir} already exists!")
        return

    print("Step 1: Downloading model snapshot with hf-transfer...")
    local_model_path = snapshot_download(
        repo_id=repo_id,
        cache_dir=str(CACHE_DIR),
        local_files_only=False,
    )
    print(f"Downloaded snapshot to: {local_model_path}")

    print("Step 2: Exporting to OpenVINO INT8 format...")
    t0 = time.perf_counter()
    model = OVModelForSequenceClassification.from_pretrained(
        local_model_path,
        export=True,
        weight_format="int8",
        compile=False,
    )
    tokenizer = AutoTokenizer.from_pretrained(local_model_path)

    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))
    print(f"✓ BGE-Reranker-Large exported in {time.perf_counter()-t0:.2f}s to {out_dir}")
    del model, tokenizer


def process_bgem3():
    print(f"\n{'='*60}\n[3/3] Processing BGE-M3 (BAAI/bge-m3)...\n{'='*60}")
    repo_id = "BAAI/bge-m3"
    out_dir = MODELS_DIR / "bge-m3-int8-ov"

    if (out_dir / "openvino_model.xml").exists():
        print(f"[SKIP] {out_dir} already exists!")
        return

    print("Step 1: Downloading model snapshot with hf-transfer...")
    local_model_path = snapshot_download(
        repo_id=repo_id,
        cache_dir=str(CACHE_DIR),
        local_files_only=False,
    )
    print(f"Downloaded snapshot to: {local_model_path}")

    print("Step 2: Exporting to OpenVINO INT8 format...")
    t0 = time.perf_counter()
    model = OVModelForFeatureExtraction.from_pretrained(
        local_model_path,
        export=True,
        weight_format="int8",
        compile=False,
    )
    tokenizer = AutoTokenizer.from_pretrained(local_model_path)

    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))
    print(f"✓ BGE-M3 exported in {time.perf_counter()-t0:.2f}s to {out_dir}")
    del model, tokenizer


def main():
    print("Starting Optimized Model Download & Export...")
    process_deberta_nli()
    process_bge_reranker()
    process_bgem3()
    print("\nAll 3 models downloaded and converted to OpenVINO INT8 successfully!")


if __name__ == "__main__":
    main()
