from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
F1_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth" / "phase_1_lexical"
OUTPUTS_DIR = F1_ROOT / "outputs"
VOCAB_DIR = OUTPUTS_DIR / "canonical_vocabulary"


def stable_key(value: str, prefix: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def row(
    *,
    owner: str,
    target: str,
    namespace: str,
    target_field: str,
    subsystem: str,
    semantic_level: str,
    term: str,
    source: str,
    source_version: str,
    source_url: str,
    tier: str,
    status: str,
    caveat: str,
) -> dict:
    concept_seed = f"{owner}|{target}|{subsystem}|{semantic_level}|{term}"
    return {
        "concept_id": stable_key(concept_seed, "CV-EXT"),
        "canonical_concept": term,
        "canonical_concept_key": stable_key(term, "CONCEPT"),
        "vocabulary_owner": owner,
        "target": target,
        "namespace": namespace,
        "target_field": target_field,
        "subsystem": subsystem,
        "semantic_level": semantic_level,
        "source": source,
        "source_version": source_version,
        "source_url": source_url,
        "evidence_type": "reference_evidence",
        "tier": tier,
        "status": status,
        "coverage_scope": subsystem,
        "can_support_contractual_denominator": False,
        "can_support_proxy_denominator": False,
        "requires_mapping_from_observed_text": True,
        "label_generation_method": "external_reference_vocabulary_ingest",
        "evaluation_independence": "independent",
        "source_caveat": caveat,
        "raw_values_emitted": False,
    }


def main() -> None:
    VOCAB_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []

    wmep_source = "WMEP database via Ozturk et al., Energies 11(9):2317, 2018"
    wmep_url = "https://doi.org/10.3390/en11092317"
    wmep_caveat = "WMEP categories reproduced through a peer-reviewed open-access secondary source, not the original WMEP database."
    for term in [
        "high wind",
        "grid failure",
        "lightning",
        "icing",
        "malfunction of control systems",
        "component wear or failure",
        "loosening of parts",
        "other causes",
        "unknown causes",
    ]:
        rows.append(
            row(
                owner="WMEP_CAUSES",
                target="Cause",
                namespace="catalog_5",
                target_field="findings[].cause",
                subsystem="wind_turbine_general",
                semantic_level="failure_cause",
                term=term,
                source=wmep_source,
                source_version="2018",
                source_url=wmep_url,
                tier="silver-high",
                status="active",
                caveat=wmep_caveat,
            )
        )

    for term in [
        "Overspeed",
        "Overload",
        "Noise",
        "Vibration",
        "Reduced power",
        "Causing follow-up damage",
        "Plant stoppage",
        "Other consequences",
    ]:
        status = "active" if term not in {"Other consequences"} else "residual_category"
        rows.append(
            row(
                owner="WMEP_EFFECTS",
                target="Symptom",
                namespace="catalog_s",
                target_field="header.symptom.group+header.symptom.code",
                subsystem="wind_turbine_general",
                semantic_level="failure_effect",
                term=term,
                source=wmep_source,
                source_version="2018",
                source_url=wmep_url,
                tier="silver-high",
                status=status,
                caveat="Failure effects can anchor symptom-like signals, but do not prove project-specific Symptom labels.",
            )
        )

    nrel_grd_source = "NREL Gearbox Reliability Database / gearbox failure publications"
    nrel_grd_url = "https://catalog.data.gov/dataset/2014-wind-turbine-gearbox-damage-distribution-based-on-the-nrel-gearbox-reliability-databa"
    nrel_grd_caveat = "Gearbox-specific vocabulary; not extrapolable to other subsystems without additional evidence."
    for subsystem, semantic_level, terms in [
        (
            "gearbox_bearing",
            "damage_mechanism",
            [
                "axial cracks",
                "hardening cracks",
                "scuffing / severe adhesion",
                "macropitting",
                "micropitting",
                "fretting corrosion",
                "false brinelling",
                "debris dents",
                "contact corrosion",
                "abrasion",
                "assembly damage",
                "plastic deformation",
                "overheating",
                "polishing wear",
            ],
        ),
        (
            "gearbox_gears",
            "damage_mechanism",
            [
                "scuffing",
                "macropitting",
                "micropitting",
                "fretting corrosion",
                "subsurface initiated bending fatigue",
                "polishing",
            ],
        ),
        (
            "gearbox",
            "failure_cause",
            [
                "lack of lubrication",
                "assembly damage",
                "misalignment",
                "poor load distribution",
                "manufacturing defects",
                "non-metallic inclusions",
                "microstructural banding",
            ],
        ),
    ]:
        target = "Cause" if semantic_level == "failure_cause" else "Damage"
        namespace = "catalog_5" if target == "Cause" else "catalog_c"
        target_field = "findings[].cause" if target == "Cause" else "findings[].damage"
        for term in terms:
            rows.append(
                row(
                    owner="NREL_GRD",
                    target=target,
                    namespace=namespace,
                    target_field=target_field,
                    subsystem=subsystem,
                    semantic_level=semantic_level,
                    term=term,
                    source=nrel_grd_source,
                    source_version="2012-2014",
                    source_url=nrel_grd_url,
                    tier="silver-high",
                    status="active",
                    caveat=nrel_grd_caveat,
                )
            )

    for term in [
        "spalling",
        "surface damage",
        "surface-initiated rolling contact fatigue",
        "wear induced",
        "subsurface-initiated rolling contact fatigue",
        "micropitting",
        "adhesive wear",
        "false brinelling",
        "standstill corrosion",
    ]:
        rows.append(
            row(
                owner="NREL_MAIN_BEARING",
                target="Damage",
                namespace="catalog_c",
                target_field="findings[].damage",
                subsystem="main_bearing",
                semantic_level="field_reported_damage",
                term=term,
                source="NREL Main Bearing Replacement and Damage field data study",
                source_version="2023",
                source_url="https://doi.org/10.2172/1992019",
                tier="silver-high",
                status="active",
                caveat="Main-bearing-specific field evidence; not a generic all-subsystem damage vocabulary.",
            )
        )

    for term in [
        "Interlaminar failure",
        "Delamination-Faulty injection",
        "Peeling/Wear",
        "Erosion of the sealing of the root",
        "Flaking of the topcoat",
        "Missing external parts",
        "Fine cracks in topcoat",
        "Transverse cracks from trailing edge",
        "Transverse cracks on blade surface",
        "Front edge cracks",
        "Web failure",
        "Fatigue failure in root connection",
        "Fatigue failure in root transition area",
        "Fatigue failure in bond lines",
        "UV effect on the fibers",
        "Lightning damage",
        "Tower hit by blade",
        "Balsa/composite cracking",
        "Transport damage",
        "Complete separation",
    ]:
        rows.append(
            row(
                owner="BLADE_FAILURE_MODE_LITERATURE",
                target="Damage",
                namespace="catalog_c",
                target_field="findings[].damage",
                subsystem="rotor_blade",
                semantic_level="failure_mode_taxonomy",
                term=term,
                source="Wind turbine component failure-mode review literature",
                source_version="2021",
                source_url="https://doi.org/10.3390/en14175241",
                tier="silver-high",
                status="active",
                caveat="Blade-specific failure-mode taxonomy; requires target-specific mapping before denominator use.",
            )
        )

    for term in [
        "phase module",
        "power-converter control board",
        "cooling system",
        "main circuit breaker",
        "grid-coupling contactor",
        "other power-converter components",
        "IGBT modules",
        "driver boards",
        "DC-link capacitors",
        "busbars",
        "short-circuit damage",
        "bond-wire failure",
        "solder joint failure",
        "die attached solder joint failure",
        "terminal damages",
        "capacitor failure",
        "PCB failure",
    ]:
        rows.append(
            row(
                owner="CONVERTER_FIELD_DAMAGE_LITERATURE",
                target="Damage",
                namespace="catalog_c",
                target_field="findings[].damage",
                subsystem="converter_power_electronics",
                semantic_level="component_or_damage_mechanism",
                term=term,
                source="Fraunhofer/IWES converter field-data and damage analysis",
                source_version="2019",
                source_url="https://doi.org/10.3390/en12040593",
                tier="silver-high",
                status="active",
                caveat="Mixes component and mechanism vocabulary; F1d must not merge semantic levels automatically.",
            )
        )

    medium_sets = {
        "GENERATOR_FAILURE_LITERATURE": (
            "generator",
            "fault_or_failure_event",
            "https://doi.org/10.1016/j.rser.2024.115227",
            [
                "Bearing Failure",
                "Stator Winding Failure",
                "Rotor Winding Failure",
                "Shaft failure",
                "Voltage regulator failure",
                "Control system malfunction",
                "Misalignment",
                "Abnormal vibration",
                "Material fatigue",
                "Insulation breakdown",
                "Short circuit",
                "Rotor imbalance",
            ],
        ),
        "YAW_FAILURE_LITERATURE": (
            "yaw_system",
            "fault_or_damage_vocabulary",
            "https://doi.org/10.1016/j.rser.2024.115227",
            [
                "Yaw motor fault",
                "Abnormal vibration",
                "Lightning module failure",
                "Yaw gear failure",
                "Cabinet switch trip",
                "Limit switch fault",
                "Limit slider fault",
                "Vane damage",
                "Anemometer damage",
            ],
        ),
        "TRANSFORMER_FAILURE_LITERATURE": (
            "transformer",
            "fault_tree_event",
            "https://doi.org/10.1016/j.rser.2024.115227",
            [
                "Bushing failure",
                "Winding failure",
                "Tank failure",
                "Core failure",
                "Paper insulation fails",
                "Oil insulation fails",
                "Oil level gauge fails to initiate trip",
                "Tank rupture or leakage due to over pressure",
                "Conductive part fails",
                "Insulation part fails",
                "Coil element fails",
                "Magnetism lost",
                "Cooling System fails",
                "Insulation contaminated",
            ],
        ),
        "HYDRAULIC_PITCH_FAILURE_LITERATURE": (
            "hydraulic_pitch_system",
            "component_failure_mode_or_cause",
            "source_verification_pending",
            [
                "hydraulic gear pump",
                "relief valve",
                "accumulators",
                "hydraulic oil",
                "hydraulic hoses",
                "wear and tear",
                "contamination",
                "cavitation",
                "thermal degradation",
                "blockage",
                "improper pressure settings",
                "mechanical wear",
                "leakage",
                "piston seal damage",
                "pre-charge pressure loss",
                "oil degradation",
                "improper viscosity",
                "hose cracking",
                "abrasion",
            ],
        ),
    }
    for owner, (subsystem, semantic_level, source_url, terms) in medium_sets.items():
        for term in terms:
            rows.append(
                row(
                    owner=owner,
                    target="Damage",
                    namespace="catalog_c",
                    target_field="findings[].damage",
                    subsystem=subsystem,
                    semantic_level=semantic_level,
                    term=term,
                    source="Subsystem-specific wind-turbine failure vocabulary literature",
                    source_version="2024-2025",
                    source_url=source_url,
                    tier="silver-medium",
                    status="requires_semantic_classification",
                    caveat="Evidence set is usable but semantically heterogeneous; classify failure mode vs damage vs cause before anchoring.",
                )
            )

    rows.sort(key=lambda item: (item["vocabulary_owner"], item["target"], item["subsystem"], item["canonical_concept"].lower()))

    fields = [
        "concept_id",
        "canonical_concept",
        "canonical_concept_key",
        "vocabulary_owner",
        "target",
        "namespace",
        "target_field",
        "subsystem",
        "semantic_level",
        "source",
        "source_version",
        "source_url",
        "evidence_type",
        "tier",
        "status",
        "coverage_scope",
        "can_support_contractual_denominator",
        "can_support_proxy_denominator",
        "requires_mapping_from_observed_text",
        "label_generation_method",
        "evaluation_independence",
        "source_caveat",
        "raw_values_emitted",
    ]
    write_csv(VOCAB_DIR / "external_failure_vocabulary_v1.csv", rows, fields)

    owner_counts = Counter(item["vocabulary_owner"] for item in rows)
    target_counts = Counter(item["target"] for item in rows)
    tier_counts = Counter(item["tier"] for item in rows)
    status_counts = Counter(item["status"] for item in rows)
    semantic_counts = Counter(item["semantic_level"] for item in rows)

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "F1c2_external_failure_vocabulary_materialization",
        "rows": len(rows),
        "distinct_concept_ids": len({item["concept_id"] for item in rows}),
        "owner_counts": dict(owner_counts),
        "target_counts": dict(target_counts),
        "tier_counts": dict(tier_counts),
        "status_counts": dict(status_counts),
        "semantic_level_counts": dict(semantic_counts),
        "wmep_effects_closed": True,
        "wmep_causes_available": True,
        "damage_beyond_gearbox_available": True,
        "damage_vocabulary_homogeneous": False,
        "high_confidence_ingest_sets": [
            "WMEP_EFFECTS",
            "WMEP_CAUSES",
            "NREL_GRD",
            "NREL_MAIN_BEARING",
            "BLADE_FAILURE_MODE_LITERATURE",
            "CONVERTER_FIELD_DAMAGE_LITERATURE",
        ],
        "medium_confidence_requires_classification": [
            "GENERATOR_FAILURE_LITERATURE",
            "YAW_FAILURE_LITERATURE",
            "TRANSFORMER_FAILURE_LITERATURE",
            "HYDRAULIC_PITCH_FAILURE_LITERATURE",
        ],
        "researchgate_primary_sources_used": False,
        "utm_source_urls_present": False,
        "observed_to_concept_mapping_performed": False,
        "raw_values_emitted": False,
        "outputs": {
            "vocabulary_csv": "stint-1-evidence-ground-truth/phase_1_lexical/outputs/canonical_vocabulary/external_failure_vocabulary_v1.csv",
            "summary_json": "stint-1-evidence-ground-truth/phase_1_lexical/outputs/f1c2_external_failure_vocabulary_summary.json",
            "memo": "stint-1-evidence-ground-truth/phase_1_lexical/outputs/f1c2_external_failure_vocabulary_memo.md",
        },
    }
    (OUTPUTS_DIR / "f1c2_external_failure_vocabulary_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    lines = [
        "# F1c2 - External Failure Vocabulary Materialization",
        "",
        "## Purpose",
        "",
        "This bounded pass materializes public/reference vocabulary needed before F1d domain grouping.",
        "",
        "It closes the WMEP failure-effects gap and adds subsystem-specific damage/failure evidence sets without merging semantic levels.",
        "",
        "## Result",
        "",
        f"- Vocabulary rows: {summary['rows']}",
        f"- Distinct concept IDs: {summary['distinct_concept_ids']}",
        "- WMEP failure effects: closed",
        "- Damage beyond gearbox: available as published evidence sets",
        "- Observed text to concept mapping: not performed in this pass",
        "- Raw operational values emitted: false",
        "",
        "## Tier Policy",
        "",
        "- `silver-high`: WMEP causes/effects, gearbox NREL GRD, NREL main bearing, blade failure-mode literature, converter field-data literature.",
        "- `silver-medium`: generator, yaw, transformer, and hydraulics sets until failure mode / damage / cause levels are separated.",
        "",
        "## Required Cautions",
        "",
        "- WMEP effects support Symptom-like anchoring but do not prove project-specific Symptom labels.",
        "- NREL GRD remains gearbox-specific.",
        "- The broader subsystem evidence sets are not equivalent vocabularies; F1d must not flatten them into one Damage list.",
        "- Public source URLs were cleaned of `utm_source` parameters, and ResearchGate was not used as a primary source.",
    ]
    (OUTPUTS_DIR / "f1c2_external_failure_vocabulary_memo.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "task": summary["task"],
                "rows": summary["rows"],
                "target_counts": summary["target_counts"],
                "tier_counts": summary["tier_counts"],
                "status_counts": summary["status_counts"],
                "raw_values_emitted": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
