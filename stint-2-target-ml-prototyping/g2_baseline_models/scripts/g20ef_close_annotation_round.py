"""Validate external resubmissions and compare nominal two-level agreement."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import g20ef_validate_responses as validator
from g20ef_register_and_analyze_responses import (
    ANNOTATORS, OUT, csv_text, digest, nominal_metrics, path_for, read,
)

ROOT = validator.ROOT
PLAN = ROOT / 'docs/PLAN-G2.0e\u2014G2.0ef-Closing the Annotation Round.md'
PROTOCOL = validator.PRIVATE / 'protocol/g01-v2.1_protocol.md'
QUALIFIERS = {
    'path': 'B1_RELATIONAL',
    'threshold': 'not_applicable_annotation_agreement',
    'eligible_for_final_heldout': False,
    'evaluation_independence': 'independent',
    'label_generation_method': 'blind_llm_annotation',
}


def response_path(target: str, annotator: str) -> Path:
    number = annotator[-2:]
    name = (f'g20e_activity_responses_v21_annotator_{number}.csv'
            if target == 'activity' else
            f'g20f_damage_responses_annotator_{number}_reformatted.csv')
    return validator.PRIVATE / 'responses' / target / annotator / name


def compare_damage(original: list[dict], new: list[dict]) -> list[dict]:
    if [r['annotation_id'] for r in original] != [r['annotation_id'] for r in new]:
        raise ValueError('Damage ID/order drift')
    repairs = []
    for old, current in zip(original, new):
        if old['group'] != current['group']:
            raise ValueError(f"Changed Damage group: {old['annotation_id']}")
        before, after = old['code'], current['code']
        if before == after:
            continue
        # Only the two committee-authorized serialization repairs are allowed.
        if old['group'] in validator.LEVEL_ONE_EXITS and after == '' and (
                before == old['group'] or before is None):
            repairs.append({
                'annotation_id': old['annotation_id'],
                'repair': ('missing_third_field_to_explicit_empty'
                           if before is None else 'duplicate_exit_to_empty_code'),
                'judgement_changed': False,
            })
        else:
            raise ValueError(f"Changed Damage code: {old['annotation_id']}")
    return repairs


def damage_categories(catalogue: list[dict]) -> tuple[list[str], list[str], set[str]]:
    groups = {r['group'] for r in catalogue}
    pairs = {r['group'] + '|' + r['code'] for r in catalogue}
    group_categories = sorted(groups | validator.LEVEL_ONE_EXITS)
    pair_categories = sorted(pairs | validator.LEVEL_ONE_EXITS |
                             {g + '|abstain' for g in groups})
    assert len(groups) == 9 and len(pairs) == 94
    assert len(group_categories) == 12 and len(pair_categories) == 106
    return group_categories, pair_categories, pairs


def pair_label(row: dict) -> str:
    return row['group'] if row['group'] in validator.LEVEL_ONE_EXITS else (
        row['group'] + '|' + row['code'])


def attach(rows: list[dict], target: str, level: str, n: int) -> list[dict]:
    protocol = 'g01-v2.1' if target == 'activity' else 'g01-v2'
    return [{**QUALIFIERS, 'target': target, 'protocol_version': protocol,
             'evaluation_set_type': f'blind_llm_annotation_{protocol}_diagnostic_non_final',
             'level': level, 'n': n, **row} for row in rows]


def wilson(successes: int, n: int) -> tuple[float, float] | tuple[None, None]:
    if not n:
        return None, None
    z = 1.959963984540054
    p = successes / n
    denominator = 1 + z*z/n
    center = (p + z*z/(2*n)) / denominator
    radius = z*((p*(1-p)/n + z*z/(4*n*n))**0.5)/denominator
    return center - radius, center + radius


def main() -> None:
    protected = [PLAN, PROTOCOL, OUT / 'g20ef_sample_manifest_sanitized.csv']
    protected.extend(p for p in OUT.iterdir() if p.is_file())
    for target in ('activity', 'damage'):
        for annotator in ANNOTATORS:
            protected.extend(path_for(target, annotator, k) for k in
                             ('response', 'package', 'catalogue'))
            protected.append(response_path(target, annotator))
    protected = sorted(set(protected))
    before = {str(p.relative_to(ROOT)): digest(p) for p in protected}
    manifest = read(OUT / 'g20ef_sample_manifest_sanitized.csv')
    files: dict[str, str] = {}

    def emit(name: str, rows: list[dict], fields: list[str] | None = None) -> None:
        files[name] = csv_text(rows, fields or list(rows[0]))

    registrations, repairs, shifts, distribution = [], [], [], []
    agreements, conditions, outcome = [], [], {}
    for target in ('activity', 'damage'):
        batches, originals = {}, {}
        for annotator in ANNOTATORS:
            path = response_path(target, annotator)
            result = validator.validate(target, annotator, path)
            fields = ['annotation_id', 'response'] if target == 'activity' else [
                'annotation_id', 'group', 'code']
            current = validator.read_csv(path, fields)
            original = read(path_for(target, annotator, 'response'))
            assert [r['annotation_id'] for r in original] == [r['annotation_id'] for r in current]
            assert len(current) == (187 if annotator == 'annotator_01' else 188)
            if target == 'damage':
                repairs.extend({'annotator_id': annotator, **r}
                               for r in compare_damage(original, current))
            else:
                shifts.extend({'annotator_id': annotator,
                               'annotation_id': old['annotation_id'],
                               'original_response': old['response'],
                               'v21_response': new['response'],
                               'response_changed': old['response'] != new['response']}
                              for old, new in zip(original, current))
            batches[annotator] = {r['annotation_id']: r for r in current}
            originals[annotator] = {r['annotation_id']: r for r in original}
            registrations.append({
                'target': target, 'annotator_id': annotator,
                'protocol_version': 'g01-v2.1' if target == 'activity' else 'g01-v2',
                'action': 'reannotation' if target == 'activity' else 'format_redelivery',
                'file': str(path.relative_to(ROOT)), 'sha256': digest(path),
                'original_sha256': digest(path_for(target, annotator, 'response')),
                'rows': len(current), 'expected_rows': len(current),
                'validation_status': result['status'], 'duplicates': 0,
                'missing_ids': 0, 'extra_ids': 0, 'malformed_rows': 0,
                'annotation_date': 'not_supplied', 'received_via': 'user_supplied_chat_csv',
                'judgements_unchanged': True if target == 'damage' else 'not_applicable_reannotation',
                'response_process_compliance': 'cannot_be_verified_from_csv_alone',
            })
            labels = Counter(r['response'] if target == 'activity' else r['group'] for r in current)
            codes = read(path_for(target, annotator, 'catalogue'))
            code_set = {r['code'] for r in codes}
            assigned_count = sum(r['response'] in code_set for r in current) if target == 'activity' else (
                sum(r['group'] not in validator.LEVEL_ONE_EXITS and r['code'] != 'abstain' for r in current))
            for label, count in sorted(labels.items()):
                distribution.extend(attach([{
                    'annotator_id': annotator, 'category': label, 'count': count,
                    'fraction': count/len(current),
                    'level_one_abstention_rate': labels['abstain']/len(current),
                    'code_level_abstentions': (sum(r['code'] == 'abstain' for r in current)
                                               if target == 'damage' else 0),
                    'assigned_codes': assigned_count,
                    'assigned_code_rate': assigned_count/len(current),
                    'scope': 'annotation_sample_not_population',
                }], target, 'response' if target == 'activity' else 'group', len(current)))

        a, b = (batches[x] for x in ANNOTATORS)
        expected = {r['annotation_id'] for r in manifest
                    if r['target'] == target and r['overlap_record'] == 'True'}
        shared = sorted(set(a) & set(b))
        assert len(expected) == len(shared) == 75 and set(shared) == expected
        assert len(set(a) | set(b)) == 300
        catalogue = read(path_for(target, ANNOTATORS[0], 'catalogue'))
        assert catalogue == read(path_for(target, ANNOTATORS[1], 'catalogue'))
        levels = {}
        if target == 'activity':
            categories = sorted({r['code'] for r in catalogue} | validator.ACTIVITY_EXITS)
            levels['response'] = ([a[k]['response'] for k in shared],
                                  [b[k]['response'] for k in shared], categories)
            prefix = 'g20e_activity_v21'
        else:
            groups, pairs, _ = damage_categories(catalogue)
            levels['group'] = ([a[k]['group'] for k in shared], [b[k]['group'] for k in shared], groups)
            levels['group_code'] = ([pair_label(a[k]) for k in shared],
                                    [pair_label(b[k]) for k in shared], pairs)
            prefix = 'g20f_damage'
        local_metrics = []
        for level, (left, right, categories) in levels.items():
            metrics, classes, matrix = nominal_metrics(left, right, categories)
            qualified = attach([{'status': 'valid', **metrics}], target, level, len(shared))[0]
            agreements.append(qualified)
            local_metrics.append(qualified)
            emit(f'{prefix}_{level}_per_class_agreement_sanitized.csv',
                 attach(classes, target, level, len(shared)))
            emit(f'{prefix}_{level}_confusion_matrix_sanitized.csv',
                 attach(matrix, target, level, len(shared)))

        code_set = {r['code'] for r in catalogue}

        def assigned(row: dict) -> bool:
            return row['response'] in code_set if target == 'activity' else (
                row['group'] not in validator.LEVEL_ONE_EXITS and row['code'] != 'abstain')

        both = [k for k in shared if assigned(a[k]) and assigned(b[k])]
        left_only = [k for k in shared if assigned(a[k]) and not assigned(b[k])]
        right_only = [k for k in shared if not assigned(a[k]) and assigned(b[k])]
        neither = [k for k in shared if not assigned(a[k]) and not assigned(b[k])]
        assert len(both) + len(left_only) + len(right_only) + len(neither) == 75
        labeling = (lambda r: r['response']) if target == 'activity' else pair_label
        matches = sum(labeling(a[k]) == labeling(b[k]) for k in both)
        ci_low, ci_high = wilson(matches, len(both))
        conditions.append(attach([{
            'both_assigned': len(both), 'only_annotator_01_assigned': len(left_only),
            'only_annotator_02_assigned': len(right_only), 'neither_assigned': len(neither),
            'both_assigned_matching_group_code': matches,
            'conditional_code_agreement': matches/len(both) if both else '',
            'conditional_n': len(both), 'wilson95_low': ci_low if both else '',
            'wilson95_high': ci_high if both else '',
            'interpretation': 'selected_subset_agreement_not_accuracy_or_coverage',
        }], target, 'code_assignment_conditioning', 75)[0])
        if both:
            c = sorted(code_set) if target == 'activity' else sorted({
                r['group'] + '|' + r['code'] for r in catalogue})
            metrics, classes, matrix = nominal_metrics(
                [labeling(a[k]) for k in both], [labeling(b[k]) for k in both], c)
            agreements.extend(attach([{'status': 'valid_selected_subset', **metrics}],
                                     target, 'both_assigned_group_code', len(both)))
            emit(f'{prefix}_both_assigned_confusion_matrix_sanitized.csv',
                 attach(matrix, target, 'both_assigned_group_code', len(both)))
            emit(f'{prefix}_both_assigned_per_class_agreement_sanitized.csv',
                 attach(classes, target, 'both_assigned_group_code', len(both)))
        paired = []
        for k in shared:
            row = {'annotation_id': k, 'annotator_01_response': labeling(a[k]),
                   'annotator_02_response': labeling(b[k]),
                   'annotator_01_code_assigned': assigned(a[k]),
                   'annotator_02_code_assigned': assigned(b[k]),
                   'agreement': labeling(a[k]) == labeling(b[k])}
            paired.extend(attach([row], target, 'response' if target == 'activity' else 'group_code', 75))
        emit(f'{prefix}_overlap_responses_sanitized.csv', paired)
        outcome[target] = {
            'metrics': local_metrics, 'conditional': conditions[-1],
            'nonzero_matrix': {level: [r for r in nominal_metrics(*data)[2] if r['count']]
                               for level, data in levels.items()},
        }
        if target == 'activity':
            old_a, old_b = (originals[x] for x in ANNOTATORS)
            old_metric = nominal_metrics([old_a[k]['response'] for k in shared],
                                         [old_b[k]['response'] for k in shared], categories)[0]
            outcome[target]['original_metrics_recomputed'] = old_metric

    emit('g20ef_closing_response_receipt_register_sanitized.csv', registrations)
    emit('g20f_damage_format_repair_audit_sanitized.csv', repairs)
    emit('g20e_activity_v21_response_changes_sanitized.csv', shifts)
    emit('g20ef_closing_class_distribution_sanitized.csv', distribution)
    emit('g20ef_closing_conditional_code_agreement_sanitized.csv', conditions)
    emit('g20e_activity_agreement_v21_sanitized.csv', [r for r in agreements if r['target'] == 'activity'])
    emit('g20f_damage_agreement_sanitized.csv', [r for r in agreements if r['target'] == 'damage'])
    act = outcome['activity']['metrics'][0]
    dam = outcome['damage']['metrics'][0]
    old = outcome['activity']['original_metrics_recomputed']
    lines = [
        '# G2.0e/f - Closing comparison memo', '',
        'All four external resubmissions passed the structural gate: 187/188',
        'rows per target, exact IDs, valid controlled responses, mode 600.',
        'Same 300 physical units per target, exactly 75 shared IDs; no resampling.',
        'Original receipts, packages, catalogue and original reports are unchanged.', '',
        '## Damage format-only verification', '',
        f'{len(repairs)} serialization repairs verified; no judgement changed.',
        '01: duplicate none_applicable removed from code, retaining group.',
        '02: the explicit empty third field for 0293 was supplied by the user',
        'in a separate correction message; that supplied correction is included.',
        'No DevOps response assignment or adjudication occurred.', '',
        '## Agreement on the overlap', '',
        '| Target / level | n | matching | raw | kappa | AC1 |',
        '| --- | ---: | ---: | ---: | ---: | ---: |',
    ]
    for row in agreements:
        kappa = 'not_estimable' if row['cohen_kappa'] is None else f"{row['cohen_kappa']:.6f}"
        lines.append(f"| {row['target']} / {row['level']} | {row['n']} | {row['matching']} | "
                     f"{row['raw_agreement']:.6f} | {kappa} | {row['gwet_ac1']:.6f} |")
    lines.extend(['', 'Activity original v2 vs v2.1 on the same 75 units:',
                  f"raw {old['raw_agreement']:.6f} -> {act['raw_agreement']:.6f}; "
                  f"kappa {old['cohen_kappa']:.6f} -> {act['cohen_kappa']:.6f}.", '',
                  '## Assigned-code conditioning', ''])
    for row in conditions:
        lines.append(f"{row['target']}: both assigned {row['both_assigned']}; only 01 "
                     f"{row['only_annotator_01_assigned']}; only 02 {row['only_annotator_02_assigned']}; "
                     f"neither {row['neither_assigned']}. Conditional exact group/code matches "
                     f"{row['both_assigned_matching_group_code']}/{row['both_assigned']}.")
    lines.extend(['', 'Full confusion matrices and per-class specific agreement are separate',
                  'sanitized CSVs. Specific agreement = 2*diagonal/(row+column marginal);',
                  'an unobserved class has no estimable agreement, not zero.',
                  'Damage code level uses group|code pairs, never code strings alone.',
                  'Level-one exits remain distinct outcomes, not matching empty codes.',
                  'Conditional agreement selects cases both annotators chose to code;',
                  'it is not catalogue coverage, SAP correctness, or corpus precision.', '',
                  '## Methods and limitations', '',
                  'Unweighted nominal kappa and Gwet AC1; no ordinal AC2 is appropriate.',
                  'AC1 uses fixed complete vocabularies: Activity 9, Damage group 12,',
                  'Damage group/code 106 (94 pairs + 3 exits + 9 group/code abstentions).',
                  'Both-assigned subset uses 5/94 catalogue outcomes respectively.',
                  'Category-count policy is explicit; AC1 depends on this choice.',
                  'Formula reference: https://pmc.ncbi.nlm.nih.gov/articles/PMC5965565/',
                  'Wilson intervals are descriptive, not guarantees of SAP accuracy.',
                  'Both annotators are LLMs, not SMEs. Models, annotation timestamps and',
                  'no-script compliance cannot be verified from CSV labels alone.',
                  'A3 was approved and communicated before re-annotation per chat;',
                  'the v2.1 repository addendum is an after-receipt archival snapshot,',
                  'not a retroactive claim that a file was frozen before annotation.',
                  'Activity frame is 1,234 units; rates describe the sample, not B1.',
                  'All metrics: B1_RELATIONAL, stated n, blind_llm_annotation, protocol',
                  'v2/v2.1 as declared, no classifier threshold. Non-final diagnostic:',
                  'eligible_for_final_heldout=false. No F6 or frozen evaluation change.', ''])
    files['g20ef_round_comparison_memo.md'] = '\n'.join(lines)
    run = {
        'registered_at_utc': datetime.now(timezone.utc).isoformat(),
        'inputs_sha256': before, 'originals_unchanged': True,
        'overlap_integrity': {'activity': 75, 'damage': 75},
        'outcomes': outcome, 'registrations': registrations,
        'damage_serialization_repairs': Counter(r['annotator_id'] for r in repairs),
        'protocol_snapshot_timing': 'archived_after_receipt_approved_rule_preceded_annotation_per_chat',
        'normalization': 'none_on_responses',
        'damage02_last_field_provenance': 'explicit_user_correction_message',
        'output_sha256': {},
    }
    import hashlib
    run['output_sha256'] = {name: hashlib.sha256(text.encode('utf-8')).hexdigest()
                            for name, text in files.items()}
    files['g20ef_closing_run_manifest.json'] = json.dumps(run, indent=2, sort_keys=True) + '\n'
    if any((OUT / name).exists() for name in files):
        raise FileExistsError('Refusing to overwrite any closure output')
    assert all(digest(ROOT / name) == value for name, value in before.items())
    for name, content in files.items():
        with (OUT / name).open('x', encoding='utf-8', newline='') as handle:
            handle.write(content)
    assert all(digest(ROOT / name) == value for name, value in before.items())
    print(json.dumps({'outcomes': outcome, 'registrations': registrations,
                      'damage_repairs': run['damage_serialization_repairs']}, indent=2))


if __name__ == '__main__':
    main()
