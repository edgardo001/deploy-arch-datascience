# Prompt Inicial — Transcripción Literal y Requisitos Destilados

> Registro histórico del prompt que originó el proyecto (`P-001` en [prompt-log.md](prompt-log.md)).
> Se conserva **sin editar** para que cualquier agente futuro reconstruya la intención original.
> Estado de cumplimiento: verificado archivo por archivo en la bitácora.

## 1. Transcripción literal

> Recibido: **2026-10-01** · Autor: usuario del proyecto (`edgardo001`) · Idioma: español.
> El bloque siguiente es copia fiel; los únicos añadidos son la numeración de secciones del original.

````markdown
Actúa como Arquitecto de Plataforma de Datos Senior y Especialista en MLOps / Sistemas Multi-Agente.

Tu objetivo es diseñar y generar la estructura completa de documentación, agentes, memoria y archivos auxiliares para un entorno local de Pruebas de Ciencia e Ingeniería de Datos Productiva. El entorno simula la arquitectura real que utilizan las empresas líderes (Modern Data Stack + MLOps) emulado mediante Docker Compose.

---

### ARQUITECTURA TÉCNICA ESTÁNDAR A MODELAR:
1. Fuentes Transaccionales (OLTP): PostgreSQL (Base de datos operativa / e-commerce).
2. Data Lake / Object Storage: MinIO (Emulador local compatible con AWS S3 para datos crudos/Parquet).
3. Data Warehouse / OLAP: PostgreSQL Analítico / ClickHouse / DuckDB (Modelado dimensional en estrella).
4. Orquestación ETL/ELT: Apache Airflow (Programación de DAGs y flujos de trabajo).
5. Transformación Analítica: dbt (data build tool, para modelos SQL, linaje y pruebas de calidad).
6. MLOps & Tracking: MLflow (Registro de experimentos, métricas y empaquetado de modelos).
7. Entorno de Experimentación: JupyterLab (Python: pandas, scikit-learn, xgboost, sqlalchemy, PySpark).
8. BI & Dashboarding: Metabase / Apache Superset (Visualización e indicadores de negocio).

---

### REGLAS DE ORO DE LONGITUD Y MODULARIDAD (STRICT):
1. NINGÚN archivo `.md` (sea principal o de la carpeta `/docs`) puede superar las 200 líneas de texto.
2. Si un módulo o documento supera las 180 líneas, DEBES podarlo, crear un nuevo archivo `.md` especializado dentro de la carpeta `/docs/` e incluir el enlace relativo correspondiente.
3. Conservación del 100% de la información útil mediante enlaces cruzados e indexación estricta entre archivos.
4. Usa Markdown limpio, estructurado y profesional con tablas, listas y bloques de código cuando sea pertinente.

---

### EQUIPO DE AGENTES ESPECIALISTAS A DEFINIR:
1. Orchestrator & Workflow Agent: Rutea peticiones, orquesta la ejecución del pipeline completo y gestiona la sesión.
2. Data Platform & Infrastructure Agent: Administra Docker Compose, volúmenes, red, buckets de MinIO y conexiones ODBC/JDBC.
3. Data Engineer Agent: Diseña la ingesta desde PostgreSQL OLTP hacia MinIO (Data Lake) y orquesta DAGs en Airflow.
4. Analytics Engineer Agent: Construye modelos dimensionales en dbt (staging, intermediate, marts), esquemas en estrella y pruebas de calidad.
5. Data Science & MLOps Agent: Realiza EDA en JupyterLab, entrena modelos predictivos (Scikit-Learn/XGBoost) y registra artefactos/métricas en MLflow.
6. BI & Data Visualization Agent: Construye dashboards interactivos en Metabase/Superset y define métricas DAX/SQL de negocio.
7. Governance & QA Agent: Supervisa linaje de datos, pruebas de dbt, auditoría de sesgo y monitoreo de *data drift*.

---

### ENTREGABLES REQUERIDOS EN LA RESPUESTA:

Proporciona el contenido exacto y completo de los siguientes archivos usando bloques de código con su ruta relativa:

#### 1. `README.md` (Vista General del Proyecto y Despliegue Local)
- Propuesta de valor de este entorno local productivo.
- Matriz indexada de archivos (accesos directos a todos los `.md` del repositorio).
- Diagrama Mermaid de Arquitectura del Pipeline de Datos (desde PostgreSQL OLTP -> MinIO -> dbt -> DW -> MLflow -> Metabase).
- Guía de inicio rápido (`docker compose up -d`) e instrucciones de verificación de servicios por puerto.

#### 2. `AGENTS.md` (Definición Operativa Multi-Agente)
- Catálogo detallado de los 7 Agentes Especialistas (Rol, Entradas, Salidas, Herramientas del stack asignadas).
- Diagrama Mermaid de Secuencia e Interacción Multi-Agente.
- Matriz de delegación y protocolos de manejo de errores / *fallback*.
- Enlaces de navegación hacia la carpeta `/docs/agents/`.

#### 3. `MEMORY.md` (Gestión de Estado, Contexto y Persistencia)
- Estructura de Memoria a Corto Plazo (Contexto de conversación/ejecución) vs. Largo Plazo (Vector DB / Metadata Store).
- Ejemplo en formato JSON del estado global del pipeline en ejecución.
- Politicas de persistencia, volumenes Docker y retencion de metadatos.
- Enlaces de navegación hacia `/docs/memory/`.

#### 4. Diagramas Mermaid Incluidos
- Mínimo 3 diagramas completos e integrados en los Markdown:
  1. Arquitectura de Infraestructura y Pipeline de Datos (en `README.md`).
  2. Diagrama de Secuencia y Protocolo de Comunicación entre Agentes (en `AGENTS.md`).
  3. Diagrama de Estado y Ciclo de Vida de los Datos/Memoria (en `MEMORY.md`).

#### 5. Carpeta `/docs` (Módulos Desglosados para Garantizar Límite de 200 Líneas)
Genera el contenido de los siguientes archivos en la carpeta `/docs/`:
- `/docs/architecture/data-pipeline.md`: Explicación paso a paso del viaje del dato (OLTP -> Lakehouse -> ML/BI).
- `/docs/infrastructure/docker-setup.md`: Especificación técnica de servicios Docker, variables de entorno y puertos.
- `/docs/agents/orchestration-rules.md`: Algoritmos de ruteo, condiciones de transferencia y reglas de negocio.
- `/docs/agents/specialists-deep-dive.md`: Guía técnica extendida de cada agente y sus comandos/scripts.
- `/docs/mlops/mlflow-dbt-pipeline.md`: Integración técnica entre las transformaciones de dbt y el tracking de MLflow.

---

### FORMATO DE ENTREGA:

Muestra cada archivo claramente etiquetado en un bloque de código separado, así:

```markdown
<!-- File: README.md -->
...
```
````

## 2. Contexto de entorno inyectado por el harness (ajeno al prompt)

| Elemento | Valor en la sesión original |
|---|---|
| Directorio de trabajo | `deploy-arch-datascience` (vacío al inicio) |
| Política de archivos | `workspace-write`; aprobaciones `ask` |
| Runtime disponible | Docker CLI sin daemon activo; Python embebido sin `PyYAML`; Node con `yaml` |
| Formato asumido por el usuario | bloques de código en el chat; se materializó en archivos reales (ver `P-002`) |

## 3. Requisitos destilados y trazabilidad

| ID | Requisito del prompt | Cumplido en | Estado |
|---|---|---|---|
| R-01 | 8 componentes del Modern Data Stack en Docker Compose | [docker-compose.yml](../../docker-compose.yml) (10 servicios) | ✅ |
| R-02 | OLTP PostgreSQL de e-commerce | `infra/postgres/init/{02_oltp_schema,03_oltp_seed}.sql` | ✅ |
| R-03 | Data Lake MinIO compatible S3 (Parquet crudo) | Buckets `bronze/silver/gold/mlflow` vía `minio-init` | ✅ |
| R-04 | DW/OLAP con modelo dimensional en estrella | [data-pipeline.md](../architecture/data-pipeline.md) §4 + marts dbt | ✅ |
| R-05 | Orquestación con Airflow (DAGs) | `infra/airflow/dags/` (`ingest_*`, `transform_*`, `train_*`) | ✅ |
| R-06 | dbt con staging, intermediate, marts y tests | `infra/dbt/models/`, `infra/dbt/tests/` | ✅ |
| R-07 | MLflow para experimentos y artefactos | [mlflow-dbt-pipeline.md](../mlops/mlflow-dbt-pipeline.md) + `infra/pipelines/` | ✅ |
| R-08 | JupyterLab con pandas/sklearn/xgboost/PySpark | `infra/jupyter/work/01_eda_orders.ipynb` | ✅ |
| R-09 | BI en Metabase/Superset con métricas de negocio | Servicios 8-9 + [runbook.md](../operations/runbook.md) | ✅ |
| R-10 | Ningún `.md` supera 200 líneas | Todos ≤ 176 (verificado por conteo real) | ✅ |
| R-11 | Lo que supere 180 líneas se poda y desglosa en `/docs` | `runbook.md` y `memory-persistence.md` creados por esa regla | ✅ |
| R-12 | 100 % de la información conservada con enlaces cruzados e índice | [README.md](../../README.md) §4 ≡ archivos reales (0 huérfanos, 0 rotos) | ✅ |
| R-13 | Markdown limpio con tablas, listas y código | 10 documentos + 4 diagramas Mermaid | ✅ |
| R-14 | 7 agentes con Rol/Entradas/Salidas/Herramientas | [AGENTS.md](../../AGENTS.md) §2 (7 fichas con DoD) | ✅ |
| R-15 | Diagrama Mermaid de arquitectura en `README.md` | [README.md](../../README.md) §3 | ✅ |
| R-16 | Diagrama Mermaid de secuencia en `AGENTS.md` | [AGENTS.md](../../AGENTS.md) §3 | ✅ |
| R-17 | Diagrama Mermaid de estado/ciclo de vida en `MEMORY.md` | [MEMORY.md](../../MEMORY.md) §4 | ✅ |
| R-18 | Memoria corto plazo vs. largo plazo + JSON de estado | [MEMORY.md](../../MEMORY.md) §1-§5 | ✅ |
| R-19 | Persistencia, volúmenes Docker y retención | [MEMORY.md](../../MEMORY.md) §6 + [memory-persistence.md](../memory/memory-persistence.md) | ✅ |
| R-20 | 5 módulos de `/docs` exigidos | `architecture/`, `infrastructure/`, `agents/` (×2), `mlops/` | ✅ |
| R-21 | Algoritmos de ruteo y reglas de negocio | [orchestration-rules.md](../agents/orchestration-rules.md) §3-§6 | ✅ |
| R-22 | Guía extendida por agente con comandos/scripts | [specialists-deep-dive.md](../agents/specialists-deep-dive.md) §1-§8 | ✅ |
| R-23 | Integración dbt ↔ MLflow | [mlflow-dbt-pipeline.md](../mlops/mlflow-dbt-pipeline.md) §1-§6 | ✅ |
| R-24 | Entrega en bloques de código etiquetados | Sustituido por archivos reales (justificado en [prompt-log.md](prompt-log.md) `P-002`) | 🔁 |

## 4. Criterios de aceptación verificables

1. **Ejecutabilidad**: `docker compose up -d` arranca el stack sin rutas inexistentes (todo bind-mount existe).
2. **Trazabilidad**: un `run_id` une Airflow → dbt (`manifest.json`) → MLflow → tabla de *scoring* → dashboard.
3. **Modularidad**: ningún `.md` > 200 líneas y ningún enlace relativo roto.
4. **Honestidad técnica**: toda limitación no verificada (Docker apagado, `_path` de ClickHouse, Mermaid sin parser)
   queda declarada por escrito en el propio repositorio.

## 5. Navegación

| Documento | Contenido |
|---|---|
| [prompt-log.md](prompt-log.md) | Bitácora viva de peticiones `P-00N` y su estado |
| [README.md](../../README.md) | Índice maestro y arquitectura |
| [AGENTS.md](../../AGENTS.md) | Protocolo multi-agente que ejecuta estos requisitos |
| [glossary.md](../glossary.md) | Significado de las siglas usadas en el propio prompt (OLTP, ELT, dbt, MLOps) |
