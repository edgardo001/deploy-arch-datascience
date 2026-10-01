# Bitácora de Peticiones — Registro Vivo del Proyecto

> **Documento vivo.** Registra el prompt inicial y **cada petición nueva** del usuario, en orden, con su
> interpretación, entregables, evidencia y estado. El prompt inicial íntegro vive en
> [initial-prompt.md](initial-prompt.md); aquí solo se resume y se enlaza.
> Última actualización: **2026-10-01** · Peticiones registradas: **7** (3 archivadas).

## 1. Protocolo de mantenimiento (obligatorio en cada petición nueva)

1. Añadir la petición a la tabla índice de la §2 con el siguiente ID correlativo (`P-003`, `P-004`, …).
2. Crear su sección en la §3 con la **petición literal** (cita textual, sin parafrasear).
3. Registrar: interpretación, entregables, archivos tocados, evidencia de verificación y estado.
4. Actualizar el índice maestro del [README.md](../../README.md) si la petición creó o renombró documentos.
5. Revalidar los invariantes: ningún `.md` > 200 líneas, 0 enlaces rotos, índice ≡ archivos reales.
6. Si este archivo supera **180 líneas**, archivar las peticiones cerradas más antiguas en
   `docs/prompts/archive-<año>-<trimestre>.md` y dejar aquí el índice y las activas.
7. Este archivo **no se reescribe hacia atrás**: una petición corregida añade una fila de seguimiento, no borra historia.
8. Si la petición nace de una duda o la resuelve, se actualiza [FAQ.md](../../FAQ.md) según su propio protocolo (§1).

## 2. Índice de peticiones

| ID | Fecha | Petición (resumen) | Entregables | Estado |
|---|---|---|---|---|
| `P-001` | 2026-10-01 | Diseñar y generar el entorno local productivo completo (Modern Data Stack + MLOps) con 7 agentes | 10 `.md` + stack Compose + 45 archivos de andamiaje | ✅ Verificada |
| `P-002` | 2026-10-01 | Documentar el prompt inicial y mantenerlo actualizado con cada petición nueva | `docs/prompts/initial-prompt.md`, `docs/prompts/prompt-log.md` | ✅ Verificada |
| `P-003` | 2026-10-01 | Documentar las siglas y sus significados (la tabla de servicios no era autoexplicativa) | `docs/glossary.md` + enlace en los 12 documentos | ✅ Verificada |
| `P-004` | 2026-10-01 | Documentar por qué se eligió cada herramienta, cuándo NO se recomienda, alternativas, pros y contras | `docs/decisions/` (4 archivos, 18 decisiones `D-01`…`D-18`) | ✅ Verificada |
| `P-005` | 2026-10-01 | Crear `FAQ.md` para dudas y comentarios, con actualización periódica y respuestas breves enlazadas a `/docs` | `FAQ.md` (34 consultas + 4 abiertas) y protocolo en AGENTS §1.8 | ✅ Verificada |
| `P-006` | 2026-10-01 | Poder aprender el proyecto: áreas especialistas como agentes, más agentes Profesor y Alumno que resuelvan dudas | `docs/learning/` (5 archivos: 9 módulos, 14 labs, rúbrica y agentes `professor`/`student`) | ✅ Verificada |
| `P-007` | 2026-10-01 | Ruta de tareas diarias: saber moverse en el entorno y qué se solicita comúnmente en el área | [daily-routine.md](../learning/daily-routine.md) + [daily-tasks.md](../learning/daily-tasks.md) (`T-01`…`T-20`) | ✅ Verificada |

> `P-001`…`P-003`: cerradas y archivadas íntegras en [archive-2026-Q4.md](archive-2026-Q4.md).

## 3. Peticiones

> Las peticiones cerradas **`P-001`…`P-003`** están archivadas íntegras en [archive-2026-Q4.md](archive-2026-Q4.md)
> (el registro superó las 180 líneas y se aplicó el protocolo §1.6).

### `P-004` — Decisiones de herramientas (ADR)

> «tambien documenta porque tomaste las decisiones de las herramienta, en que caso no se recomiendas, cuales son las alternativas, pros y contras»

| Campo | Detalle |
|---|---|
| Interpretación | Faltaba el registro de decisiones: el stack se justificaba de forma dispersa y nunca se decía **cuándo deja de ser una buena elección**, ni qué alternativas había con sus pros y contras. |
| Entregables | `docs/decisions/`: [README.md](../decisions/README.md) con criterios ponderados, disparadores de revisión, plantilla y estado de reversibilidad; y tres módulos con **18 decisiones** `D-01`…`D-18` ([storage-and-runtime](../decisions/storage-and-runtime.md), [orchestration-and-transform](../decisions/orchestration-and-transform.md), [ml-bi-and-memory](../decisions/ml-bi-and-memory.md)). |
| Estructura por decisión | Contexto · por qué (en este repositorio) · **cuándo NO** · señal de migración · reversibilidad y coste · tabla de alternativas con pros y contras. |
| Archivos tocados | 4 archivos nuevos en `docs/decisions/`, índice y §2 del [README.md](../../README.md) (filas de ejecutables y de prompts consolidadas para no romper el límite), y enlace desde [AGENTS.md](../../AGENTS.md), [docker-setup.md](../infrastructure/docker-setup.md), [data-pipeline.md](../architecture/data-pipeline.md), [mlflow-dbt-pipeline.md](../mlops/mlflow-dbt-pipeline.md) y [glossary.md](../glossary.md). |
| Evidencia | 17 documentos, ninguno > 179 líneas · 0 enlaces rotos · índice del README 17/17 · 18/18 decisiones con sección «Cuándo NO» y con al menos 4 alternativas comparadas. |
| Decisión de diseño | Cada decisión declara su **reversibilidad y coste**, porque una elección sin condiciones de revocación es un dogma, no una decisión de arquitectura. |
| Estado | ✅ Verificada |

### `P-005` — FAQ vivo de dudas y comentarios

> «crea un FAQ.md en donde se puedan ir dejando las dudas y comentarios, este tambien se debera ir actualizando periodicamente, la idea es que sean consultas breves y respuestas resumidas o indicando en que seccion de los /docs puedo responder esa duda»

| Campo | Detalle |
|---|---|
| Interpretación | Faltaba un punto de entrada por pregunta: las respuestas existían repartidas en 17 documentos, sin un lugar donde dejar dudas breves ni comentarios. |
| Entregables | [FAQ.md](../../FAQ.md): **34 consultas cerradas** en 6 secciones temáticas, **4 dudas abiertas**, protocolo de mantenimiento (revisión mensual + obligatoria al cerrar cada `P-00N`) y plantilla de alta. |
| Criterio de contenido | Cada fila responde en ≤2 líneas y enlaza a la **sección exacta** de `/docs`; si la respuesta exige más, se amplía el módulo y la FAQ solo enlaza. |
| Archivos tocados | `FAQ.md` (nuevo), índice del [README.md](../../README.md) (filas de decisiones consolidadas para no romper el límite de 180), [AGENTS.md](../../AGENTS.md) §1.8 y §1 de este registro. |
| Evidencia | 18 documentos, ninguno > 177 líneas · 0 enlaces rotos · índice del README 18/18 · 38 consultas registradas con enlace válido. |
| Decisión de diseño | Se descartaron las plantillas de enlace con marcador de posición (documento/ruta) para que ningún comprobador de enlaces del repositorio marque falsos positivos. |
| Estado | ✅ Verificada |

### `P-006` — Capa de aprendizaje con agentes Profesor y Alumno

> «necesito tambien poder aprender todo este proyecto, la idea seria tener las areas especialistas como agentes espcificos, tambien agregar agentes como profesor y alumno, los cuales resuelve dudas y demases.»

| Campo | Detalle |
|---|---|
| Interpretación | Faltaba la vía para **aprender** el proyecto: los 7 agentes lo operaban, pero nadie diseñaba una ruta formativa, ni evaluaba con criterio, ni representaba a quien está aprendiendo. |
| Entregables | `docs/learning/`: [README](../learning/README.md) (rutas y cómo pedir sesión), [curriculum](../learning/curriculum.md) (`M0`…`M8`), [professor-and-student-agents](../learning/professor-and-student-agents.md) (fichas, bucle de enseñanza en Mermaid y `learning-log`), [exercises-labs](../learning/exercises-labs.md) + [labs-quality-ml-bi](../learning/labs-quality-ml-bi.md) (`L-01`…`L-14`) y [assessment](../learning/assessment.md) (rúbrica `N0`-`N3` + banco `Q-01`…`Q-24`). |
| Modelo de agentes | Los 7 especialistas pasan a ser **áreas docentes** y se añaden `professor` y `student` → [AGENTS.md](../../AGENTS.md) §2 (9 agentes) y principio §1.9. |
| Bucle de aprendizaje | Diagnóstico → contexto mínimo → lab guiado → evidencia → rúbrica → repaso; el `student` puede operar en modo simulado y auditar la documentación. |
| Archivos tocados | 6 nuevos en `docs/learning/`, índice y §7 del README, AGENTS §1-§2-§6, glosario §7 (`M-0N`, `L-0N`, `Q-0N`), FAQ §8 (`F-039`…`F-044`) y este registro. |
| Evidencia | 24 documentos, ninguno > 180 líneas (se dividió `exercises-labs.md` al alcanzar 193) · 0 enlaces rotos · índice 24/24 · 9 módulos, 14 labs y 24 preguntas, todas con referencia verificada. |
| Decisión de diseño | La capa de aprendizaje es también **QA de la documentación**: el alumno simulado reporta fricciones que se convierten en aclaraciones o en filas del FAQ. |
| Estado | ✅ Verificada |

### `P-007` — Ruta de tareas diarias del área

> «Implementa una ruta con "tareas diarias" a realizar en el entorno. Así además del ecosistema puedes saber como moverte y que es lo que comúnmente te solicitan en el área»

| Campo | Detalle |
|---|---|
| Interpretación | Faltaba la dimensión **laboral**: cómo se organiza un día de trabajo, qué solicitudes llegan de verdad, cómo se priorizan y cómo se cierra una tarea con evidencia. |
| Entregables | [daily-routine.md](../learning/daily-routine.md) (ritmo en 3 bloques, ritual de apertura ejecutable, **catálogo de 20 solicitudes típicas** con quién pide, urgencia, agente y entregable, priorización y cierre) y [daily-tasks.md](../learning/daily-tasks.md) (backlog `T-01`…`T-20` en 4 semanas, con comandos del entorno y evidencia exigida). |
| Modelo de trabajo | Apertura 15 min (salud, frescura, fallos) → producción (1-3 solicitudes) → cierre 15 min (evidencia, respuesta de 3 líneas al solicitante, fila en `meta.session_events`). |
| Archivos tocados | 2 nuevos en `docs/learning/`, índice y §7 del README, `learning/README.md` y `curriculum.md` (tablas y navegación), glosario §7 (`T-0N`) y FAQ §8 (`F-045`…`F-048`). |
| Protocolo estrenado | Al superar el registro las 180 líneas, `P-001`…`P-003` se movieron **verbatim** a [archive-2026-Q4.md](archive-2026-Q4.md) y el índice del README se consolidó por temas para no crecer. |
| Evidencia | 27 documentos, ninguno > 180 líneas · 0 enlaces rotos · índice 27/27 · 20 tareas `T-0NN` y 20 tipos de solicitud, todos con comando o entregable verificable. |
| Estado | ✅ Verificada |

## 4. Convenciones

| Convención | Regla |
|---|---|
| Identificador | `P-00N` correlativo, nunca reutilizado |
| Estados | `propuesta` → `en curso` → `entregada` → `verificada` (o `bloqueada` + causa) |
| Petición literal | Siempre en cita textual; la interpretación va aparte y es revisable |
| Trazabilidad | Cada entregable se enlaza con ruta relativa; los requisitos se numeran `R-00N` |

## 5. Plantilla para la próxima petición

```markdown
### `P-00N` — <título corto>

> «<petición literal del usuario>»

| Campo | Detalle |
|---|---|
| Interpretación | Qué se entiende y qué se asume |
| Entregables | Archivos creados/modificados, con enlaces relativos |
| Evidencia | Comandos ejecutados y resultado real |
| Desviación | Qué se hizo distinto a lo pedido y por qué |
| Estado | `entregada` / `verificada` / `bloqueada` (+ causa) |
```

## 6. Hallazgos y correcciones aplicadas durante `P-001`

| # | Defecto detectado en la revisión | Corrección |
|---|---|---|
| 1 | Firma inválida de `s3()` en la macro de dbt | Endpoint dentro de la URL y 5 argumentos |
| 2 | `source()` no rendía una URL S3 | Macro resuelve `relation.identifier` + `var()`/`env_var()` |
| 3 | `external:` inválido en `_sources.yml` (dbt-core) | Ruta y formato movidos a `meta:` |
| 4 | Marts leyendo Bronze (rompía Medallion) | Creados `stg_payments` y `stg_support_tickets` |
| 5 | Test singular dentro de `model-paths` | Movido a `infra/dbt/tests/` + `test-paths` |
| 6 | *Quality gate* sin tests que lo alimentaran | Tests con `tag: critical` en los 3 marts |
| 7 | 3 DAGs con tareas TaskFlow sin argumentos | `run_id`/`ds` explícitos y templateados |
| 8 | Imagen Airflow sin *providers* ni librerías | `infra/airflow/Dockerfile` + `requirements.txt` |
| 9 | Contrato Gold incompatible con los datos sembrados | Enum y rangos alineados al esquema OLTP |
| 10 | Siglas sin definir (OLTP, OLAP, ELT, DAG, S3, PSI…) y servicios sin explicar | Creado [glossary.md](../glossary.md) y enlazado desde los 12 documentos |

## 7. Pendientes

| Pendiente | Depende de | Nota |
|---|---|---|
| Ejecución real del stack y primer ciclo Gold | Daemon de Docker encendido | Ver [runbook.md](../operations/runbook.md) §1 |
| Validación de `_path` de ClickHouse en runtime | ClickHouse levantado | Solo afecta a `ingested_dt` |
| Volcado íntegro de módulos en el chat (si se pide) | Preferencia del usuario | Alternativa a los archivos reales |

## 8. Navegación

| Documento | Contenido |
|---|---|
| [initial-prompt.md](initial-prompt.md) | Prompt inicial literal y requisitos `R-01`…`R-24` |
| [README.md](../../README.md) | Índice maestro, arquitectura y verificación |
| [AGENTS.md](../../AGENTS.md) | Agentes que ejecutan las peticiones y sus protocolos |
| [glossary.md](../glossary.md) | Siglas y términos citados en las peticiones |
