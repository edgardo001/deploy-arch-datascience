# FAQ — Dudas, Comentarios y Respuestas Cortas

> **Documento vivo.** Aquí se dejan las consultas breves; cada una se responde en **1-2 líneas** o, mejor,
> apuntando a la **sección exacta** de `docs/` que la resuelve. Versión inicial: **2026-10-01** (todas las
> respuestas llevan esa fecha) · Consultas registradas: **44** + **4 abiertas**.
> Contexto del proyecto: [README.md](README.md) · Petición que lo originó: [prompt-log.md](docs/prompts/prompt-log.md) `P-005`.

## 1. Cómo usar y mantener esta FAQ

1. **Formato**: `| F-00N | pregunta breve | respuesta resumida → enlace-relativo §sección |`. Una fila por consulta.
2. **Consultas breves**: si la pregunta exige más de 2 líneas de respuesta, la respuesta **no se escribe aquí**: se amplía el documento de `docs/` correspondiente y aquí se deja el enlace.
3. **Actualización periódica**: revisión mensual (cerrar dudas de la §9, corregir enlaces, retirar lo obsoleto) y revisión **obligatoria al cerrar cada petición `P-00N`**.
4. **Sin duplicar**: la FAQ no reemplaza a los módulos; su valor es el índice rápido y el registro de dudas.
5. **Si supera 180 líneas**: las consultas estables y cerradas se archivan en `docs/faq/archive-<año>.md` y aquí queda el índice y lo vivo.
6. **Numeración inmutable**: `F-00N` nunca se reutiliza; una respuesta corregida actualiza la fila y se anota en la §8 solo si cambia el sentido.
7. **Comentarios**: las observaciones sin pregunta (mejoras, quejas, ideas) van a la §9 con estado `comentario`.

## 2. Arranque, operación y entorno

| ID | Consulta | Respuesta resumida y dónde se responde |
|---|---|---|
| `F-001` | ¿Cómo levanto todo el stack? | `cp .env.example .env && docker compose up -d` y esperar 9/9 *healthy* → [runbook.md](docs/operations/runbook.md) §1 |
| `F-002` | ¿Por qué `dbt` no aparece como servicio *healthy*? | Es efímero (perfil `transform`): se ejecuta bajo demanda y se valida con `dbt build` exit 0 → [docker-setup.md](docs/infrastructure/docker-setup.md) §7 |
| `F-003` | Un servicio quedó `unhealthy`, ¿qué hago? | Revisar la tabla de troubleshooting y el playbook de recuperación → [runbook.md](docs/operations/runbook.md) §4-§5 |
| `F-004` | ¿Cuándo se ejecuta cada DAG? | Ingesta `@daily`; `transform_dbt_marts` 02:00; `train_churn_model` 04:00 → [docker-setup.md](docs/infrastructure/docker-setup.md) §2 |
| `F-005` | ¿Cómo detengo el entorno sin perder datos? | `docker compose down` conserva volúmenes; `down -v` los destruye → [MEMORY.md](MEMORY.md) §6 |
| `F-006` | ¿Qué puertos del host debo tener libres? | 5432, 9000/9001, 8123, 9100, 8080, 5000, 8888, 3000, 8088, 6333 → [README.md](README.md) §2 |
| `F-007` | ¿Dónde están las credenciales? | En `.env` (nunca versionado); la plantilla con valores de relleno es [.env.example](.env.example) → [docker-setup.md](docs/infrastructure/docker-setup.md) §4 |

## 3. Datos, modelado y transformación

| ID | Consulta | Respuesta resumida y dónde se responde |
|---|---|---|
| `F-008` | ¿Por qué BI no puede leer Bronze? | Bronze es crudo e inmutable: solo lo lee `staging`; consumir Bronze desde BI es un anti-patrón → [data-pipeline.md](docs/architecture/data-pipeline.md) §6 |
| `F-009` | ¿`customer_sk` y `customer_id` son lo mismo? | No: `customer_id` es la clave de negocio (BK) y `customer_sk` la sustituta (SK) que permite el SCD2 → [glossary.md](docs/glossary.md) §9 |
| `F-010` | Quiero una tabla o KPI nuevo, ¿por dónde empiezo? | La intención `modeling` rutea a `analytics_engineer`: modelo dbt + tests + contrato → [orchestration-rules.md](docs/agents/orchestration-rules.md) §4 |
| `F-011` | ¿Cómo reproceso un día concreto? | Playbook: reproducir desde Bronze (inmutable) con el `run_id` original y validar contratos → [runbook.md](docs/operations/runbook.md) §5 |
| `F-012` | ¿Por qué `avg_ticket` puede valer 0? | Porque el cliente no compró en 365 días; el contrato exige `>= 0` y el 0 dispara un aviso suave → [mlflow-dbt-pipeline.md](docs/mlops/mlflow-dbt-pipeline.md) §2 |
| `F-013` | ¿Por qué el segmento solo admite `retail`, `pyme`, `enterprise`? | Es el `CHECK` real del OLTP; el contrato Gold se alineó a los datos, no al revés → [marts.yml](infra/contracts/marts.yml) |
| `F-014` | ¿Cuál es la granularidad de los hechos? | `fct_orders`: una fila por línea de pedido; `fct_payments`: una por pago → [data-pipeline.md](docs/architecture/data-pipeline.md) §4 |

## 4. Agentes, peticiones y memoria

| ID | Consulta | Respuesta resumida y dónde se responde |
|---|---|---|
| `F-015` | ¿Qué hace cada agente y qué herramientas tiene? | Fichas con rol, entradas, salidas, herramientas y DoD → [AGENTS.md](AGENTS.md) §2 |
| `F-016` | ¿Quién decide qué agente atiende mi petición? | El `orchestrator` con *scoring* de intención y umbral 0.55 → [orchestration-rules.md](docs/agents/orchestration-rules.md) §3-§4 |
| `F-017` | ¿Dónde queda registrada una petición mía? | En la bitácora, con ID `P-00N`, interpretación y evidencia → [prompt-log.md](docs/prompts/prompt-log.md) §1-§3 |
| `F-018` | ¿Qué es un *handoff* y qué contiene? | Mensaje tipado con `run_id`, artefactos, contratos y `next_agent` → [orchestration-rules.md](docs/agents/orchestration-rules.md) §5 |
| `F-019` | ¿Qué recuerda el sistema y por cuánto tiempo? | Memoria corta (sesión/run) y larga (metadata, Qdrant, MLflow) con retención por volumen → [MEMORY.md](MEMORY.md) §1-§3 y §6 |
| `F-020` | ¿Qué pasa si un paso falla? | Reintentos con *backoff*, *quality gate* que bloquea Gold y escalado definido → [AGENTS.md](AGENTS.md) §5 |

## 5. MLOps y modelos

| ID | Consulta | Respuesta resumida y dónde se responde |
|---|---|---|
| `F-021` | ¿Cómo entreno y registro un modelo? | `python infra/pipelines/train_churn.py --run-id …` registra parámetros, métricas y firma → [mlflow-dbt-pipeline.md](docs/mlops/mlflow-dbt-pipeline.md) §3 |
| `F-022` | ¿Por qué mi modelo no pasa a `Production`? | Requiere ROC-AUC sobre *baseline*, PSI < 0.2 y paridad demográfica; si no, queda en `Staging` → [mlflow-dbt-pipeline.md](docs/mlops/mlflow-dbt-pipeline.md) §4 |
| `F-023` | ¿Qué significa PSI > 0.2? | Deriva fuerte en una *feature*: se congela el *scoring* y el dashboard se marca no certificado → [glossary.md](docs/glossary.md) §6 |
| `F-024` | ¿Dónde quedan modelos y artefactos? | En MLflow (`datalab_meta` + `s3://datalake/mlflow`) y el volumen `mlflow_artifacts` → [MEMORY.md](MEMORY.md) §6 |
| `F-025` | ¿De dónde salen las *features*? | Solo de marts Gold (`customer_features`), nunca del OLTP ni de Bronze → [mlflow-dbt-pipeline.md](docs/mlops/mlflow-dbt-pipeline.md) §1 |

## 6. BI, dashboards y consumo

| ID | Consulta | Respuesta resumida y dónde se responde |
|---|---|---|
| `F-026` | ¿Uso Metabase o Superset? | Metabase para *self-service*; Superset para gobierno, SQL Lab y automatización; el coste de tener ambas está asumido → [decisions/ml-bi-and-memory.md](docs/decisions/ml-bi-and-memory.md) `D-17` |
| `F-027` | ¿Cómo conecto una herramienta de BI al DW? | Driver ClickHouse con `jdbc:clickhouse://clickhouse:8123/marts` (host = nombre de servicio) → [runbook.md](docs/operations/runbook.md) §4 |
| `F-028` | ¿Puedo analizar el lake sin levantar ClickHouse? | Sí: DuckDB con `read_parquet` sobre MinIO, es el *output* `duckdb` del perfil dbt → [decisions/storage-and-runtime.md](docs/decisions/storage-and-runtime.md) `D-06` |

## 7. Documentación, reglas y decisiones

| ID | Consulta | Respuesta resumida y dónde se responde |
|---|---|---|
| `F-029` | ¿Por qué ningún `.md` supera 180/200 líneas? | Es la regla de oro #2 del encargo: lo que excede se poda y se desglosa en `/docs` con enlaces → [initial-prompt.md](docs/prompts/initial-prompt.md) §3 `R-10`, `R-11` |
| `F-030` | No entiendo una sigla (OLTP, PSI, SCD2…) | Están todas definidas con su implicación práctica → [glossary.md](docs/glossary.md) §2-§7 |
| `F-031` | ¿Por qué se eligió esta herramienta y no otra? | Cada pieza tiene una decisión con alternativas, pros, contras y «cuándo NO» → [decisions/README.md](docs/decisions/README.md) §4 |
| `F-032` | ¿Cómo propongo un cambio en la documentación? | Se registra como petición `P-00N` y, si nace de una duda, se enlaza aquí → [prompt-log.md](docs/prompts/prompt-log.md) §1 |
| `F-033` | ¿Hay pruebas automáticas? | Tests dbt (`tag: critical` como *gate*) y auditorías en `infra/qa/` → [specialists-deep-dive.md](docs/agents/specialists-deep-dive.md) §4 y §7 |
| `F-034` | ¿Qué evidencia hay de que esto funciona? | Conteos de líneas, enlaces, YAML/JSON y sintaxis Python verificados; la ejecución real con Docker queda pendiente → [README.md](README.md) §6 |

## 8. Aprendizaje: profesor, alumno y rutas

| ID | Consulta | Respuesta resumida y dónde se responde |
|---|---|---|
| `F-039` | ¿Por dónde empiezo a aprender el proyecto? | Módulo `M0` (orientación, 60 min) y después tu ruta por perfil → [learning/README.md](docs/learning/README.md) §4 |
| `F-040` | ¿Quién me enseña y quién resuelve mis dudas? | El `professor` diseña la ruta; cada especialista responde dudas de su dominio → [professor-and-student-agents.md](docs/learning/professor-and-student-agents.md) §2 |
| `F-041` | ¿Cómo sé que he aprendido algo? | Evidencia ejecutada + explicación con tus palabras + repaso; rúbrica `N0`-`N3` → [assessment.md](docs/learning/assessment.md) §1-§2 |
| `F-042` | ¿Puedo hacerme un quiz de un módulo? | Sí: banco `Q-01`…`Q-24` con respuesta esperada y enlace a la fuente → [assessment.md](docs/learning/assessment.md) §3 |
| `F-043` | ¿Puedo practicar sin romper el pipeline? | Los 14 labs son reversibles; `L-08` y `L-11` fallan a propósito para estudiar el fallo → [labs 1-8](docs/learning/exercises-labs.md) y [labs 9-14](docs/learning/labs-quality-ml-bi.md) |
| `F-044` | ¿Para qué sirve el agente `student` si el alumno soy yo? | Puede operar en modo simulado: sigue los documentos como novato y reporta cada fricción → [professor-and-student-agents.md](docs/learning/professor-and-student-agents.md) §3 |
| `F-045` | ¿Qué se hace en un día normal en este entorno? | Ritual de apertura (salud, frescura, fallos), producción de solicitudes y cierre con evidencia → [daily-routine.md](docs/learning/daily-routine.md) §1-§2 |
| `F-046` | ¿Qué me van a pedir cuando trabaje en esto? | 20 solicitudes típicas con quién pide, urgencia, agente y entregable → [daily-routine.md](docs/learning/daily-routine.md) §3 |
| `F-047` | Quiero «trabajar» el entorno: ¿por dónde empiezo? | Backlog `T-01`…`T-20` repartido en 4 semanas, con comandos y cierre → [daily-tasks.md](docs/learning/daily-tasks.md) |
| `F-048` | ¿Cómo priorizo si me llegan tres cosas a la vez? | Matriz urgencia × impacto y reglas de convivencia (una crítica a la vez) → [daily-routine.md](docs/learning/daily-routine.md) §4 |

## 9. Dudas abiertas y comentarios

| ID | Duda o comentario | Estado |
|---|---|---|
| `F-035` | ¿Se puede confirmar en runtime la columna `_path` de `s3()` en ClickHouse? (solo afecta a `ingested_dt`) | Abierta · bloqueada por daemon Docker apagado → [prompt-log.md](docs/prompts/prompt-log.md) §7 |
| `F-036` | ¿Conviene consolidar el BI en una sola herramienta? | Abierta · depende del tamaño del equipo; disparador en [decisions/README.md](docs/decisions/README.md) §5 |
| `F-037` | ¿Migramos Bronze a Iceberg/Delta para tener MERGE y *time travel*? | Abierta · solo si aparecen borrados retroactivos; ver `D-04` |
| `F-038` | ¿Añadimos un *feature store* (Feast) al stack? | Abierta · solo si el linaje por columna pasa a ser requisito; ver `D-13` |

## 10. Plantilla para añadir una consulta

```markdown
| `F-0NN` | <pregunta breve, en una línea> | <respuesta ≤2 líneas> → enlace-relativo §sección |
```

El `enlace-relativo` se escribe con la ruta real desde la raíz (por ejemplo `docs/operations/runbook.md`),
nunca como marcador de posición: así cualquier comprobador de enlaces del repositorio lo valida.

Si la duda no tiene respuesta todavía, se añade a la §9 con estado `abierta` y, cuando se resuelva, se
promueve a la sección temática correspondiente y se deja la fila de la §9 como `cerrada` con el enlace.

## 11. Navegación

| Documento | Contenido |
|---|---|
| [README.md](README.md) | Índice maestro, arquitectura y verificación |
| [runbook.md](docs/operations/runbook.md) | Operación diaria, troubleshooting y playbooks |
| [glossary.md](docs/glossary.md) | Siglas y servicios, uno por uno |
| [decisions/README.md](docs/decisions/README.md) | Por qué cada herramienta y cuándo deja de servir |
| [prompt-log.md](docs/prompts/prompt-log.md) | Bitácora de peticiones y dudas convertidas en cambios |
| [learning/README.md](docs/learning/README.md) | Rutas de aprendizaje, labs y rúbrica con los agentes `professor` y `student` |
