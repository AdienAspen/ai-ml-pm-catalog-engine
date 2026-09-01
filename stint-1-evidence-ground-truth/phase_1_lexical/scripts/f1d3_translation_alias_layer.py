from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
F1_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth" / "phase_1_lexical"
OUTPUTS_DIR = F1_ROOT / "outputs"
VOCAB_DIR = OUTPUTS_DIR / "canonical_vocabulary"
EXTERNAL_VOCAB = VOCAB_DIR / "external_failure_vocabulary_v1.csv"


ALIASES_ES = {
    "high wind": "viento fuerte",
    "grid failure": "falla de red",
    "lightning": "rayo",
    "icing": "hielo",
    "malfunction of control systems": "falla de sistema de control",
    "component wear or failure": "desgaste o falla de componente",
    "loosening of parts": "aflojamiento de partes",
    "other causes": "otras causas",
    "unknown causes": "causas desconocidas",
    "Overspeed": "sobrevelocidad",
    "Overload": "sobrecarga",
    "Noise": "ruido",
    "Vibration": "vibracion",
    "Reduced power": "potencia reducida",
    "Causing follow-up damage": "dano consecuente",
    "Plant stoppage": "detencion de planta",
    "Other consequences": "otras consecuencias",
    "axial cracks": "grietas axiales",
    "hardening cracks": "grietas de temple",
    "scuffing / severe adhesion": "rayado severo adhesion",
    "macropitting": "macropicadura",
    "micropitting": "micropicadura",
    "fretting corrosion": "corrosion por friccion",
    "false brinelling": "falso brinelling",
    "debris dents": "indentacion por particulas",
    "contact corrosion": "corrosion de contacto",
    "abrasion": "abrasion",
    "assembly damage": "dano de montaje",
    "plastic deformation": "deformacion plastica",
    "overheating": "sobrecalentamiento",
    "polishing wear": "desgaste por pulido",
    "subsurface initiated bending fatigue": "fatiga por flexion subsuperficial",
    "polishing": "pulido",
    "lack of lubrication": "falta de lubricacion",
    "misalignment": "desalineacion",
    "poor load distribution": "mala distribucion de carga",
    "manufacturing defects": "defectos de fabricacion",
    "non-metallic inclusions": "inclusiones no metalicas",
    "microstructural banding": "bandeado microestructural",
    "spalling": "desconchamiento",
    "surface damage": "dano superficial",
    "surface-initiated rolling contact fatigue": "fatiga de contacto iniciada en superficie",
    "wear induced": "inducido por desgaste",
    "subsurface-initiated rolling contact fatigue": "fatiga de contacto iniciada bajo superficie",
    "adhesive wear": "desgaste adhesivo",
    "standstill corrosion": "corrosion en parada",
}


def stable_key(value: object, prefix: str) -> str:
    raw = "" if value is None or pd.isna(value) else str(value)
    return f"{prefix}-{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:12]}"


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if not EXTERNAL_VOCAB.exists():
        raise FileNotFoundError(f"Missing external vocabulary: {EXTERNAL_VOCAB}")
    vocab = pd.read_csv(EXTERNAL_VOCAB)
    rows: list[dict] = []
    missing_alias_sources: list[str] = []

    for english_term, alias_es in ALIASES_ES.items():
        matches = vocab[vocab["canonical_concept"] == english_term]
        if matches.empty:
            missing_alias_sources.append(english_term)
            continue
        for _, source in matches.iterrows():
            rows.append(
                {
                    "alias_id": stable_key(f"{source['concept_id']}|es|{alias_es}", "ALIAS"),
                    "canonical_concept_id": source["concept_id"],
                    "canonical_concept_key": source["canonical_concept_key"],
                    "canonical_alias_es": alias_es,
                    "canonical_alias_key": stable_key(alias_es, "ALIASKEY"),
                    "target": source["target"],
                    "namespace": source["namespace"],
                    "target_field": source["target_field"],
                    "vocabulary_owner": source["vocabulary_owner"],
                    "subsystem": source["subsystem"],
                    "semantic_level": source["semantic_level"],
                    "alias_language": "es",
                    "evidence_type": "expert_inference",
                    "tier": "silver-medium",
                    "status": "translation_alias",
                    "source": "project_team_translation_alias",
                    "source_version": "F1d3",
                    "source_date": "2026-09-01",
                    "label_generation_method": "translation_alias_rule_set_v1",
                    "evaluation_independence": "derived_from_rules",
                    "can_support_contractual_denominator": False,
                    "can_support_proxy_denominator": False,
                    "raw_values_emitted": False,
                }
            )

    fields = [
        "alias_id",
        "canonical_concept_id",
        "canonical_concept_key",
        "canonical_alias_es",
        "canonical_alias_key",
        "target",
        "namespace",
        "target_field",
        "vocabulary_owner",
        "subsystem",
        "semantic_level",
        "alias_language",
        "evidence_type",
        "tier",
        "status",
        "source",
        "source_version",
        "source_date",
        "label_generation_method",
        "evaluation_independence",
        "can_support_contractual_denominator",
        "can_support_proxy_denominator",
        "raw_values_emitted",
    ]
    write_csv(VOCAB_DIR / "translation_aliases_es_v1.csv", rows, fields)

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "F1d3_translation_alias_layer",
        "alias_rows": len(rows),
        "missing_alias_sources": len(missing_alias_sources),
        "target_counts": dict(Counter(row["target"] for row in rows)),
        "owner_counts": dict(Counter(row["vocabulary_owner"] for row in rows)),
        "evidence_type": "expert_inference",
        "tier": "silver-medium",
        "evaluation_independence": "derived_from_rules",
        "raw_values_emitted": False,
        "outputs": {
            "alias_csv": "stint-1-evidence-ground-truth/phase_1_lexical/outputs/canonical_vocabulary/translation_aliases_es_v1.csv",
            "summary_json": "stint-1-evidence-ground-truth/phase_1_lexical/outputs/f1d3_translation_alias_layer_summary.json",
            "memo": "stint-1-evidence-ground-truth/phase_1_lexical/outputs/f1d3_translation_alias_layer_memo.md",
        },
    }
    (OUTPUTS_DIR / "f1d3_translation_alias_layer_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    lines = [
        "# F1d3 - Translation Alias Layer",
        "",
        "## Purpose",
        "",
        "This pass adds Spanish aliases for selected public/reference English concepts so matching can run against both canonical English terms and project-team translation aliases.",
        "",
        "Aliases are not `reference_evidence`; they are `expert_inference` in a separate column and layer.",
        "",
        "## Result",
        "",
        f"- Alias rows: {summary['alias_rows']}",
        f"- Missing alias sources: {summary['missing_alias_sources']}",
        "- Evidence type: `expert_inference`",
        "- Tier: `silver-medium`",
        "- Evaluation independence: `derived_from_rules`",
        "",
        "## Governance",
        "",
        "- Aliases may improve semantic matching coverage, but they are not validated mappings.",
        "- Aliases cannot support contractual denominators.",
        "- Matching against aliases must preserve the original canonical concept ID.",
    ]
    (OUTPUTS_DIR / "f1d3_translation_alias_layer_memo.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
