# Fase 4 — Reescritura
## Path B · Reconstrucción de evidencia por familia de fuente

**FSA BRIDGE / AI-ML Workstream · STINT_1**
*Reemplaza la Fase 4 del plan técnico v2, tras F4.0 y F4.0b*

---

## Qué cambió

La versión anterior trataba Path B como una familia homogénea de "XLSX / Daily Maintenance Reports" y asumía weak supervision como herramienta principal para los siete targets.

**La caracterización reveló dos familias con naturalezas opuestas:**

```
CONTRACTOR_PATH_001    modelo relacional · 7 entidades · 33.660 registros
                       registros atómicos · joins al 93,6–100%
                       → buena parte se resuelve sin ML

OEM_ENTITY_001 EOD / POD           workbooks diarios de estado
                       misma naturaleza que Path A
                       → requiere deduplicación antes de extraer
```

**Consecuencia:** dos ramas, mismo objetivo, distinto método. Nunca un denominador común.

---

## Objetivo

Producir evidencia evaluable por target, con procedencia y estrato, para los dos paths de Path B.

**Principio rector confirmado por la caracterización:**

> El trabajo de ML no es clasificar todo. Es clasificar lo que no se puede resolver de otra forma.

---

## Rama B1 — `CONTRACTOR_PATH_001` · relacional

### Frontera determinístico / ML — establecida

| Target | Ruta | Método |
|---|---|---|
| **Activity Type / MAT** | campo directo `activityType` | join · **sale de ML** |
| **Object Part** | `consumption` → materiales | join + mapeo material→catálogo B |
| **Activity** | estructural + detalle textual | join + ML sobre residuo |
| **FLOC leaf** | joins internos + alineación SAP | join + matching contra IH06 |
| **Cause** | `reason` — semántica sin confirmar | texto → ML |
| **Damage** | sin campo dedicado | texto → ML |
| **Symptom** | sin campo pre-ejecución | ❌ no alcanzable |

### B1.1 — Cosecha determinística *(primero)*

- Extraer `activityType` → **MAT resuelto**, `evidence_type: real_observed_label`
- `consumption` → materiales por orden. Evaluar cobertura y viabilidad de mapeo a catálogo B por regla
- Joins internos para FLOC: `assets → sites`, y alineación contra la jerarquía IH06
- **Todo lo cosechado aquí no entra al pipeline de ML.** Es evidencia estructural

**Entregable:** `b1_deterministic_harvest` con tier y procedencia por target.

### B1.2 — Residuo textual *(solo lo que queda)*

Targets: **Cause**, **Damage**, y el detalle de **Activity** no cubierto por campo.

- Campo primario: `description_extended` (96,2% cobertura)
- Soporte: `reason` (100% cobertura, semántica no confirmada)
- Aplicar `LEXICAL_LAYER v2` — 359 conceptos, banda high únicamente
- Weak supervision con convergencia de señales

**Entregable:** `b1_silver_labels` por target, con `source_text_field` declarado.

### ⚠️ B1.3 — Pregunta abierta sobre `reason`

`reason` está poblado al 100% pero su semántica no está confirmada. En modelos de servicio de campo suele ser **motivo de la visita** —por qué se despachó al técnico— no causa raíz.

> **Si resulta ser eso, es más cercano a Symptom que a Cause** — y sería el único campo del corpus con información pre-ejecución.

**Verificar antes de enrutarlo definitivamente.** No promover mientras siga sin confirmar.

---

## Rama B2 — OEM_ENTITY_001 EOD / POD · snapshot

**Misma naturaleza que Path A. Mismo tratamiento.**

### B2.1 — Caracterización pendiente

`F4.0` muestreó `CONTRACTOR_PATH_002` y `SITE_PATH_002_SNAPSHOT` con caps bajos. Falta:

- Inventario de variantes de plantilla por familia
- Extracción espacial validada contra caso positivo conocido
- Localizar campos de prosa fuera del routing

**Aplicar el método de F3.5, que ya está probado.**

### B2.2 — Deduplicación

Los workbooks son de estado: una condición persiste en múltiples archivos diarios.

```
clave: site + asset + code + ventana(incident_start ± tolerancia)
incident_start_estimated = snapshot_date − duration
```

**Reportar siempre `snapshot_rows` y `estimated_events` por separado.**

### B2.3 — Extracción y weak supervision

- Separar códigos de estado de códigos de falla — namespace `asset_state`
- Extraer prosa técnica donde exista
- Anclar contra `LEXICAL_LAYER v2`

### ⚠️ B2.4 — Verificación EOD vs POD

```
POD  →  Plan of Day   ·  estado al inicio del turno
EOD  →  End of Day    ·  trabajo ejecutado
```

**Nadie ha comparado ambas familias.** Si los EOD registran ejecución, deberían tener mejor densidad de Activity y menor repetición.

**Y la pregunta crítica:** ¿algún EOD registra el reporte inicial del problema? Es el único lugar del corpus donde Symptom podría existir.

---

## FLOC leaf *(G06)* — transversal a ambas ramas

**KKS cerrado definitivamente.** Sin designaciones heredadas utilizables. La vía es matching contra los nodos reales del IH06.

**Constraints confirmados:**

- Jerarquía real: 88.441 filas · 9 sitios · profundidad 4–5
- **Cero filas a profundidad ≥ 6** — el leaf disponible es Component/Maintainable Item, no Part
- Profundidad **no homogénea entre sitios** — medir por planta, nunca globalmente
- Un Object Part más granular que el leaf FLOC **no tiene nodo donde aterrizar**

En B1, los joins internos pueden aportar ruta estructural parcial. En B2, es matching léxico puro.

**Nota:** el crosswalk IH06 ↔ IEC es documentación de cobertura, no requisito del pipeline. Prioridad baja.

---

## Activity Type / MAT *(G05)* — estado actualizado

```
B1   →  resuelto por campo directo. Sale de ML
B2   →  sin fuente OEM_ENTITY_001 controlada
        ZEUS maintenance_type como andamiaje
        reconstrucción marcada expert_inference
```

**G05 deja de estar bloqueado en la rama relacional.** Era el target más bloqueado del proyecto desde STINT_0.

---

## Estratificación — reglas

```
B1  →  activityType explícito, 100% cobertura → estratificar directo
B2  →  event_structural · NUNCA planned/reactive
Path A → event_structural
```

- **No mezclar estratos en un mismo denominador**
- Derivación planned/reactive por inferencia → `expert_inference`
- **B1 y B2 nunca comparten denominador.** Distribuciones distintas, naturalezas distintas

---

## Symptom — estado tras la caracterización

```
Path A        no registra síntoma observado
B1            sin campo pre-ejecución confirmado
B2            pendiente de verificar (B2.4)
```

**Dos de tres familias confirmadas sin fuente.** Si B2.4 confirma la tercera, Symptom pasa de *escaso* a **estructuralmente inalcanzable** — porque el corpus se compone de objetos tipo orden y reportes de estado, y ninguno registra el síntoma reportado.

**Eso es un hallazgo de feasibility válido, no un fallo.**

---

## Secuencia

| Paso | Rama | Depende de |
|---|---|---|
| B1.1 cosecha determinística | B1 | F4.0b ✅ |
| B1.3 verificar `reason` | B1 | — |
| B1.2 residuo textual | B1 | B1.1, B1.3 |
| B2.1 caracterización | B2 | — |
| B2.4 EOD vs POD | B2 | B2.1 |
| B2.2 deduplicación | B2 | B2.1 |
| B2.3 extracción | B2 | B2.2 |

**B1 y B2 son paralelizables.** B1.1 es la de mayor retorno inmediato: resuelve MAT y evalúa Object Part sin ML.

---

## Entregables

```
b1_deterministic_harvest      evidencia estructural
b1_silver_labels              Cause · Damage · Activity residual
b2_snapshot_dedup             snapshot_rows vs estimated_events
b2_silver_labels              por target, con estrato
floc_leaf_candidates          por sitio, nunca global
reason_semantics_verdict      resolución de B1.3
eod_pod_comparison            resolución de B2.4
```

---

## Criterio de cierre

Por target y por rama:

- Evidencia declarada con `evidence_type`, `tier`, `status`
- Ruta declarada: determinística, ML, o no alcanzable
- Estrato y `source_text_field` en toda fila
- Denominadores separados por rama, nunca agregados
- `UNKNOWN` permitido y esperado

**Declarar que un target no es alcanzable en una rama es resultado válido.**
