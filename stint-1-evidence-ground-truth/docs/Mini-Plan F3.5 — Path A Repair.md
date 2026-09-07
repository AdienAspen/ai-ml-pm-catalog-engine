# Mini-Plan `F3.5` — Path A Repair

**Reparación de F3 tras la caracterización de PDFs**
Inserción entre F3 y F4 · Estimado 3–4 días

---

## Por qué existe

La inspección manual de 2 PDFs reveló que el universo de F3 estaba mal caracterizado:

- El parseo estructural descartó el bloque **NOTES**, donde vive la semántica de mantención
- Los códigos `156` y `155` coinciden con categorías del panel `ASSET STATUS` — **serían códigos de estado, no de falla**
- Un mismo evento aparece repetido en snapshots diarios consecutivos (T9: `112d 20h`)

F3 corrió correctamente sobre el universo equivocado. Esta fase corrige el universo, no el método.

---

## T3.5.1 — Verificación de la hipótesis código-estado

**La tarea más barata y la de mayor impacto.**

- Extraer las categorías del panel `ASSET STATUS` de una muestra de PDFs: `Tripped`, `Stopped`, `Impacted`, `Repair`, `Maintenance`, `No Comm.`, `Online`, `Available`
- Cruzar los 79 fault-code keys contra el valor del campo `Event` asociado
- Clasificar cada token: `state_code` · `fault_code` · `undetermined`

**Salida esperada:** partición de los 79. Los `state_code` **salen del universo de Damage y Cause** — no describen falla.

**Entregable:** `f35_faultcode_state_partition.csv`

⚠️ Si una porción sustantiva resulta `state_code`, los 55/79 sin candidato de F3 quedan explicados y el resultado deja de leerse como fallo del matching.

---

## T3.5.2 — Re-parseo con Docling

**Objetivo:** recuperar NOTES sin volver al parser que traspuso columnas.

- Evaluar Docling sobre una muestra de 10 PDFs antes de correr los 394
- Verificar que preserva ambas capas: tabla `ASSETS OF CONCERN` + prosa `NOTES`
- Comparar la extracción estructural contra la del parser actual — no debe degradarse

**Campos nuevos a capturar:**
```
notes_text          prosa libre del bloque NOTES
asset_status_panel  conteos por categoría
planned_work        sección (vacía en la muestra, verificar)
site_roster         ⚠️ contiene PII — no versionar
```

**Entregable:** `pdf_docling_reparse_v1` + nota de comparación con el parseo anterior.

---

## T3.5.3 — Extracción semántica de NOTES

El bloque NOTES tiene estructura reconocible:

```
[contratista] - [turbina] [componente] [acción]

"CONTRACTOR_ENTITY_001- T48 Yaw Limit switch"
"CONTRACTOR_ENTITY_003- T9 blade repair"
"CONTRACTOR_ENTITY_002- T30 & T33 annual maintenance"
"WTG 26 PCH and accumulator"
```

- Extraer contratista, referencia de turbina, componente y acción
- **Resolver la referencia de turbina** (`T48` → asset 48) para unir con la tabla de concern
- Anclar componente y acción contra el `LEXICAL_LAYER v2` (359 conceptos)

**Nota importante:** las referencias de NOTES no siempre coinciden con los assets de la tabla. En la muestra de 2025, NOTES menciona T26 y la tabla lista 4, 45, 55. **Son fuentes complementarias, no redundantes.**

**Entregable:** `pdf_notes_extraction_v1` con procedencia por fila.

---

## T3.5.4 — Deduplicación de snapshots

**Objetivo:** establecer cuántos eventos reales hay detrás de las 602 filas.

- Agrupar por `asset + fault_code + ventana de duración`
- Un evento con duración creciente en fechas consecutivas es **un evento**, no N
- Producir dos conteos: `filas_snapshot` y `eventos_estimados`

**Regla:** el denominador de Path A usa `eventos_estimados`. Las filas snapshot quedan como observaciones del mismo evento.

**Entregable:** `pdf_event_deduplication_v1` + ambos conteos declarados.

---

## T3.5.5 — Re-corrida del crosswalk

Con universo corregido:

- Solo los tokens clasificados `fault_code` entran al matching contra Damage/Cause
- Los `state_code` se enrutan a **Activity Type**, donde sí tienen sentido semántico
- NOTES aporta señal nueva para **Object Part** y **Activity**

**Entregable:** `ge_fault_code_crosswalk_v2`, reemplaza al de F3.

---

## Criterio de cierre

- Los 79 tokens clasificados por naturaleza, con evidencia
- NOTES extraído y anclado, con procedencia
- Ambos conteos de Path A declarados: filas vs eventos
- Crosswalk v2 emitido, con `expert_inference` y tier por fila
- PII del site roster identificada y excluida de artefactos versionables

**Sigue sin promoverse nada a measurement-ready.**

---

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Docling degrada la extracción estructural | evaluar sobre 10 antes de los 394 |
| NOTES no une con la tabla por falta de clave | tratarlas como fuentes separadas, no forzar join |
| Deduplicación colapsa eventos legítimos distintos | ventana de duración, no solo asset+code |
| PII se filtra a artefactos versionables | exclusión explícita desde el parseo |

---
