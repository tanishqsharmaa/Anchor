# Kaggle Competition Specification & Submission Format

> **Competition:** INICAI Indian Navy AI Hackathon 2026 — DefenceRAG Track
> **Target:** Automated Leaderboard (50% of total evaluation score)
> **Output Destination:** `kaggle/precomputed/` & `kaggle/notebook.ipynb`

---

## 1. Submission Schema

The final submission CSV file must strictly adhere to the following schema:

| Column Name | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `id` | `string` / `integer` | Unique query/question identifier | `"Q042"` |
| `prediction` | `string` | The resolved or generated response text | `"Under DFPDS-2026 Schedule 7 (Tactical Drones), a Fleet Commander (L2) may sanction up to ₹15.0 Crore with IFA concurrence."` |
| `pred_source` | `string` | The regulatory source document cited | `"DFPDS-2026/Schedule_07"` |
| `pred_section` | `string` | The specific clause/table row/tier reference | `"Clause 7.2 (Tier L2)"` |

---

## 2. Evaluation Metrics & Minimum Quality Bar

| Metric | Target | Formula / Enforcement |
| :--- | :---: | :--- |
| **Faithfulness** | $\ge 0.92$ | $\frac{\text{NLI-verified claims } (\ge 0.85)}{\text{Total claims}}$ |
| **Citation Precision** | $\ge 0.95$ | $\frac{\text{Claims with valid byte-offset anchor}}{\text{Total cited claims}}$ |
| **Hallucination Rate** | $\le 0.05$ | $\frac{\text{Incorrect ₹ numbers or phantom refs}}{\text{Total claims}}$ |
| **Abstention Accuracy** | $= 1.00$ | $\frac{\text{Correct refusals on OOD questions}}{\text{Total OOD questions}}$ |
| **Structured Query Accuracy** | $= 1.00$ | Exact match via Deterministic SQL Resolver |

---

## 3. Precomputed Artifact Structure

To ensure 100% reproducibility and instant Kaggle kernel execution without requiring heavy GPU downloads on Kaggle infrastructure:

```
kaggle/
├── notebook.ipynb                    # Self-contained Kaggle evaluation notebook
├── precomputed/
│   ├── resolver_outputs.json         # 100% accurate SQL resolver precomputed lookups
│   ├── rag_outputs.json              # Full pipeline interpretive outputs with SHA-256 anchors
│   ├── autodeck_outputs.json         # Slide AST structures & BLUF deck validations
│   └── eval_metrics.json             # Published test suite metrics & verification hashes
└── README.md                         # Kernel execution instructions
```

---

## 4. Submission Timing Milestones

1. **Sprint 4 (Day 6)**: First submission using deterministic resolver on structured questions (baseline leaderboard entry).
2. **Sprint 9 (Day 20)**: Second submission integrating full NLI-verified RAG pipeline outputs.
3. **Sprint 14 (Day 28)**: Final submissions optimizing leaderboard position using all 5 daily submission slots.
