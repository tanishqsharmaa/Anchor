import json
from pathlib import Path
import sys

# Ensure Build directory is on python path
build_dir = Path(__file__).resolve().parent.parent
if str(build_dir) not in sys.path:
    sys.path.insert(0, str(build_dir))

from anchor.retrieve.resolver import resolve_dfpds_delegation, resolve_dpm_threshold

def generate_all_resolver_outputs(output_path: Path) -> dict:
    """Evaluate all 384 statutory permutations and export to indexed JSON."""
    results = {}
    tiers = ["Tier 1", "Tier 2", "Tier 3", "Tier 4", "Tier 5", "Tier 6"]
    ifa_states = [True, False]

    count = 0
    for sched in range(1, 33):
        for tier in tiers:
            for ifa in ifa_states:
                res = resolve_dfpds_delegation(schedule_no=sched, tier=tier, ifa_concurrence=ifa)
                if res:
                    key = f"SCH-{sched:02d}_{tier.replace(" ", "_")}_{"with_ifa" if ifa else "without_ifa"}"
                    results[key] = {
                        "schedule_no": res.schedule_no,
                        "schedule_name": res.schedule_name,
                        "reference": res.reference,
                        "tier": res.tier,
                        "tier_name": res.tier_name,
                        "sanction_limit": res.sanction_limit,
                        "with_ifa": res.with_ifa,
                        "is_pac": res.is_pac,
                        "pac_limit": res.pac_limit,
                        "formatted_answer": res.formatted_answer,
                        "pred_source": res.reference,
                        "pred_section": f"{res.tier} ({res.tier_name})" if res.tier_name else res.tier,
                    }
                    count += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"[SUCCESS] Precomputed {count} deterministic resolver outputs to {output_path}")
    return results

if __name__ == "__main__":
    out_file = build_dir / "kaggle" / "precomputed" / "resolver_outputs.json"
    generate_all_resolver_outputs(out_file)
