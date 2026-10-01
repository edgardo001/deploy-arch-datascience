# Caso de Estudio — Comprender un Entorno Productivo de Data Science

> **Descripción inicial del proyecto.** Este repositorio no es solo una instalación de herramientas: es un
> **caso de estudio** para entender cómo se arma un entorno productivo de Data Science, quién hace qué y qué
> hay detrás de un dashboard. Rutas: [learning/README.md](learning/README.md) · Tareas reales:
> [daily-routine.md](learning/daily-routine.md) · Arquitectura: [README.md](../README.md) §3.

## 1. Descripción inicial (texto de origen, mejorado)

> Pensé que, si uno no trabaja directamente en esta área, es difícil ver cómo otros arman una arquitectura de
> Data Science de punta a punta. También veo que muchos trabajan con los datos —o solo con los gráficos— sin
> notar todo lo que hay detrás: no es una sola persona, sino **áreas y cargos distintos**, cada uno responsable
> de una sección.
>
> Y hay una distinción que suele pasarse por alto: **levantar la plataforma no lo hace el mismo perfil que
> analiza los datos**. Infraestructura de TI (o Cloud/DevOps) provee las máquinas, la red y el almacenamiento
> base; Data Engineering instala y configura sobre esa base las herramientas, los *pipelines* y la orquestación;
> Analytics Engineering modela los datos para que sean confiables y reutilizables; Data Science y MLOps
> construyen y mantienen los modelos; y BI, analistas y especialistas de visualización convierten todo eso en
> decisiones.
>
> Este caso de estudio reconstruye ese ecosistema completo en local —con sus roles, sus contratos y su
> gobierno— para entender qué hay debajo de un dashboard y qué se le pide a cada cargo en el día a día.

## 2. La metáfora del iceberg

| Capa | Lo que se ve | Lo que hay detrás |
|---|---|---|
| Consumo | Un dashboard, un informe, una predicción | Definiciones de KPI, semántica, permisos y dueños |
| Modelado | Tablas «que ya existen» | Esquema en estrella, SCD2, contratos y tests de calidad |
| Transformación | «Los datos limpios» | dbt: capas `staging`/`intermediate`/`marts`, linaje y *seeds* |
| Ingesta | «El dato llegó» | Extracción incremental, *watermarks*, idempotencia y auditoría |
| Almacenamiento | Un nombre de base de datos | Lake en objetos, particionado, retención y coste |
| Plataforma | «La herramienta ya está» | Contenedores, red, volúmenes, secretos, perfiles y *healthchecks* |

## 3. Los cargos, uno por uno

| Cargo | De qué responde | Aquí lo ves en |
|---|---|---|
| Infraestructura de TI / Cloud | Servidores, red, seguridad, cómputo y almacenamiento base; hoy con IaC (Terraform) y orquestadores (Kubernetes) | [docker-setup.md](infrastructure/docker-setup.md) (la «casa»), agente `platform` |
| Data Platform Engineer | El «suelo de datos»: warehouse, catálogo, permisos, coste y disponibilidad | Compose + volúmenes + Qdrant, agente `platform` |
| Data Engineer | Ingesta, *pipelines*, orquestación y calidad del traslado | DAG `ingest_oltp_to_bronze`, agente `data_engineer` |
| Analytics Engineer | Modelado dimensional, tests, contratos y semántica reutilizable | dbt `marts/*`, agente `analytics_engineer` |
| DBA | Copias, *tuning*, disponibilidad y acceso a los motores | `01_databases.sql`, retención en [MEMORY.md](../MEMORY.md) §6 |
| Data Quality / Governance | Linaje, contratos, privacidad, sesgo y *drift* | `infra/qa/*.py`, agente `governance` |
| Data Scientist | EDA, *features*, modelos y evaluación | `train_churn.py`, agente `ds_mlops` |
| ML / MLOps Engineer | Empaquetado, despliegue, monitoreo y promoción de modelos | MLflow + `score.py`, agente `ds_mlops` |
| Data Analyst | Análisis descriptivo y diagnóstico de negocio | [daily-tasks.md](learning/daily-tasks.md) `T-01`, `T-11` |
| BI Developer / Analytics | Dashboards, capa semántica y certificación de KPIs | Metabase y Superset, agente `bi_viz` |
| Especialista en visualización | Claridad y diseño de la presentación | [decisions/ml-bi-and-memory.md](decisions/ml-bi-and-memory.md) `D-17` |
| Product Owner / Negocio | Prioriza preguntas, define KPIs y acepta entregables | `orchestrator` y el catálogo de solicitudes |

**Quién levanta qué** (la duda más frecuente): Infraestructura pone las máquinas y la red; Data Engineering
instala y conecta las herramientas de datos sobre esa base; en equipos pequeños ambas responsabilidades se
solapan en una sola persona, y en empresas grandes se separan por seguridad y por especialización. Aquí el
equivalente es [docker-compose.yml](../docker-compose.yml): la «casa» (infra) y el «mobiliario» (herramientas),
en un mismo archivo, porque es un laboratorio de aprendizaje.

## 4. Del organigrama de la industria a este repositorio

| En la industria | Aquí es el agente | Dónde verlo |
|---|---|---|
| Arquitecto / Tech Lead / PO | `orchestrator` | [AGENTS.md](../AGENTS.md) §2.1 |
| Infraestructura + plataforma | `platform` | [AGENTS.md](../AGENTS.md) §2.2 |
| Data Engineering | `data_engineer` | §2.3 |
| Analytics Engineering | `analytics_engineer` | §2.4 |
| Data Science + MLOps | `ds_mlops` | §2.5 |
| BI + visualización | `bi_viz` | §2.6 |
| Gobierno y calidad | `governance` | §2.7 |
| Formación interna / onboarding | `professor` y `student` | [learning/professor-and-student-agents.md](learning/professor-and-student-agents.md) |

## 5. Qué se aprende con este caso de estudio

1. **Ver el iceberg completo**: por qué un número del dashboard depende de un `run_id`, un contrato y un test.
2. **Hablar el idioma de cada área**: qué se le puede pedir a un Data Engineer y qué a un Analytics Engineer.
3. **Distinguir responsabilidades**: plataforma, ingeniería, modelado, ciencia, gobierno y consumo.
4. **Reconocer las solicitudes reales**: incidencias de frescura, KPIs nuevos, auditorías, informes y sesgo.
5. **Decidir con criterio**: cada herramienta tiene su «cuándo NO» documentado en [decisions/](decisions/README.md).
6. **Operar con evidencia**: ninguna tarea se cierra sin número, comando o artefacto verificable.

## 6. Cómo recorrerlo

| Si quieres… | Empieza en |
|---|---|
| Entender la arquitectura en 10 minutos | [README.md](../README.md) §3 y §2 |
| Aprender con un plan guiado | [learning/README.md](learning/README.md) y su currículo `M0`…`M8` |
| Practicar como si trabajaras | [daily-routine.md](learning/daily-routine.md) y `T-01`…`T-20` |
| Saber por qué cada herramienta está aquí | [decisions/README.md](decisions/README.md) |
| Resolver una duda puntual | [FAQ.md](../FAQ.md) y el [glosario](glossary.md) |

## 7. Navegación

| Documento | Contenido |
|---|---|
| [glossary.md](glossary.md) | Siglas y los 10 servicios, uno por uno |
| [decisions/README.md](decisions/README.md) | Decisiones de herramientas con pros, contras y «cuándo NO» |
| [learning/README.md](learning/README.md) | Rutas de aprendizaje, labs y evaluación |
| [architecture/data-pipeline.md](architecture/data-pipeline.md) | Viaje del dato, paso a paso |
