"""Report-only catalogue semantic coverage and separately characterized residuals."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

import numpy as np
import pandas as pd
from openpyxl import load_workbook
from sentence_transformers import SentenceTransformer
from sklearn.cluster import MiniBatchKMeans

import g20c_neutral_ngram_extraction as extraction
import g20c_step2_filtering as filtering
import g20d_catalogue_free_coverage as lexical
import g20d2_semantic_reference_coverage as semantic
import g20h_profile_inheritance as profiles
from g20c_lexical_safety import restricted_match, TERMS_FILE
from g20c_lexical_safety import restricted_terms
from g20ef_prepare_annotation_packages import sanitize

ROOT = extraction.STINT2_ROOT
OUT = ROOT / 'g2_baseline_models/outputs/g20j_catalogue_code_coverage'
PRIVATE = ROOT / 'g2_baseline_models/internal/g20j_catalogue_code_coverage'
PLAN = ROOT / 'docs/PLAN-G2.0j\u2014symptom_cause-against-catalog-codes.md'
CATALOGUE = profiles.CATALOG
ZEUS = lexical.ZEUS
OLD = semantic.OUT / 'g20d2_unit_scores_sanitized.csv'
COMPONENTS = ROOT / ('g2_baseline_models/outputs/g20i_profile_consensus/'
                     'g20i_profile_consensus_by_order_sanitized.csv')
G12 = profiles.G12 / 'internal/g12_floc_alignment_internal_review.csv'
TYPES = {'Symptom': 'S', 'Cause': '5'}
EXPECTED = {'Symptom': (4171, 6), 'Cause': (6232, 13)}
SETTINGS = {
    'model': semantic.MODEL_NAME,
    'normalization': 'semantic_normalisation_v2',
    'catalogue_threshold': 0.50,
    'presence_threshold': 0.50,
    'threshold_basis': 'historical_T5.1b2X_value_not_calibrated_for_new_catalogue',
    'description_input': 'verbatim_no_normalization_paraphrase_or_typo_correction',
    'scoring': 'T5.1b2X_L2_cosine_max_over_independent_normalized_source_segments',
    'tie_tolerance': 1e-6,
    'tie_policy': 'stable_lexicographic_composite_key_report_all_max_tie_count',
    'universe': lexical.ELIGIBLE,
    'presence_symptom': 'ZEUS_detection_symptom_frozen_definition_OR_WMEP_EFFECTS_reference',
    'presence_cause': 'WMEP_CAUSES_only_9_frozen_phrases',
    'residual_ngram_sizes': [1, 2, 3],
    'residual_frequency_floors': filtering.FREQUENCY_FLOORS,
    'residual_grouping': 'MiniBatchKMeans_normalized_embeddings_no_string_distance',
    'residual_k_rule': 'min(256,max(1,round(sqrt(distinct_retained_terms))))',
    'residual_random_state': 20260921,
    'residual_member_cosine_min': 0.50,
    'residual_min_members': 2,
    'residual_target_assignment': 'inherited_from_domain_presence_test_not_term_classification',
    'residual_reference_role': 'diagnostic_only_not_added_to_training_or_reference_vocabulary',
    'no_catalogue_code_interpretation': 'candidate_configuration_gap_or_detector_miss_not_confirmed_gap',
    'no_promotion': True, 'no_denominator_change': True,
}
META = {
    'anchor_source': 'sap_catalog_as_class_space',
    'evidence_type': 'expert_inference', 'tier': 'silver-medium',
    'label_generation_method': 'semantic_catalogue_code_matching_v1',
    'embedding_model': semantic.MODEL_NAME,
    'evaluation_independence': 'derived_from_rules',
    'evaluation_set_type': 'not_evaluation_descriptive_candidate_coverage',
    'eligible_for_final_heldout': False,
    'threshold': 0.50, 'presence_threshold': 0.50,
    'raw_operational_values_emitted': False,
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(extraction.PROJECT_ROOT))


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    if path.exists():
        raise FileExistsError(path)
    frame.to_csv(path, index=False, lineterminator='\n')
    reread = pd.read_csv(path, keep_default_na=False)
    assert len(reread) == len(frame) and list(reread.columns) == list(frame.columns)


def write_json(path: Path, data: dict) -> None:
    with path.open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(data, indent=2, sort_keys=True) + '\n')


def catalogue_rows() -> pd.DataFrame:
    book = load_workbook(CATALOGUE, read_only=True, data_only=True)
    rows = []
    try:
        associations = set()
        for row in list(book['Catalog Profile and Code Groups'].values)[1:]:
            if row[0] == 'PMMUWW':
                associations.add((str(row[2]), str(row[3])))
        for target, typ in TYPES.items():
            sheet = f'Catalog. {typ} - Group and Code'
            iterator = book[sheet].iter_rows(values_only=True)
            headers = next(iterator)
            for number, values in enumerate(iterator, 2):
                source = dict(zip(headers, values, strict=True))
                if not source.get('Code'):
                    continue
                group, code = str(source['Code Group']), str(source['Code'])
                text = str(source['Short Text for Code'])
                assert source['Catalog'] == typ and group and code and text
                rows.append({'target': target, 'catalog_type': typ,
                             'code_group': group, 'code': code,
                             'catalogue_key': '|'.join((typ, group, code)),
                             'description': text,
                             'description_sha256': hashlib.sha256(text.encode()).hexdigest(),
                             'profile_scoped': (typ, group) in associations,
                             'source_sheet': sheet, 'source_row': number})
    finally:
        book.close()
    frame = pd.DataFrame(rows).sort_values('catalogue_key').reset_index(drop=True)
    assert not frame.catalogue_key.duplicated().any()
    for target, (wide, narrow) in EXPECTED.items():
        subset = frame[frame.target.eq(target)]
        assert len(subset) == wide and int(subset.profile_scoped.sum()) == narrow
        assert subset[subset.profile_scoped].code_group.nunique() == 1
    return frame


def domain_rows() -> pd.DataFrame:
    external = pd.read_csv(lexical.EXTERNAL).fillna('')
    selected = external[external.vocabulary_owner.isin(['WMEP_EFFECTS', 'WMEP_CAUSES'])]
    rows = [{'target': r.target, 'prototype_id': r.concept_id,
             'prototype_text': ' '.join(extraction.normalise_text(r.canonical_concept)[0]),
             'source': r.vocabulary_owner, 'semantic_role': 'operational_consequence_reference'
             if r.target == 'Symptom' else 'cause_presence_reference',
             'source_artifact': relative(lexical.EXTERNAL)} for r in selected.itertuples()]
    zeus = pd.read_csv(ZEUS).fillna('')
    category = zeus[zeus.zeus_category.eq('detection_symptom')]
    assert len(category) == 1
    for r in category.itertuples():
        rows.append({'target': 'Symptom', 'prototype_id': r.concept_id,
                     'prototype_text': ' '.join(extraction.normalise_text(r.working_definition)[0]),
                     'source': 'ZEUS_detection_symptom',
                     'semantic_role': 'frozen_container_definition_presence_test_not_lexicon',
                     'source_artifact': relative(ZEUS)})
    frame = pd.DataFrame(rows)
    assert frame.groupby('target').size().to_dict() == {'Cause': 9, 'Symptom': 9}
    assert not frame.prototype_text.map(restricted_match).any()
    return frame


def input_paths() -> list[Path]:
    paths = [PLAN, CATALOGUE, ZEUS, lexical.EXTERNAL, OLD, COMPONENTS, G12,
             profiles.IH06, TERMS_FILE, extraction.LEAKAGE_REGEX_CATALOG,
             extraction.LEAKAGE_MASKING_MANIFEST, semantic.T51_SCRIPT,
             Path(__file__), Path(extraction.__file__), Path(filtering.__file__),
             Path(lexical.__file__), Path(semantic.__file__), Path(profiles.__file__),
             Path(__file__).with_name('g20ef_prepare_annotation_packages.py'),
             ROOT/'g0_independent_evaluation/scripts/g02_build_stratified_annotation_packages.py',
             Path(__file__).with_name('g20c_lexical_safety.py')]
    paths.extend(ROOT.rglob('*split_manifest*.csv'))
    paths.extend(p for base in (ROOT/'artifacts/evaluation_sets', lexical.F6.parent)
                 for p in base.rglob('*') if p.is_file())
    return sorted(set(paths))


def freeze() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    os.chmod(PRIVATE, 0o700)
    if (OUT/'g20j_freeze_manifest.json').exists():
        raise FileExistsError('Instrument already frozen; no retrospective changes')
    cat, domain = catalogue_rows(), domain_rows()
    registry = cat.drop(columns='description').copy()
    registry['prototype_source'] = relative(CATALOGUE)
    registry['construction_method'] = 'transcribed_catalogue_description_verbatim'
    registry['evaluation_exclusion'] = 'not_evaluation_catalogue_class_space_reference'
    write_csv(OUT/'g20j_catalogue_registry_sanitized.csv', registry)
    write_csv(OUT/'g20j_domain_presence_registry_sanitized.csv', domain)
    write_json(OUT/'g20j_freeze_manifest.json', {
        'frozen_at_utc': datetime.now(timezone.utc).isoformat(),
        'settings': SETTINGS, 'coverage_observed': False,
        'source_sha256': {relative(p): sha(p) for p in input_paths()},
        'corpus_input_sha256': lexical.corpus_input_hashes(),
        'registry_sha256': {p.name: sha(p) for p in OUT.glob('*registry*.csv')},
        'catalogue_counts': EXPECTED,
        'profile_scope_warning': '3934_component_profiles_are_not_all_PMMUWW_do_not_add_to_9151',
        'activity_plan_statistic_warning': '1_of_375_is_stale_v21_received_has_6_of_375_responses',
    })
    print('Frozen BEFORE scoring: catalogue=0.50, domain presence=0.50; two targets/two code spaces.', flush=True)


def verify_freeze() -> dict:
    frozen = json.loads((OUT/'g20j_freeze_manifest.json').read_text())
    assert frozen['settings'] == SETTINGS
    for rel, digest in frozen['source_sha256'].items():
        assert sha(extraction.PROJECT_ROOT/rel) == digest, rel
    for name, digest in frozen['registry_sha256'].items():
        assert sha(OUT/name) == digest, name
    assert lexical.corpus_input_hashes() == frozen['corpus_input_sha256']
    return frozen


def profile_metadata() -> dict[str, dict]:
    nodes = profiles.load_ih06()
    valid = profiles.load_valid_profiles()
    direct = profiles.read_csv(G12)
    comp = pd.read_csv(COMPONENTS).fillna('').set_index('order_id_hash')
    result, direct_counts, component_counts = {}, Counter(), Counter()
    for row in direct:
        order_hash = extraction.prefixed_hash('ORDER', row['order_id'], 16)
        profile = ''
        if row['match_status'] == 'matched_asset_node':
            node = row['matched_floc']
            profile = nodes[node]['profile']
            if profile not in valid:
                _, profile, _, _ = profiles.walk_ancestors(nodes, node, valid)
            scope = 'structural_PMMUWW' if profile == 'PMMUWW' else (
                'structural_other_profile' if profile else 'no_profile_no_filter')
        else:
            scope = 'unmatched_structural_asset'
        direct_counts[scope] += 1
        component = comp.loc[order_hash]
        cp = component.resolved_rbnr if component.profile_status in (
            'resolved_node', 'resolved_node_ambiguous') else ''
        if cp:
            component_counts[cp] += 1
        key = lexical.unit_hash(extraction.physical_record_id(row['order_id']))
        result[key] = {'structural_profile_scope': scope,
                       'component_profile_present': bool(cp),
                       'component_profile_is_PMMUWW': cp == 'PMMUWW',
                       'component_profile_dependency': 'text_derived_not_independent' if cp else 'none'}
    assert direct_counts['structural_PMMUWW'] == 9151
    assert direct_counts['no_profile_no_filter'] == 1548
    assert sum(component_counts.values()) == 3934
    print('Profile scopes verified: turbine PMMUWW=9151, component profiles=3934/30 types (overlapping).', flush=True)
    return result


def prepare() -> None:
    verify_freeze()
    if (PRIVATE/'g20j_corpus_vectors.npz').exists():
        raise FileExistsError('Prepared corpus already exists')
    extraction.LEAKAGE_PATTERNS = extraction.load_leakage_patterns()
    units = extraction.load_b1_units() + extraction.load_path_a_units() + extraction.load_b2_units()
    assert len(units) == 12968 and len({u['unit_key'] for u in units}) == 12968
    old = pd.read_csv(OLD).fillna('')
    old = old[old.target.eq('Symptom')].set_index('unit_key_hash')
    exclusions = extraction.load_exclusions()
    text_index, texts, prepared, mask_keys = {}, [], [], set()
    pm = profile_metadata()
    restricted = restricted_terms()
    universe_counts = Counter()
    for unit in units:
        key = lexical.unit_hash(unit['unit_key'])
        prior = old.loc[key]
        reason = extraction.exclusion_reason(unit, *exclusions[:4])
        assert bool(prior.construction_eligible) == (not reason)
        assert prior.path_bucket == unit['path_bucket']
        tokens_by_segment, residual_segments = [], []
        mask_count = 0
        for _, text in unit['segments']:
            masked, count, _ = extraction.apply_leakage_mask(text, extraction.LEAKAGE_PATTERNS)
            mask_count += count
            assert not any(p.search(masked) for p, _, _ in extraction.LEAKAGE_PATTERNS)
            tokens_by_segment.append(extraction.normalise_text(masked)[0])
            sanitized = sanitize(text, extraction.LEAKAGE_PATTERNS, restricted)
            residual_segments.append(' '.join(extraction.normalise_text(sanitized)[0]))
        if mask_count:
            mask_keys.add(unit['source_unit_key'])
        universe_counts[(unit['path_bucket'], 'excluded' if reason else 'eligible')] += 1
        if reason:
            continue
        ids = []
        for tokens in tokens_by_segment:
            text = ' '.join(tokens)
            if not text:
                continue
            if text not in text_index:
                text_index[text] = len(texts)
                texts.append(text)
            ids.append(text_index[text])
        metadata = pm.get(key, {'structural_profile_scope': 'not_resolved_for_path',
                                'component_profile_present': False,
                                'component_profile_is_PMMUWW': False,
                                'component_profile_dependency': 'not_available'})
        prepared.append({'unit_key_hash': key, 'path_bucket': unit['path_bucket'],
                         'segment_indices': sorted(set(ids)), 'leakage_mask_applied': bool(mask_count),
                         'residual_segments': residual_segments,
                         **metadata})
    assert mask_keys == set(pd.read_csv(extraction.LEAKAGE_MASKING_MANIFEST).source_unit_key)
    assert len(mask_keys) == 13
    assert Counter(u['path_bucket'] for u in prepared) == {
        'B1_RELATIONAL': 9263, 'B2_WORKBOOKS': 1478, 'PATH_A': 159}
    print(f'Eligible corpus: {len(prepared)} units; {len(texts)} unique normalized segments.', flush=True)
    model = SentenceTransformer(semantic.MODEL_NAME, local_files_only=True)
    model[0].auto_model.config._name_or_path
    chunks = []
    for start in range(0, len(texts), 1024):
        chunks.append(model.encode(texts[start:start+1024], normalize_embeddings=True,
                                  show_progress_bar=False, batch_size=64, convert_to_numpy=True))
        print(f'Embedded corpus {min(start+1024,len(texts))}/{len(texts)}', flush=True)
    os.umask(0o077)
    np.savez_compressed(PRIVATE/'g20j_corpus_vectors.npz', vectors=np.vstack(chunks))
    write_json(PRIVATE/'g20j_prepared_corpus_internal.json', {'units': prepared, 'texts': texts})
    for p in (PRIVATE/'g20j_corpus_vectors.npz', PRIVATE/'g20j_prepared_corpus_internal.json'):
        os.chmod(p, 0o600)
    counts = [{'path_bucket': path, 'eligibility': eligible, 'units': n,
               'universe': lexical.ELIGIBLE, 'exclusions_reported_separately': True}
              for (path, eligible), n in sorted(universe_counts.items())]
    write_csv(OUT/'g20j_universe_register_sanitized.csv', pd.DataFrame(counts))
    write_json(OUT/'g20j_prepare_manifest.json', {
        'prepared_at_utc': datetime.now(timezone.utc).isoformat(),
        'masked_full_corpus_units': 13, 'eligible_units': len(prepared),
        'unique_normalized_segments': len(texts),
        'model_revision': model[0].auto_model.config._commit_hash,
        'cache_sha256': {p.name: sha(p) for p in PRIVATE.iterdir() if p.is_file()},
        'freeze_sha256': sha(OUT/'g20j_freeze_manifest.json')})
    verify_freeze()


def partition(catalogue_present: bool, domain_present: bool) -> str:
    if catalogue_present:
        return 'catalogue_and_domain' if domain_present else 'catalogue_only'
    return 'no_catalogue_code' if domain_present else 'no_anchor_at_all'


def segment_winners(vectors: np.ndarray, prototypes: np.ndarray, scoring) -> tuple[np.ndarray, list]:
    maxima, tied = [], []
    eps = SETTINGS['tie_tolerance']
    for start in range(0, len(vectors), 256):
        scores = scoring.cosine_matrix(vectors[start:start+256], prototypes)
        best = scores.max(axis=1)
        maxima.extend(best.tolist())
        for row, value in zip(scores, best):
            ids = np.flatnonzero(row >= value-eps)
            tied.append((ids, row[ids]))
    return np.asarray(maxima), tied


def unit_winner(indices: list[int], maxima: np.ndarray, tied: list) -> tuple[float | None, int, int]:
    if not indices:
        return None, -1, 0
    best = float(maxima[indices].max())
    ids = set()
    for i in indices:
        if maxima[i] >= best-SETTINGS['tie_tolerance']:
            positions, values = tied[i]
            ids.update(int(p) for p, v in zip(positions, values)
                       if v >= best-SETTINGS['tie_tolerance'])
    return best, min(ids), len(ids)


def measure(target: str) -> None:
    verify_freeze()
    output = OUT/f'g20j_{target.lower()}_unit_scores_sanitized.csv'
    if output.exists():
        raise FileExistsError('Target already scored; do not overwrite a run')
    prepared_manifest = json.loads((OUT/'g20j_prepare_manifest.json').read_text())
    for name, digest in prepared_manifest['cache_sha256'].items():
        assert sha(PRIVATE/name) == digest
    cache = json.loads((PRIVATE/'g20j_prepared_corpus_internal.json').read_text())
    vectors = np.load(PRIVATE/'g20j_corpus_vectors.npz')['vectors']
    cat = catalogue_rows()
    cat = cat[cat.target.eq(target)].reset_index(drop=True)
    domain = domain_rows()
    domain = domain[domain.target.eq(target)].reset_index(drop=True)
    model = SentenceTransformer(semantic.MODEL_NAME, local_files_only=True)
    assert model[0].auto_model.config._commit_hash == prepared_manifest['model_revision']
    descriptions = cat.description.drop_duplicates().tolist()
    print(f'{target}: embedding {len(descriptions)} distinct verbatim descriptions / {len(cat)} codes.', flush=True)
    proto = model.encode(descriptions, normalize_embeddings=True,
                         show_progress_bar=False, batch_size=64, convert_to_numpy=True)
    lookup = {text: i for i, text in enumerate(descriptions)}
    code_vectors = np.asarray([proto[lookup[text]] for text in cat.description])
    domain_vectors = model.encode(domain.prototype_text.tolist(), normalize_embeddings=True,
                                 show_progress_bar=False, batch_size=64, convert_to_numpy=True)
    scoring = semantic.load_t51_scoring()
    domain_maxima, domain_ties = segment_winners(vectors, domain_vectors, scoring)
    domain_labels = []
    for unit in cache['units']:
        score, index, _ = unit_winner(unit['segment_indices'], domain_maxima, domain_ties)
        domain_labels.append((score, index, score is not None and score >= SETTINGS['presence_threshold']))
    result = []
    for space in ('profile_scoped', 'catalogue_wide'):
        subset = cat[cat.profile_scoped] if space == 'profile_scoped' else cat
        subset = subset.reset_index(drop=True)
        positions = [i for i, row in cat.iterrows() if space == 'catalogue_wide' or row.profile_scoped]
        maxima, tied = segment_winners(vectors, code_vectors[positions], scoring)
        print(f'{target}: {space} scoring complete ({len(subset)} codes).', flush=True)
        for unit, (domain_score, domain_idx, has_domain) in zip(cache['units'], domain_labels):
            score, index, tie_count = unit_winner(unit['segment_indices'], maxima, tied)
            assigned = score is not None and score >= SETTINGS['catalogue_threshold']
            best = subset.iloc[index] if index >= 0 else None
            source = domain.iloc[domain_idx].source if domain_idx >= 0 else ''
            row = {**META, **{k:v for k,v in unit.items() if k not in ('segment_indices', 'residual_segments')},
                   'target': target, 'class_space': space, 'profile': 'PMMUWW' if space=='profile_scoped' else '',
                   'profile_application': ('structurally_supported_turbine_profile'
                                           if space=='profile_scoped' and unit['structural_profile_scope']=='structural_PMMUWW'
                                           else 'counterfactual_PMMUWW_reference_not_asset_profile'
                                           if space=='profile_scoped' else 'catalogue_wide_reference_not_asset_mapping'),
                   'has_normalized_text': bool(unit['segment_indices']),
                   'best_score': score, 'assigned': assigned,
                   'assigned_catalogue_key': best.catalogue_key if assigned else '',
                   'assigned_group': best.code_group if assigned else '',
                   'assigned_code': best.code if assigned else '',
                   'nearest_code_key_diagnostic_only': best.catalogue_key if best is not None else '',
                   'max_score_tie_count': tie_count,
                   'assignment_ambiguous_tie': assigned and tie_count>1,
                   'domain_present': has_domain, 'domain_best_score': domain_score,
                   'domain_best_prototype': domain.iloc[domain_idx].prototype_id if has_domain else '',
                   'domain_best_source': source if has_domain else '',
                   'noncoverage_partition': partition(assigned, has_domain),
                   'fallback_unspecified_code': bool(assigned and space=='profile_scoped' and
                                                     best.code in ('OTH','NOTH'))}
            result.append(row)
    frame = pd.DataFrame(result)
    assert len(frame) == 10900*2
    assert not frame.duplicated(['unit_key_hash','target','class_space']).any()
    # The narrow prototype space is a literal subset of the wide one.
    pivot = frame.pivot(index='unit_key_hash', columns='class_space', values='assigned')
    assert not (pivot.profile_scoped & ~pivot.catalogue_wide).any()
    write_csv(output, frame)
    write_json(OUT/f'g20j_{target.lower()}_run_manifest.json', {
        'completed_at_utc': datetime.now(timezone.utc).isoformat(),
        'freeze_sha256': sha(OUT/'g20j_freeze_manifest.json'),
        'score_file_sha256': sha(output), 'model_revision': prepared_manifest['model_revision'],
        'no_training': True, 'denominator_changed': False})
    verify_freeze()
    print(frame.groupby(['path_bucket','class_space']).agg(n=('assigned','size'),
          assigned=('assigned','sum'), domain=('domain_present','sum')).to_string(), flush=True)


def residual_concepts(units: list[dict], cache: dict, target: str, path: str, space: str,
                      model) -> tuple[list[dict], dict]:
    terms = defaultdict(set)
    for unit in units:
        per_unit = set()
        for text in unit['residual_segments']:
            per_unit.update(extraction.ngrams(text.split()))
        for term in per_unit:
            parts = term.split()
            if (filtering.has_valid_shape(term,len(parts)) and not filtering.is_generic_only(term)
                    and not set(parts)&filtering.OPERATIONAL_ENTITY_TOKENS
                    and not restricted_match(term)):
                terms[term].add(unit['unit_key_hash'])
    floor = SETTINGS['residual_frequency_floors'][path]
    kept = sorted(term for term, keys in terms.items() if len(keys)>=floor)
    diagnostic = {'target':target, 'path_bucket':path, 'class_space':space,
                  'residual_units':len(units), 'frequency_floor':floor,
                  'pre_frequency_terms':len(terms), 'retained_terms':len(kept),
                  'concept_count':0, 'grouped_terms':0, 'unresolved_terms':len(kept),
                  'units_with_grouped_concept':0}
    if len(kept)<2:
        return [],diagnostic
    vectors = np.asarray(model.encode(kept, normalize_embeddings=True, batch_size=128,
                                     show_progress_bar=False, convert_to_numpy=True))
    k = min(256,max(1,round(math.sqrt(len(kept)))))
    clusters = MiniBatchKMeans(n_clusters=k,random_state=20260921,n_init=3,
                              batch_size=2048).fit(vectors)
    centers = clusters.cluster_centers_.astype(np.float32)
    norms = np.linalg.norm(centers,axis=1,keepdims=True)
    centers /= np.maximum(norms,1e-12)
    similarity = np.sum(vectors*centers[clusters.labels_],axis=1)
    concepts,covered = [],set()
    for label in range(k):
        positions=np.flatnonzero((clusters.labels_==label)&(similarity>=0.50))
        if len(positions)<2:
            continue
        scores={int(i):float(similarity[i])+0.015*np.log1p(len(terms[kept[i]]))-
                0.02*(len(kept[i].split())-1) for i in positions}
        canonical=kept[sorted(scores,key=lambda i:(-scores[i],kept[i]))[0]]
        membership=set().union(*(terms[kept[i]] for i in positions))
        covered.update(membership)
        signature='|'.join(kept[i] for i in sorted(positions))
        cid=extraction.prefixed_hash('G20J-RESIDUAL',f'{target}|{path}|{space}|{signature}',16)
        concepts.append({**META,'target':target,'path_bucket':path,'class_space':space,
                         'concept_id':cid,'canonical_label':canonical,
                         'surface_variants':len(positions),'unit_count':len(membership),
                         'n_residual_units':len(units),'share_of_residual':len(membership)/len(units),
                         'above_5pct':len(membership)/len(units)>0.05,
                         'grouping_method':SETTINGS['residual_grouping'],'selected_k':k,
                         'construction_method':'derived_from_eligible_masked_residual_inspection_algorithm',
                         'target_assignment':'context_from_presence_test_not_confirmed_term_semantics',
                         'reusable_for_training':False})
    concepts.sort(key=lambda r:(-r['unit_count'],r['canonical_label']))
    for rank,row in enumerate(concepts,1):
        row['rank']=rank;row['top_20']=rank<=20
    diagnostic.update(concept_count=len(concepts),grouped_terms=sum(r['surface_variants'] for r in concepts),
                      unresolved_terms=len(kept)-sum(r['surface_variants'] for r in concepts),
                      units_with_grouped_concept=len(covered))
    return concepts,diagnostic


def report() -> None:
    frozen=verify_freeze()
    if (OUT/'g20j_catalogue_coverage_sanitized.csv').exists():
        raise FileExistsError('Report already exists')
    frames=[]
    for target in TYPES:
        score=OUT/f'g20j_{target.lower()}_unit_scores_sanitized.csv'
        run=json.loads((OUT/f'g20j_{target.lower()}_run_manifest.json').read_text())
        assert sha(score)==run['score_file_sha256']
        assert run['freeze_sha256']==sha(OUT/'g20j_freeze_manifest.json')
        frames.append(pd.read_csv(score).fillna(''))
    frame=pd.concat(frames,ignore_index=True)
    coverage,partitions,counts,contrast=[],[],[],[]
    old=pd.read_csv(OLD).fillna('')
    for (target,path,space),group in frame.groupby(['target','path_bucket','class_space'],sort=True):
        frequencies=group[group.assigned].assigned_catalogue_key.value_counts()
        top_count=int(frequencies.iloc[0]) if len(frequencies) else 0
        n,assigned=len(group),int(group.assigned.sum())
        partition_counts=group.noncoverage_partition.value_counts()
        no_code=int(partition_counts.get('no_catalogue_code',0))
        no_anchor=int(partition_counts.get('no_anchor_at_all',0))
        domain=int(group.domain_present.sum())
        assert assigned+no_code+no_anchor==n
        share=top_count/assigned if assigned else None
        base={**META,'universe':lexical.ELIGIBLE,'target':target,'path_bucket':path,
              'class_space':space,'n':n,'profile_scope':'PMMUWW_common_reference_not_all_component_profiles',
              'comparison_status':'provisional_inherited_B2_source_identity' if path=='B2_WORKBOOKS'
              else 'descriptive_not_independent_evaluation'}
        coverage.append({**base,'units_evaluated':n,'assigned':assigned,'abstained':n-assigned,
                         'coverage_pct':100*assigned/n,'domain_present_units':domain,
                         'no_applicable_units':no_code,'no_applicable_rate':no_code/domain if domain else None,
                         'no_applicable_rate_denominator':'domain_anchored_units',
                         'no_catalogue_code_rate_of_universe':no_code/n,'no_anchor_at_all':no_anchor,
                         'top_code_key':frequencies.index[0] if len(frequencies) else '',
                         'top_code_share':share,'top_code_above_30pct':bool(share is not None and share>0.30),
                         'distinct_assigned_codes':len(frequencies),
                         'assigned_ambiguous_ties':int(group.assignment_ambiguous_tie.sum()),
                         'profile_fallback_unspecified_assignments':int(group.fallback_unspecified_code.sum()),
                         'structural_PMMUWW_units':int(group.structural_profile_scope.eq('structural_PMMUWW').sum()),
                         'catalogue_without_domain_support':int(partition_counts.get('catalogue_only',0))})
        for name in ('catalogue_and_domain','catalogue_only','no_catalogue_code','no_anchor_at_all'):
            number=int(partition_counts.get(name,0))
            partitions.append({**base,'partition':name,'units':number,'fraction_of_universe':number/n,
                               'interpretation':'candidate_configuration_gap_or_detector_miss'
                               if name=='no_catalogue_code' else 'method_defined_partition_not_ground_truth'})
        for key,number in frequencies.items():
            counts.append({**base,'catalogue_key':key,'assigned_units':int(number),
                           'share_of_assigned':int(number)/assigned,
                           'assignment_policy':SETTINGS['tie_policy']})
        previous=old[old.target.eq(target)&old.path_bucket.eq(path)&old.construction_eligible]
        assert set(previous.unit_key_hash)==set(group.unit_key_hash)
        old_n=int(previous.semantic_external_only.sum())
        contrast.append({**base,'previous_semantic_external_units':old_n,'catalogue_measured_units':assigned,
                         'descriptive_delta':assigned-old_n,
                         'detector_changed':False,'class_space_changed':True,
                         'presence_instrument_changed':True,
                         'delta_interpretation':'descriptive_not_improvement_or_causal_detector_effect'})
    write_csv(OUT/'g20j_catalogue_coverage_sanitized.csv',pd.DataFrame(coverage))
    partition_frame=pd.DataFrame(partitions)
    write_csv(OUT/'g20j_noncoverage_partition_sanitized.csv',partition_frame)
    write_csv(OUT/'g20j_no_applicable_report_sanitized.csv',partition_frame[
        partition_frame.partition.isin(['no_catalogue_code','no_anchor_at_all'])])
    write_csv(OUT/'g20j_assigned_per_code_sanitized.csv',pd.DataFrame(counts))
    write_csv(OUT/'g20j_wmep_contrast_sanitized.csv',pd.DataFrame(contrast))
    # Same units in both spaces; report known structural PMMUWW separately from counterfactual scope.
    strata=[]
    for keys,group in frame.groupby(['target','path_bucket','class_space','structural_profile_scope']):
        target,path,space,scope=keys
        strata.append({**META,'target':target,'path_bucket':path,'class_space':space,
                       'structural_profile_scope':scope,'n':len(group),
                       'assigned':int(group.assigned.sum()),'coverage_pct':100*group.assigned.mean(),
                       'component_profile_present_units':int(group.component_profile_present.sum()),
                       'component_profile_PMMUWW_units':int(group.component_profile_is_PMMUWW.sum())})
    write_csv(OUT/'g20j_profile_applicability_sanitized.csv',pd.DataFrame(strata))
    prepared=json.loads((PRIVATE/'g20j_prepared_corpus_internal.json').read_text())
    lookup={u['unit_key_hash']:u for u in prepared['units']}
    model=SentenceTransformer(semantic.MODEL_NAME,local_files_only=True)
    residuals,diagnostics=[],[]
    for keys,group in frame.groupby(['target','path_bucket','class_space'],sort=True):
        target,path,space=keys
        keys_of_gap=set(group[group.noncoverage_partition.eq('no_catalogue_code')].unit_key_hash)
        units=[lookup[k] for k in sorted(keys_of_gap)]
        print(f'Residual {target}/{path}/{space}: {len(units)} units',flush=True)
        concepts,diagnostic=residual_concepts(units,prepared,target,path,space,model)
        residuals.extend(concepts);diagnostics.append({**META,**diagnostic})
    columns=[*META,'target','path_bucket','class_space','concept_id','canonical_label','surface_variants',
             'unit_count','n_residual_units','share_of_residual','above_5pct','grouping_method','selected_k',
             'construction_method','target_assignment','reusable_for_training','rank','top_20']
    residual=pd.DataFrame(residuals,columns=columns)
    assert not residual.canonical_label.map(restricted_match).any()
    write_csv(OUT/'g20j_residual_concepts_sanitized.csv',residual)
    write_csv(OUT/'g20j_residual_top20_sanitized.csv',residual[residual.top_20.astype(bool)])
    write_csv(OUT/'g20j_residual_grouping_audit_sanitized.csv',pd.DataFrame(diagnostics))
    lines=['# G2.0j - Catalogue code coverage and residual characterization','',
           'Report only: no training, mapping to production, candidate promotion or F6 change.',
           'All results are uncalibrated semantic candidates, not verified code assignments.',
           'Catalogue and presence thresholds 0.50 were frozen before observing this run.',
           'They are inherited historical values, not calibrated on these new class spaces.',
           'Unit text uses semantic_normalisation_v2 after G2.0b masking; prototype code',
           'descriptions are verbatim. All thirteen source leakage rows are checked masked.', '',
           '## Universe and class-space controls','',
           'B1 eligible 9,263; Path A 159; B2 1,478. Full-corpus exclusions are separately',
           'registered. No unit counts or residuals are aggregated across paths.',
           'B2 preserves its inherited event universe and remains provisional because its',
           'source identity does not reconcile with historical F6; no silent repair was made.',
           'Symptom S: 1 PMMUWW group -> 6 codes; catalogue-wide 4,171 group-code pairs.',
           'Cause 5: 1 PMMUWW group -> 13 codes; catalogue-wide 6,232 group-code pairs.',
           'Both class spaces score the SAME eligible units. PMMUWW for orders without',
           'that structural profile is counterfactual, not a fabricated asset assignment.',
           'The 9,151 structural PMMUWW orders overlap the 3,934 component-profile orders.',
           'Those components have 30 profiles, only 50 PMMUWW; their code spaces are not',
           'all PMMUWW. Their text-derived dependency is retained and not independently evaluated.', '',
           '## Coverage','',
           '| Target | Path | Space | n | Assigned | Coverage | Domain | Gap | No anchor | Top share |',
           '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for row in coverage:
        top='undefined' if row['top_code_share'] is None else f"{row['top_code_share']:.2%}"
        lines.append(f"| {row['target']} | {row['path_bucket']} | {row['class_space']} | "
                     f"{row['n']} | {row['assigned']} | {row['coverage_pct']:.2f}% | "
                     f"{row['domain_present_units']} | {row['no_applicable_units']} | "
                     f"{row['no_anchor_at_all']} | {top} |")
    lines.extend(['','## Presence and gap interpretation','',
                  'Cause presence uses exactly nine WMEP causes. Symptom uses the single',
                  'frozen ZEUS detection_symptom container definition as a presence-test',
                  'prototype, plus eight WMEP effects as operational-consequence references.',
                  'The ZEUS container is not represented as a developed lexicon. Both are',
                  'imperfect, explicit presence tests and cannot prove subject matter.',
                  'no_catalogue_code = domain anchored AND no catalogue score >= threshold.',
                  'no_anchor_at_all = neither detector anchors; NOT proof of no target signal.',
                  'no_applicable_rate denominator is domain-anchored units; the separate',
                  'no_catalogue_code_rate_of_universe uses all evaluated units.',
                  'A gap can arise from catalogue expressiveness, profile restrictions or',
                  'detector/threshold limitations; this run alone does not distinguish them.',
                  'Catalogue-only matches are reported separately: matching a code does not',
                  'establish target presence or true classification.', '',
                  '## Assignment ambiguity and fallback descriptions','',
                  'Catalogue keys are type|group|code. Ties within 1e-6 are explicitly counted;',
                  'the displayed assignment uses stable lexicographic tie-breaking, not truth.',
                  'Identical descriptions across groups can inflate top-code concentration.',
                  'PMMUWW OTH/NOTH are unspecified fallback codes and separately counted;',
                  'they do not demonstrate that a specific symptom/cause was expressed.', '',
                  '## Residual characterization','',
                  'Only eligible masked gap texts generate 1-3 grams. G2.0c path frequency',
                  'floors and neutral shape/generic/safety filters are reused. Semantic grouping',
                  'uses normalized MiniLM vectors and MiniBatchKMeans with frozen sqrt(n)',
                  'k rule capped at 256, member cosine >=0.50 and at least two members.',
                  'Canonical labels are centroid/frequency summaries, not analyst adjudication.',
                  'Concept frequency deduplicates physical units across all member ngrams.',
                  'Concepts can overlap; their unit counts must not be summed. Empty residuals',
                  'and small ungrouped sets are explicitly registered, not silently omitted.',
                  'Top 20 and >5% concentration are separate files; concepts are diagnostic',
                  'and never promoted into vocabulary, training or evaluation from this run.', '',
                  '## Historical contrast and plan corrections','',
                  'The 104 Symptom / 289 Cause B1 historical semantic values are contrasted',
                  'on identical eligible unit keys. The earlier Cause instrument included',
                  'NREL as well as WMEP; the old Symptom instrument had eight WMEP effects',
                  'and no developed ZEUS symptom lexicon. Deltas are descriptive, not improvement.',
                  'A literal lexical-to-semantic contrast would change detectors; these two',
                  'historical values specifically come from the semantic G2.0d2 scores.',
                  'The plan Activity example 1/375 is stale: corrected v2.1 has 6/375 responses,',
                  'none in the 75 shared units. Those annotations were not used for this run.',
                  'No independent precision, recall, F1, final-heldout or SAP correctness claim.', ''])
    with (OUT/'g20j_memo.md').open('x',encoding='utf-8') as handle:
        handle.write('\n'.join(lines))
    verify_freeze()
    write_json(OUT/'g20j_run_manifest.json',{
        'completed_at_utc':datetime.now(timezone.utc).isoformat(),
        'freeze_sha256':sha(OUT/'g20j_freeze_manifest.json'),
        'protected_sources_unchanged':True,'settings':SETTINGS,
        'outputs_sha256':{p.name:sha(p) for p in OUT.iterdir() if p.is_file()},
        'status':'report_complete_B2_provisional_no_independent_accuracy_claim'})
    print(pd.DataFrame(coverage)[['target','path_bucket','class_space','n','assigned',
                                'domain_present_units','no_applicable_units','top_code_share']].to_string(index=False))


if __name__=='__main__':
    import torch
    torch.set_num_threads(4)
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['freeze','prepare','measure','report'])
    parser.add_argument('--target',choices=list(TYPES))
    args=parser.parse_args()
    if args.phase=='freeze': freeze()
    elif args.phase=='prepare': prepare()
    elif args.phase=='measure':
        if not args.target:parser.error('--target is required for measure')
        measure(args.target)
    else: report()
