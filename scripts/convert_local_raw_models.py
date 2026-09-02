#!/usr/bin/env python3
r"""
convert_local_raw_models.py — OpenVINO INT8 Exporter from Local Raw Model Folders

Converts:
- E:/anchor-models/raw/deberta-v3-nli -> F:/Navi_build/Build/models/deberta-v3-nli-int8-ov
- E:/anchor-models/raw/bge-reranker-large -> F:/Navi_build/Build/models/bge-reranker-large-int8-ov
- E:/anchor-models/raw/bge-m3 -> F:/Navi_build/Build/models/bge-m3-int8-ov
"""

import sys
import time
from pathlib import Path

from optimum.intel.openvino import OVModelForFeatureExtraction, OVModelForSequenceClassification
from transformers import AutoTokenizer

RAW_MODELS_DIR = Path("E:/anchor-models/raw")
MODELS_DIR = Path("F:/Navi_build/Build/models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)


def convert_deberta():
    src = RAW_MODELS_DIR / "deberta-v3-nli"
    dst = MODELS_DIR / "deberta-v3-nli-int8-ov"
    if (dst / "openvino_model.xml").exists():
        print(f"[SKIP] DeBERTa-v3-NLI already converted at {dst}")
        return True
    if not (src / "pytorch_model.bin").exists() and not (src / "model.safetensors").exists():
        print(f"[WAIT] {src} weights not yet downloaded.")
        return False

    print(f"\nConverting DeBERTa-v3-NLI from {src} to OpenVINO INT8 at {dst}...")
    t0 = time.perf_counter()
    model = OVModelForSequenceClassification.from_pretrained(
        str(src),
        export=True,
        weight_format="int8",
        compile=False,
    )
    tokenizer = AutoTokenizer.from_pretrained(str(src))
    dst.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(dst))
    tokenizer.save_pretrained(str(dst))
    print(f"[SUCCESS] DeBERTa-v3-NLI converted in {time.perf_counter()-t0:.2f}s!")
    return True


def convert_bge_reranker():
    src = RAW_MODELS_DIR / "bge-reranker-large"
    dst = MODELS_DIR / "bge-reranker-large-int8-ov"
    if (dst / "openvino_model.xml").exists():
        print(f"[SKIP] BGE-Reranker-Large already converted at {dst}")
        return True
    if not (src / "pytorch_model.bin").exists() and not (src / "model.safetensors").exists():
        print(f"[WAIT] {src} weights not yet downloaded.")
        return False

    print(f"\nConverting BGE-Reranker-Large from {src} to OpenVINO INT8 at {dst}...")
    t0 = time.perf_counter()
    model = OVModelForSequenceClassification.from_pretrained(
        str(src),
        export=True,
        weight_format="int8",
        compile=False,
    )
    tokenizer = AutoTokenizer.from_pretrained(str(src))
    dst.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(dst))
    tokenizer.save_pretrained(str(dst))
    print(f"[SUCCESS] BGE-Reranker-Large converted in {time.perf_counter()-t0:.2f}s!")
    return True


def convert_bgem3():
    src = RAW_MODELS_DIR / "bge-m3"
    dst = MODELS_DIR / "bge-m3-int8-ov"
    if (dst / "openvino_model.xml").exists():
        print(f"[SKIP] BGE-M3 already converted at {dst}")
        return True
    if not (src / "pytorch_model.bin").exists() and not (src / "model.safetensors").exists():
        print(f"[WAIT] {src} weights not yet downloaded.")
        return False

    print(f"\nConverting BGE-M3 from {src} to OpenVINO INT8 at {dst}...")
    t0 = time.perf_counter()
    model = OVModelForFeatureExtraction.from_pretrained(
        str(src),
        export=True,
        weight_format="int8",
        compile=False,
    )
    tokenizer = AutoTokenizer.from_pretrained(str(src))
    dst.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(dst))
    tokenizer.save_pretrained(str(dst))
    print(f"[SUCCESS] BGE-M3 converted in {time.perf_counter()-t0:.2f}s!")
    return True


def main():
    convert_deberta()
    convert_bge_reranker()
    convert_bgem3()


if __name__ == "__main__":
    main()
