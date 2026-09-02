import os
from pathlib import Path
import pytest

BUILD_DIR = Path(__file__).resolve().parent.parent.parent


def test_scripts_exist_and_non_empty():
    setup_script = BUILD_DIR / "scripts" / "setup.ps1"
    start_script = BUILD_DIR / "scripts" / "start.ps1"
    demo_script = BUILD_DIR / "scripts" / "demo.ps1"

    assert setup_script.exists(), "setup.ps1 must exist"
    assert start_script.exists(), "start.ps1 must exist"
    assert demo_script.exists(), "demo.ps1 must exist"

    assert len(setup_script.read_text(encoding="utf-8")) > 200
    assert len(start_script.read_text(encoding="utf-8")) > 200
    assert len(demo_script.read_text(encoding="utf-8")) > 200


def test_setup_script_structure():
    setup_content = (BUILD_DIR / "scripts" / "setup.ps1").read_text(encoding="utf-8")
    
    # Must check Python & Node prerequisites
    assert "Python" in setup_content
    assert "Node.js" in setup_content
    assert "pnpm" in setup_content

    # Must manage virtualenv and backend dependencies
    assert ".venv" in setup_content
    assert "requirements.txt" in setup_content

    # Must verify SQLite and audit triggers
    assert "audit" in setup_content.lower()

    # Must compile Next.js production build
    assert "pnpm build" in setup_content or "pnpm" in setup_content


def test_start_script_structure():
    start_content = (BUILD_DIR / "scripts" / "start.ps1").read_text(encoding="utf-8")
    
    assert "8000" in start_content
    assert "3000" in start_content
    assert "health" in start_content
    assert "uvicorn" in start_content


def test_demo_script_structure():
    demo_content = (BUILD_DIR / "scripts" / "demo.ps1").read_text(encoding="utf-8")
    
    assert "8000" in demo_content
    assert "3000" in demo_content
    assert "powercfg" in demo_content or "power" in demo_content.lower()
    assert "localhost:3000" in demo_content


def test_readme_completeness_and_sections():
    readme_path = BUILD_DIR / "README.md"
    assert readme_path.exists(), "README.md must exist in Build/"
    
    content = readme_path.read_text(encoding="utf-8")
    
    # Title & Subtitle
    assert "ANCHOR" in content
    assert "INICAI" in content
    
    # Key Sections
    assert "## Executive Summary" in content
    assert "## 🚀 Quick Start" in content
    assert "## 🏛️ System Architecture" in content
    assert "```mermaid" in content
    assert "## 📊 Statutory Evaluation Scorecard" in content
    assert "## 🎯 5-Minute Kill-Shot Demonstration Flow" in content
    assert "## ⌨️ C4ISR Tactical Console Keyboard Shortcuts" in content
    assert "## 🛠️ Complete Tech Stack" in content
    assert "## 🔒 Security & Air-Gap Invariants" in content
    assert "## 📄 License" in content

    # Scorecard Quality Gates
    assert "Faithfulness" in content
    assert "Citation Precision" in content
    assert "Context Recall" in content
    assert "Abstention Accuracy" in content
    assert "Hallucination Rate" in content
    assert "Structured Accuracy" in content


def test_requirements_txt_exact_pinning():
    req_path = BUILD_DIR / "requirements.txt"
    assert req_path.exists(), "requirements.txt must exist in Build/"
    
    lines = [line.strip() for line in req_path.read_text(encoding="utf-8").splitlines()]
    pkg_lines = [l for l in lines if l and not l.startswith("#")]
    
    assert len(pkg_lines) >= 15, "Should list all primary backend dependencies"
    
    for pkg in pkg_lines:
        assert "==" in pkg, f"Package {pkg} must be pinned with exact '==' version"
        assert not pkg.startswith(">="), f"Package {pkg} should not use '>='"
        assert not pkg.startswith("<="), f"Package {pkg} should not use '<='"


def test_gitignore_clean_exclusions():
    gitignore_path = BUILD_DIR / ".gitignore"
    assert gitignore_path.exists(), ".gitignore must exist in Build/"
    
    content = gitignore_path.read_text(encoding="utf-8")
    
    assert ".venv/" in content
    assert "node_modules/" in content
    assert "__pycache__/" in content
    assert ".next/" in content
    assert "models/" in content
    assert "data/pdfs/" in content


def test_dockerfile_stub_and_license():
    docker_path = BUILD_DIR / "Dockerfile-stub"
    license_path = BUILD_DIR / "LICENSE"
    
    assert docker_path.exists(), "Dockerfile-stub must exist"
    assert license_path.exists(), "LICENSE must exist"
    
    docker_content = docker_path.read_text(encoding="utf-8")
    assert "FROM" in docker_content
    assert "EXPOSE 8000" in docker_content
    
    license_content = license_path.read_text(encoding="utf-8")
    assert "MIT License" in license_content
    assert "2026" in license_content


def test_precomputed_competition_packages_completeness():
    import json
    
    precomp_dir = BUILD_DIR / "kaggle" / "precomputed"
    assert precomp_dir.exists(), "kaggle/precomputed directory must exist"

    resolver_f = precomp_dir / "resolver_outputs.json"
    rag_f = precomp_dir / "rag_outputs.json"
    autodeck_f = precomp_dir / "autodeck_outputs.json"
    eval_f = precomp_dir / "eval_metrics.json"

    assert resolver_f.exists(), "resolver_outputs.json must exist"
    assert rag_f.exists(), "rag_outputs.json must exist"
    assert autodeck_f.exists(), "autodeck_outputs.json must exist"
    assert eval_f.exists(), "eval_metrics.json must exist"

    resolver_data = json.loads(resolver_f.read_text(encoding="utf-8"))
    assert len(resolver_data) == 384

    rag_data = json.loads(rag_f.read_text(encoding="utf-8"))
    assert len(rag_data) >= 5

    autodeck_data = json.loads(autodeck_f.read_text(encoding="utf-8"))
    assert len(autodeck_data) >= 3

    eval_data = json.loads(eval_f.read_text(encoding="utf-8"))
    assert "faithfulness" in eval_data
    assert "citation_precision" in eval_data
    assert eval_data.get("audit_ledger_status") == "SEALED"
    assert eval_data.get("statutory_gates_passed") == 6