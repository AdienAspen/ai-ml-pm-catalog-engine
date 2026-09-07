# Plan Técnico v2 — STINT_1
## Evidence Reconstruction & Surrogate Ground Truth

**FSA BRIDGE / AI-ML Workstream**
*Actualizado tras el cierre de `STINT_1.1-reference-layer`*

---

## Framing

> **STINT_0** midió el problema de evidencia. **STINT_1.1** construyó la capa de referencia.
> **STINT_1 reconstruye evidencia evaluable por target, sin inventarla.**

---

## Objetivo

Producir, para cada uno de los 7 targets, un conjunto de evidencia evaluable con procedencia trazable, que habilite prototipado de modelos en STINT_2.

**No es objetivo:** entrenar modelos, estimar accuracy, ni cerrar el contrato `/classify`.

---

## Qué cambió desde la versión anterior

| Área | Antes | Ahora |
|---|---|---|
| Reference layer | no existía | `reference-layer-v1` congelado |
| G06 / FLOC | vía KKS + research | **KKS cerrado.** Va por matching léxico contra IH06 |
| G03 / Fault codes OEM_ENTITY_001 | investigación pendiente | research agotado. **No hay catálogo público** |
| G05 / MAT | bloqueado sin fuente | ZEUS aporta `maintenance_type` |
| G07 / Symptom | sin marco | `≈ Failure Effect tipo 6` (hipótesis) + 289 términos léxicos detectados |
| G04 | pendiente | cerrado por proxy documentado |
| G08 | abierto | cerrado — `0 parser issues` |
| Benchmark | inexistente | 0,75–0,85 F1 publicado en dominio |

---

## Principios de gobernanza

- **Procedencia granular por fila** — `evidence_type` y `tier` en ejes independientes
- **Canonical congelado** — `v1.8-baseline-frozen`. Divergencia al `canonical-delta-log`, nunca sobrescritura
- **Denominadores por target** — y por site/contractor/estrato donde aplique. Jamás global
- **Cero claims de performance** hasta que exista denominador defendible
- **`UNKNOWN` siempre permitido** — mejor vacío que inventado
- **Nunca inferir Causa desde Daño**

---

## Deudas heredadas de STINT_1.1

Se resuelven dentro de STINT_1, con dueño asignado:

| Deuda | Qué falta | Fase |
|---|---|---|
| `LEXICAL_LAYER` provisional | filtrado por frecuencia + agrupamiento por dominio | F1 |
| `SEMANTIC_NORMALISATION` parcial | poblar WMEP y NREL GRD en scaffold ZEUS | F1 |
| `DELTA-0002` | decidir clave de identidad para denominadores | F0 |
| `DELTA-0003` | vincular campo de texto primario por target | F0 |
| `DELTA-0009` | semantic split Activity / Cause / Activity Type | F2 |

---

## Fase 0 — Consolidación y precondiciones *(inmediata)*

**Objetivo:** dejar el Feasibility Report auditable y resolver las dos deltas que bloquean denominadores.

- Incorporar la reconciliación de denominadores (838+72=910; 147 vs 157)
- Corregir estado de G08 — cerrado, `0 issues`
- Marcar en el matrix que Cause / Activity / Activity Type comparten expansión multi-target
- **Resolver DELTA-0002** — declarar `physical_record_id` para conteos de denominador y `stint1_record_id` para trazabilidad record-field. Sin esto no hay denominador defendible
- **Resolver DELTA-0003** — declarar campo de texto primario por target. Sin esto no hay evidencia medible

**Entregable:** Feasibility Report Draft 2 + `canonical-constraints.md` actualizado.

---

## Fase 1 — Consolidación léxica (revisada)

Objetivo: convertir el diccionario provisional en capa operativa.

Paso previo obligatorio — dimensionar antes de decidir

El conteo del T8c reportó filas por longitud, no términos distintos. Antes de cualquier filtrado:

contar distinct observed_term_key por longitud en palabras

Los 3.081 unigramas son un conteo de filas contextuales y pueden estar inflados por duplicados. El vocabulario real puede ser sustancialmente menor.

Sin este conteo, cualquier dimensionamiento es a ciegas.

Trabajo
Filtrado por frecuencia — descartar n-gramas de aparición única sin señal de dominio
Agrupamiento por concepto — colapsar variantes a canonical_concept con concept_id estable
Ampliar muestreo más allá de los 600 registros, manteniendo estratificación
Poblar el scaffold ZEUS con vocabulario WMEP y NREL GRD, evidence_type por fila
Preservar source_text_field por término


Sobre el rango 300–800

Es una heurística de timebox, no un criterio de éxito.

El número correcto emerge del dominio. Forzar 800 fusiona conceptos distintos; forzar 300 elimina señal útil.

Cómo usarlo: si el resultado cae muy fuera del rango, es señal para revisar el método de agrupamiento — no para ajustar el resultado hacia el número.

Entregable: lexical_layer_v2 + SEMANTIC_NORMALISATION completo + conteo de términos distintos por longitud.

---

## Fase 2 — Semantic Reconciliation *(G02 + DELTA-0009)*

**Objetivo:** convertir las 802 filas `unknown` en mapa real de evidencia, y separar los targets que comparten señal.

- Agrupar por patrón, no por fila — se esperan 15–30 grupos
- Clasificar: `matched_vocabulary`, `unrelated_cooccurrence`, `out_of_scope`, `pending`
- Validación humana por grupo
- **Semantic split de las 36 estructuras multi-target** — determinar si Activity, Cause y Activity Type tienen evidencia propia o comparten una sola señal expandida

**Precondición crítica:** sin este split, ninguno de los tres puede promoverse a nivel target.

**Entregable:** `unknown_reconciliation_report` + `multitarget_split_report`.

---

## Fase 3 — Path A: Fault codes OEM_ENTITY_001 *(G03)*

**Objetivo:** resolver los 79 tokens de fault code sobre 602 registros PDF.

**El research está agotado.** No existe catálogo público OEM_ENTITY_001 ni crosswalk OEM→SAP. La cadena de trabajo es interna:

```
fault code → contexto de aparición → concepto de mantención
→ candidato SAP (B/C/5/A) + provenance + confidence
```

**Regla adoptada:** no forzar equivalencia 1:1. Si un fault code no mapea a un solo código SAP, eso es hallazgo válido.

**Recursos disponibles:** scaffold ZEUS, vocabulario WMEP, diccionarios Malyi por sistema.

**Entregable:** `ge_fault_code_crosswalk` con `evidence_type: expert_inference`, tier según convergencia.

---

## Fase 4 — Path B: XLSX / Daily Maintenance Reports

**El frente más grande. Weak supervision es la herramienta principal.**

Reconstrucción semántica desde:
```
narrative + component + action + site + turbine
+ metadata + catálogos + reglas de negocio
```

Ejecutar **target por target**, emitiendo silver labels cuando múltiples señales convergen.

### Estratificación — confirmada asimétrica *(T8a)*

- **`CONTRACTOR_PATH_001`** — `activityType` explícito, cobertura 100%. Estratificar directo
- **PDFs** — `event` estructural. Estrato separado, **nunca planned/reactive**
- **No mezclar estratos en un mismo denominador**

Si la derivación planned/reactive requiere inferencia, marcarla `expert_inference`.

### FLOC leaf *(G06)* — dentro de esta fase

**KKS cerrado definitivamente.** No hay designaciones heredadas utilizables. La vía es matching léxico contra los nodos reales del IH06.

**Constraints confirmados:**
- Jerarquía real: 88.441 filas, 9 sitios, profundidad 4–5
- **Cero filas a profundidad ≥ 6** — el leaf disponible es Component/Maintainable Item, no Part
- Profundidad **no homogénea entre sitios** — medir por planta, no globalmente
- Un Object Part más granular que el leaf FLOC **no tiene nodo donde aterrizar**

**Nota:** el crosswalk IH06 ↔ IEC es documentación de cobertura, no requisito del pipeline. Prioridad baja.

### Activity Type / MAT *(G05)*

- ZEUS `maintenance_type` como andamiaje conceptual
- `activityType` de `CONTRACTOR_PATH_001` como señal directa donde exista
- Sin fuente OEM_ENTITY_001 controlada: reconstrucción marcada `expert_inference`

**Entregable:** silver labels por target, con procedencia y estrato.

---

## Fase 5 — Symptom *(G07)*

**El más difícil. Al final, con deliberación.**

**Estado actualizado:** T8 detectó **289 términos léxicos de Symptom** en el corpus. No son labels ni códigos, pero confirman que existe vocabulario sintomático en el texto. Eso habilita la Ruta A.

**Rutas, en orden de preferencia:**

- **A — Derivación inversa + validación cruzada** ⭐ *(estrategia acordada)*
  - Inferir Symptom plausible desde Damage + Object Part + Activity
  - **Cruzar contra referente:** categorías `detection symptom` de ZEUS pobladas con efectos WMEP
  - **Segundo filtro:** el catálogo Wind S del cliente. Lo que no exista ahí, se descarta
  - **El cruce filtra, nunca confirma.** Sigue siendo `expert_inference`, tier máximo `silver-medium`
- **B — Synthetic fundado** sobre catálogo Wind S real
- **C — Expert inference supervisada**, documentada como tal
- **D — Aceptar el hallazgo** — declarar no derivable. **Resultado de feasibility válido**

**Precondiciones:** requiere B, C y A resueltos primero. Debe correr **sobre el subconjunto reactivo**, no sobre el corpus completo.

⚠️ **Prohibido:** rellenar con valor genérico para que el canonical no quede vacío. Eso convierte una brecha honesta en dato falso no auditable.

⚠️ **`Symptom ≈ Failure Effect tipo 6` sigue siendo `hypothesis`.** No cristalizar sin evidencia de configuración FSA.

---

## Fase 6 — Denominadores *(reescrita)*

**No es una tarea — es la consecuencia de las anteriores.**

### La distinción que gobierna toda la fase

F3, F4 y F5 producen mayoritariamente `expert_inference`. Excluirlo de forma absoluta dejaría esos targets sin ninguna forma de evaluación.

**Por eso se emiten dos denominadores separados, nunca fusionados:**

```
┌─────────────────────────────────────────────────────┐
│  DENOMINADOR CONTRACTUAL                            │
├─────────────────────────────────────────────────────┤
│  Admite:   real_observed_label                      │
│            validated_mapping                        │
│            tier = gold                              │
│            status = resolved                        │
│  Excluye:  expert_inference — sin excepción         │
│            reference_evidence                       │
│            external_corroboration                   │
│                                                     │
│  Es el único que respondería al 95% del contrato.   │
│  Expectativa realista: cero o cercano a cero en     │
│  varios targets. Eso es un resultado válido.        │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  DENOMINADOR PROXY POC                              │
├─────────────────────────────────────────────────────┤
│  Admite:   todo lo del contractual                  │
│            silver-high                              │
│            silver-medium cualificado                │
│            expert_inference con provenance completa │
│                                                     │
│  Se reporta SIEMPRE como proxy evaluation set.      │
│  NUNCA como verified production accuracy.           │
│  Es el que permite evaluar el POC.                  │
└─────────────────────────────────────────────────────┘
```

### Requisitos para admitir `expert_inference` en el proxy

Una entrada `expert_inference` solo entra al denominador proxy si cumple **todas**:

- `concept_id` estable y resoluble
- Regla de derivación documentada y reproducible
- Fuente de la que deriva, declarada
- Destino canónico válido en `canonical-constraints.md`
- Tier asignado con criterio explícito
- `label_generation_method` declarado
- `evaluation_independence` declarado

**Si falta cualquiera, va a `unresolved`.**

### Unidad de conteo

`N` cuenta registros físicos únicos por target, no filas de evidencia. Varias evidencias convergentes sobre el mismo registro y target cuentan una vez.

`stint1_record_id` puede identificar unidades `record-field` para auditoría, pero F6 debe deduplicar por `physical_record_id x target`.

### Independencia de evaluación

Todo label proxy debe declarar `label_generation_method` y `evaluation_independence`.

Un held-out proxy evaluation set solo puede usar registros `independent`, o debe excluir explícitamente el rule set que produjo las etiquetas del predictor evaluado. Si el mismo rule set genera y predice la etiqueta, la evaluación es circular y no puede reportarse como accuracy.

### Estructura de reporte

```
target × denominator_type × evidence_type × tier
      × path × site × estrato → N registros evaluables
```

`denominator_type` es columna obligatoria. **Un reporte que no la traiga es inválido.**

### Reglas que no cambian

- Nunca un denominador global
- Estratos no se mezclan — `event_structural` jamás con `planned/reactive`
- Un denominador de cero es resultado válido y esperado
- La cifra contractual y la proxy **nunca se presentan juntas sin etiqueta**

**Entregable:** `evidence_denominator_matrix` con ambos denominadores separados por target.

---

## Actualización al criterio de cierre

Para cada uno de los 7 targets debe existir:

- **Denominador contractual declarado** — aunque sea cero
- **Denominador proxy declarado** — aunque sea cero
- Tier y `evidence_type` que respaldan cada uno
- Procedencia documentada por registro
- Recomendación de método justificada por la evidencia real
- Segmentación declarada donde aplique

---

## Actualización al registro de riesgos

| Riesgo | Mitigación |
|---|---|
| Proxy se reporta como contractual | `denominator_type` obligatorio en todo output; verificación en F6 |
| `expert_inference` entra al proxy sin provenance | checklist de cinco requisitos, bloqueante |
| Evaluación circular sobre etiquetas generadas por reglas | `label_generation_method` y `evaluation_independence` obligatorios |
| Convergencia de evidencia infla denominadores | contar `N` por `physical_record_id x target`, no por filas de evidencia |
| Vocabulario dimensionado sobre conteo inflado | conteo de términos distintos antes de filtrar (F1) |
| Rango 300–800 tratado como meta | declarado explícitamente como heurística de timebox |
