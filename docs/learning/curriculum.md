# Currículo — 9 Módulos del Proyecto

> Módulos `M0`…`M8` del [aprendizaje](README.md). Cada módulo declara **objetivo, artefactos reales que se tocan,
> laboratorios y evidencia de aprobación**. Los labs se detallan en [exercises-labs.md](exercises-labs.md) y la
> evaluación en [assessment.md](assessment.md). Notación: [glossary.md](../glossary.md) §7.

## Cómo se lee un módulo

| Campo | Significado |
|---|---|
| **Objetivo** | Qué sabrá *hacer* el alumno al terminar (verbo medible) |
| **Artefactos** | Archivos y servicios reales del repositorio que se usan |
| **Labs** | Ejercicios con criterio de aceptación binario |
| **Evidencia** | Prueba mínima exigida para aprobar (comando + salida o artefacto) |
| **Duración** | Estimación para un perfil con la base indicada |

## `M0` · Orientación y mapa del proyecto

| | |
|---|---|
| **Objetivo** | Explicar qué hace cada servicio del stack, dónde vive cada tipo de dato y cómo navegar la documentación |
| **Artefactos** | [README.md](../../README.md) §2-§3, [glossary.md](../glossary.md), [docker-compose.yml](../../docker-compose.yml) |
| **Labs** | `L-01`, `L-02` |
| **Evidencia** | Stack levantado con 9/9 *healthy* + mapa propio dibujado o descrito con las 3 capas (lake, DW, consumo) |
| **Duración** | 60 min · sin prerrequisitos |

## `M1` · Fundamentos de datos y arquitectura Medallion

| | |
|---|---|
| **Objetivo** | Distinguir OLTP de OLAP y justificar el paso por `bronze → silver → gold` |
| **Artefactos** | [data-pipeline.md](../architecture/data-pipeline.md) §1-§3, [decisions/storage-and-runtime.md](../decisions/storage-and-runtime.md) `D-01`, `D-04`, `D-05` |
| **Labs** | `L-03`, `L-04` |
| **Evidencia** | Consultar la misma entidad en Bronze (Parquet) y en Gold (DW) y explicar las diferencias observadas |
| **Duración** | 90 min · requiere `M0` |

## `M2` · Ingesta incremental y auditoría

| | |
|---|---|
| **Objetivo** | Ejecutar y auditar una extracción incremental idempotente desde el OLTP al lake |
| **Artefactos** | `infra/airflow/dags/ingest_oltp_to_bronze.py`, `meta.ingest_audit`, [docker-setup.md](../infrastructure/docker-setup.md) §7 |
| **Labs** | `L-05`, `L-06` |
| **Evidencia** | DAG `ingest_oltp_to_bronze` en verde + fila propia en `meta.ingest_audit` con `rows_read` que cuadra |
| **Duración** | 120 min · requiere `M1` |

## `M3` · Transformación analítica con dbt

| | |
|---|---|
| **Objetivo** | Construir y testear modelos por capas, entender materializaciones y leer el linaje |
| **Artefactos** | `infra/dbt/models/`, `infra/dbt/tests/`, `infra/dbt/seeds/`, [data-pipeline.md](../architecture/data-pipeline.md) §3 |
| **Labs** | `L-07`, `L-08` |
| **Evidencia** | `dbt build --select staging marts` sin errores + un test propio que falle y luego pase |
| **Duración** | 150 min · requiere `M2` |

## `M4` · Modelado dimensional

| | |
|---|---|
| **Objetivo** | Explicar granularidad, claves sustitutas y SCD2, y consultar KPIs con SQL correcto |
| **Artefactos** | `marts.fct_orders`, `dim_customer`, `dim_date`, [data-pipeline.md](../architecture/data-pipeline.md) §4 |
| **Labs** | `L-09`, `L-10` |
| **Evidencia** | Consulta de ingresos por categoría por mes, correcta y sin doble conteo, explicando la granularidad usada |
| **Duración** | 120 min · requiere `M3` |

## `M5` · Orquestación, contratos y puertas de calidad

| | |
|---|---|
| **Objetivo** | Programar dependencias, provocar un fallo controlado y comprobar que el *quality gate* bloquea |
| **Artefactos** | `infra/airflow/dags/transform_dbt_marts.py`, `infra/contracts/marts.yml`, `infra/qa/contract_check.py`, [orchestration-rules.md](../agents/orchestration-rules.md) §5-§6 |
| **Labs** | `L-11`, `L-12` |
| **Evidencia** | Test crítico roto a propósito que impide publicar Gold + registro del gate en `meta.quality_gates` |
| **Duración** | 120 min · requiere `M4` |

## `M6` · Ciencia de datos y MLOps

| | |
|---|---|
| **Objetivo** | Entrenar, registrar, evaluar y promover un modelo con trazabilidad completa |
| **Artefactos** | `infra/pipelines/train_churn.py`, `register.py`, `score.py`, [mlflow-dbt-pipeline.md](../mlops/mlflow-dbt-pipeline.md) |
| **Labs** | `L-13` |
| **Evidencia** | Run en MLflow con `run_id` y `dbt_manifest` + decisión razonada de promover o no a `Production` |
| **Duración** | 150 min · requiere `M4` (no depende de `M5`) |

## `M7` · BI, métricas y consumo

| | |
|---|---|
| **Objetivo** | Publicar un KPI certificado, reproducible por SQL y con dueño declarado |
| **Artefactos** | Metabase (3000), Superset (8088), `marts.*`, [decisions/ml-bi-and-memory.md](../decisions/ml-bi-and-memory.md) `D-17` |
| **Labs** | `L-14` |
| **Evidencia** | Dashboard con un KPI cuya consulta SQL se puede reproducir desde la documentación |
| **Duración** | 90 min · requiere `M4` |

## `M8` · Gobierno, linaje y operación multi-agente

| | |
|---|---|
| **Objetivo** | Trazar un dato de extremo a extremo, auditar sesgo/drift y redactar una decisión de arquitectura |
| **Artefactos** | `infra/qa/*.py`, `meta.handoffs`, [decisions/README.md](../decisions/README.md), [AGENTS.md](../../AGENTS.md), [MEMORY.md](../../MEMORY.md) |
| **Labs** | Complementario: se evalúa con `Q-11`…`Q-24` de [assessment.md](assessment.md) |
| **Evidencia** | Un ADR nuevo (o una revisión de uno existente) con «cuándo NO» + informe de drift o sesgo ejecutado |
| **Duración** | 150 min · requiere `M5` y `M6` |

## Rutas por perfil

| Perfil | Ruta recomendada | Duración total |
|---|---|---|
| Analista de negocio | `M0 → M1 → M4 → M7` | ~6 h |
| Ingeniero de datos | `M0 → M1 → M2 → M3 → M5` | ~9 h |
| Científico de datos | `M0 → M1 → M3 → M4 → M6` | ~9 h |
| Responsable de plataforma | `M0 → M1 → M5 → M6 → M8` | ~10 h |
| Curioso total | `M0 … M8` en orden | ~18 h |

## Reglas de progresión

1. **No se salta un módulo** sin aprobar su evidencia, salvo que el diagnóstico inicial del `professor` lo justifique por experiencia previa demostrable.
2. **Una evidencia por lab**: sin salida de comando o artefacto verificable, el lab no cuenta.
3. **Repaso espiral**: cada módulo termina con 2 preguntas de módulos anteriores (`Q-0NN`).
4. **La fricción es un resultado válido**: si un documento no permite completar el lab, se registra como hallazgo y se mejora la documentación.
5. **Un módulo se reabre** si cambia el artefacto subyacente (por ejemplo, un cambio de esquema en `marts`), porque el alumno debe aprender el estado actual del repositorio.

## Navegación

| Documento | Contenido |
|---|---|
| [README.md](README.md) | Cómo funciona la capa de aprendizaje y cómo pedir una sesión |
| [professor-and-student-agents.md](professor-and-student-agents.md) | Roles, fichas, protocolo de sesión y `learning-log` |
| [exercises-labs.md](exercises-labs.md) | Los laboratorios `L-01`…`L-08` (entorno, lake, ingesta, dbt) |
| [labs-quality-ml-bi.md](labs-quality-ml-bi.md) | Los laboratorios `L-09`…`L-14` (modelado, calidad, ML, BI) |
| [daily-routine.md](daily-routine.md) | El ritmo diario y las solicitudes típicas del área |
| [daily-tasks.md](daily-tasks.md) | Las 20 tareas `T-01`…`T-20` para practicar ese ritmo |
| [assessment.md](assessment.md) | Rúbrica de niveles y banco de preguntas |
