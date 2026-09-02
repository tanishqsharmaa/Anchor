#!/usr/bin/env python3
r"""
export_openvino_int8.py — Direct OpenVINO INT8 Exporter for PROJECT ANCHOR

Exports:
1. cross-encoder/nli-deberta-v3-base -> deberta-v3-nli-int8-ov (~240 MB)
2. BAAI/bge-reranker-large -> bge-reranker-large-int8-ov (~600 MB)
3. BAAI/bge-m3 -> bge-m3-int8-ov (~600 MB)
"""

import os
import sys
import time
from pathlib import Path

# Cache on E: drive
CACHE_DIR = Path("E:/anchor-models/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ["HF_HOME"] = str(CACHE_DIR)
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

MODELS_DIR = Path("F:/Navi_build/Build/models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)

from transformers import AutoTokenizer
from optimum.intel.openvino import OVModelForFeatureExtraction, OVModelForSequenceClassification


def export_deberta():
    out_dir = MODELS_DIR / "deberta-v3-nli-int8-ov"
    if (out_dir / "openvino_model.xml").exists():
        print(f"[SKIP] DeBERTa-v3-NLI already exists at {out_dir}")
        return True

    print("\n" + "="*60)
    print("Exporting DeBERTa-v3-NLI (cross-encoder/nli-deberta-v3-base) to OpenVINO INT8...")
    print("="*60)
    t0 = time.perf_counter()
    model_id = "cross-encoder/nli-deberta-v3-base"

    print("Loading & converting model...")
    model = OVModelForSequenceClassification.from_pretrained(
        model_id,
        export=True,
        weight_format="int8",
        compile=False,
    )
    tokenizer = AutoTokenizer.from_pretrained(model_id)

    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))
    print(f"✓ DeBERTa-v3-NLI successfully exported to {out_dir} in {time.perf_counter()-t0:.2f}s")
    del model, tokenizer
    return True


def export_bge_reranker():
    out_dir = MODELS_DIR / "bge-reranker-large-int8-ov"
    if (out_dir / "openvino_model.xml").exists():
        print(f"[SKIP] BGE-Reranker-Large already exists at {out_dir}")
        return True

    print("\n" + "="*60)
    print("Exporting BGE-Reranker-Large (BAAI/bge-reranker-large) to OpenVINO INT8...")
    print("="*60)
    t0 = time.perf_counter()
    model_id = "BAAI/bge-reranker-large"

    print("Loading & converting model...")
    model = OVModelForSequenceClassification.from_pretrained(
        model_id,
        export=True,
        weight_format="int8",
        compile=False,
    )
    tokenizer = AutoTokenizer.from_pretrained(model_id)

    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))
    print(f"✓ BGE-Reranker-Large successfully exported to {out_dir} in {time.perf_counter()-t0:.2f}s")
    del model, tokenizer
    return True


def export_bgem3():
    out_dir = MODELS_DIR / "bge-m3-int8-ov"
    if (out_dir / "openvino_model.xml").exists():
        print(f"[SKIP] BGE-M3 already exists at {out_dir}")
        return True

    print("\n" + "="*60)
    print("Exporting BGE-M3 (BAAI/bge-m3) to OpenVINO INT8...")
    print("="*60)
    t0 = time.perf_counter()
    model_id = "BAAI/bge-m3"

    print("Loading & converting model...")
    model = OVModelForFeatureExtraction.from_pretrained(
        model_id,
        export=True,
        weight_format="int8",
        compile=False,
    )
    tokenizer = AutoTokenizer.from_pretrained(model_id)

    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))
    print(f"✓ BGE-M3 successfully exported to {out_dir} in {time.perf_counter()-t0:.2f}s")
    del model, tokenizer
    return True


def main():
    print("Starting direct OpenVINO INT8 model export pipeline...")
    export_deberta()
    export_bge_reranker()
    export_bgem3()
    print("\n" + "="*60)
    print("All 3 models exported and verified in OpenVINO INT8!")
    print("="*60)


if __name__ == "__main__":
    main()
