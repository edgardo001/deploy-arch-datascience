# Archivo de Peticiones — 2026 Q4 (`P-001`…`P-003`)

> Archivo histórico del [registro vivo](prompt-log.md). Contiene las peticiones cerradas y estables, trasladadas
> **íntegras** cuando el registro superó las 180 líneas (protocolo §1.6). Nada se resume ni se reescribe: se mueve.
> Periodo: **2026-10-01** · Peticiones archivadas: **3** · Prompt inicial literal: [initial-prompt.md](initial-prompt.md).

## Reglas de este archivo

1. Solo entran peticiones con estado `verificada` y sin cambios pendientes.
2. El texto se copia **verbatim** desde el registro vivo, incluidos enlaces relativos.
3. Si una petición archivada se reabre, se le asigna una petición nueva `P-00N` en el registro vivo, no se edita aquí.
4. Los identificadores no se reutilizan nunca.

## `P-001` — Prompt inicial: entorno DataLab productivo

> Transcripción literal completa en [initial-prompt.md](initial-prompt.md) §1.

| Campo | Detalle |
|---|---|
| Interpretación | Construir un entorno local reproducible (OLTP → Lakehouse → DW → ML/BI) documentado, con equipo de 7 agentes, memoria persistente y reglas estrictas de modularidad. |
| Entregables | [README.md](../../README.md), [AGENTS.md](../../AGENTS.md), [MEMORY.md](../../MEMORY.md) y 7 módulos en `docs/` (5 exigidos + `memory-persistence.md` y `runbook.md` por la regla de 180 líneas). |
| Extras asumidos | Stack ejecutable ([docker-compose.yml](../../docker-compose.yml), [.env.example](../../.env.example), [.gitignore](../../.gitignore)) y andamiaje `infra/` para que el arranque no falle por rutas ausentes. |
| Evidencia | 10/10 `.md` ≤ 174 líneas al cierre · 0 enlaces rotos · índice ≡ archivos reales · 4 diagramas Mermaid · YAML/JSON sin errores · 9/9 `.py` con sintaxis válida. |
| Desviación declarada | La entrega se hizo como **archivos reales** en el repositorio en lugar de bloques de código en el chat (ver `P-002`). |
| Estado | ✅ Verificada; pendiente de ejecución real del stack (daemon Docker apagado). |

## `P-002` — Registro vivo del prompt y de las peticiones

> «documenta el prompt inicial y actualizalo con todas las peticiones nuevas que se vayan realizando»

| Campo | Detalle |
|---|---|
| Interpretación | Persistir el prompt inicial en un documento consultable y crear una bitácora que se amplíe con cada petición futura, con protocolo de actualización explícito. |
| Entregables | [initial-prompt.md](initial-prompt.md) (transcripción literal + requisitos `R-01`…`R-24` + criterios de aceptación) y el [registro vivo](prompt-log.md). |
| Archivos tocados | `docs/prompts/initial-prompt.md`, `docs/prompts/prompt-log.md`, índice del [README.md](../../README.md) §4, [AGENTS.md](../../AGENTS.md) §1.7, [MEMORY.md](../../MEMORY.md) §3 y [orchestration-rules.md](../agents/orchestration-rules.md) §6.7. |
| Evidencia | 12 documentos, ninguno > 176 líneas · 0 enlaces rotos · índice 12/12 sin huérfanos · YAML/JSON sin errores · 9/9 `.py` válidos. |
| Decisión de diseño | El prompt inicial se transcribe con valla de 4 *backticks* para no romper el ejemplo de `FORMATO DE ENTREGA` que contiene vallas de 3. |
| Estado | ✅ Verificada |

## `P-003` — Glosario de siglas, términos y servicios

> «es importante que documentes las siglas y sus significados, por que al ver "## 2. Mapa de servicios y puertos", no era cada elemento»

| Campo | Detalle |
|---|---|
| Interpretación | Faltaba un glosario: la tabla de servicios del README usaba OLTP, OLAP, ELT/ETL, DAG, S3, BI, *one-shot*… sin definir, y no explicaba qué es ni para qué sirve **cada elemento** del stack. |
| Entregables | [glossary.md](../glossary.md): 10 secciones, **más de 80 entradas** agrupadas por dominio, tabla «los servicios del stack, uno por uno» y convenciones de nomenclatura (`dt=`, `stg_`, `dim_`, `fct_`, `tag: critical`). |
| Archivos tocados | `docs/glossary.md` (nuevo), §2 y índice del [README.md](../../README.md), y fila de navegación en los 11 documentos restantes. |
| Evidencia | 13 documentos, ninguno > 178 líneas · 0 enlaces rotos · índice del README 13/13 sin huérfanos. |
| Decisión de diseño | El glosario documenta **el sentido que tiene cada sigla en este repositorio** cuando es ambigua en la industria (p. ej. `DAX` → se traduce a SQL certificado; `SK/BK` → `customer_sk`/`customer_id`). |
| Estado | ✅ Verificada |

## Navegación

| Documento | Contenido |
|---|---|
| [prompt-log.md](prompt-log.md) | Registro vivo: protocolo, índice completo y peticiones activas |
| [initial-prompt.md](initial-prompt.md) | Prompt inicial literal y requisitos `R-01`…`R-24` |
| [README.md](../../README.md) | Índice maestro del repositorio |
