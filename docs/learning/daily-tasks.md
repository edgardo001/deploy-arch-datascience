# Tareas Diarias `T-01`…`T-20` — Cuatro Semanas de Trabajo Real

> Backlog de la [rutina diaria](daily-routine.md): una tarea por día laborable, enunciada **como te la pide un
> solicitante** y resuelta con comandos de este entorno. Base teórica: [curriculum.md](curriculum.md) ·
> Práctica: [exercises-labs.md](exercises-labs.md). Cierre obligatorio: número + causa + siguiente paso.

## Cómo se usan

1. Una `T-0NN` por día, en orden; si sobra tiempo, se repite con otro filtro (otro mes, otra categoría, otro canal).
2. Cada tarea se cierra con **evidencia ejecutada** y una fila en `meta.session_events`:

```bash
docker compose exec oltp-postgres psql -U datalab -d datalab_meta -c \
"INSERT INTO meta.session_events (session_id, kind, payload)
 VALUES ('dia-2026-10-01','decision','{\"tarea\":\"T-01\",\"resultado\":\"diferencia 1,8% por cancelados\"}'::jsonb);"
```

3. Si una tarea revela un problema de documentación, se añade una fila al [FAQ.md](../../FAQ.md).

| Semana | Foco | Tareas | Módulos |
|---|---|---|---|
| 1 | Operación y datos | `T-01`…`T-05` | `M0`-`M2` |
| 2 | Modelado y calidad | `T-06`…`T-10` | `M3`-`M5` |
| 3 | Machine learning y BI | `T-11`…`T-15` | `M6`-`M7` |
| 4 | Gobierno y comunicación | `T-16`…`T-20` | `M8` |

## Semana 1 · Operación y datos

### `T-01` · «El dashboard no cuadra con el ERP» — `analytics_engineer` · 30 min
**Te piden**: explicar la diferencia de ingresos del día anterior, sin "ajustarla".
**Cómo**: `psql -c "SELECT sum(total_amount) FROM orders WHERE order_date = current_date-1 AND status NOT IN ('cancelled','refunded')"` frente a `fct_orders` del mismo día.
**Cierre**: respuesta con número, causa (estados o granularidad) y acción propuesta.
**Base**: `M4`, `L-09` · **Riesgo**: reportar ingresos inflados.

### `T-02` · «No veo la venta de ayer» — `data_engineer` · 30 min
**Te piden**: que los datos de ayer estén disponibles ya.
**Cómo**: revisar `meta.ingest_audit` para `dt=ayer`, lanzar `airflow dags trigger ingest_oltp_to_bronze` y refrescar Gold.
**Cierre**: frescura verificada con `SELECT max(order_date) FROM marts.fct_orders`.
**Base**: `M2`, `L-05` · **Riesgo**: cargar dos veces la misma partición.

### `T-03` · «El pipeline falló anoche» — `platform` · 45 min
**Te piden**: diagnóstico y arreglo de la incidencia.
**Cómo**: `airflow dags list-runs -d ingest_oltp_to_bronze --state failed`, leer el log de la tarea, `airflow tasks test` para reproducir y `airflow tasks clear -y` para reintentar.
**Cierre**: DAG en verde + causa raíz y prevención.
**Base**: `M5` · **Riesgo**: reintentar sin entender el fallo y duplicar datos.

### `T-04` · «Reprocesa el lunes» — `data_engineer` · 30 min
**Te piden**: rehacer la carga de un día concreto.
**Cómo**: mover el *watermark* y reejecutar el DAG con la fecha objetivo; verificar la partición del lake con `docker compose run --rm minio-init 'aws --endpoint-url http://minio:9000 --region us-east-1 s3 ls --recursive s3://datalake/bronze/orders/'`.
**Cierre**: mismos conteos, sin filas duplicadas ni huérfanas.
**Base**: `M2`, `D-10` · **Riesgo**: refresco completo innecesario.

### `T-05` · «¿Por qué este pedido aparece dos veces?» — `analytics_engineer` · 40 min
**Te piden**: eliminar el duplicado en el informe.
**Cómo**: buscar el pedido en Bronze y en `fct_orders`, revisar la clave (`order_id` + `product_id`) y el `unique_key` del incremental.
**Cierre**: duplicado corregido **en el modelo**, y test que lo impida en el futuro.
**Base**: `M3`, `L-08` · **Riesgo**: filtrar el duplicado en el dashboard y tapar el problema.

## Semana 2 · Modelado y calidad

### `T-06` · «Agrega el margen al reporte» — `analytics_engineer` · 60 min
**Te piden**: una columna nueva de margen por línea.
**Cómo**: añadir el cálculo en el modelo, documentarlo y cubrirlo con un test `accepted_range`.
**Cierre**: columna disponible en Gold con definición y dueño.
**Base**: `M3`-`M4` · **Riesgo**: importe sin coste asociado → margen ficticio.

### `T-07` · «El total de clientes no coincide» — `analytics_engineer` · 40 min
**Te piden**: aclarar por qué hay más filas que clientes.
**Cómo**: `count()` vs `uniqExact(customer_id)` vs `countIf(is_current)` en `dim_customer`.
**Cierre**: explicación de SCD2 y de por qué los hechos usan `customer_sk`.
**Base**: `M4`, `L-10` · **Riesgo**: contar versiones históricas como clientes distintos.

### `T-08` · «Un test está en rojo» — `governance` · 45 min
**Te piden**: dejarlo en verde sin romper Gold.
**Cómo**: `dbt test --select tag:critical --store-failures`, inspeccionar las filas fallidas y corregir aguas arriba.
**Cierre**: gate aprobado y registro en `meta.quality_gates`.
**Base**: `M5`, `L-11` · **Riesgo**: relajar el test para que pase.

### `T-09` · «Cambió la definición de cliente activo» — `analytics_engineer` + `governance` · 60 min
**Te piden**: aplicar la nueva definición en todo el reporting.
**Cómo**: actualizar el modelo y el contrato, `dbt ls --resource-type exposure` para localizar consumidores y avisar.
**Cierre**: una sola definición vigente en todos los dashboards.
**Base**: `M5`, `D-18` · **Riesgo**: dos verdades distintas en dos paneles.

### `T-10` · «Esta consulta tarda 40 segundos» — `analytics_engineer` · 45 min
**Te piden**: bajarla a menos de 5 s con el mismo resultado.
**Cómo**: `EXPLAIN` en ClickHouse, revisar `order_by` del modelo, evitar `JOIN` innecesario y pre-agregar en un mart.
**Cierre**: consulta optimizada y medición antes/después.
**Base**: `M4`, `D-11` · **Riesgo**: cachear en el BI y falsear la mejora.

## Semana 3 · Machine learning y BI

### `T-11` · «El modelo predice peor que antes» — `ds_mlops` + `governance` · 60 min
**Te piden**: explicar la degradación y proponer acción.
**Cómo**: `python /opt/airflow/qa/drift_report.py` y comparación de métricas en MLflow entre versiones.
**Cierre**: informe con PSI por *feature* y decisión (reentrenar o congelar).
**Base**: `M6`, `L-13` · **Riesgo**: reentrenar sin diagnosticar la causa.

### `T-12` · «Necesito el scoring de hoy» — `ds_mlops` · 30 min
**Te piden**: predicciones listas para marketing antes de las 8:00.
**Cómo**: `python /opt/airflow/pipelines/score.py --model churn_classifier --stage Production --dt $(date +%F)`.
**Cierre**: partición `scoring_dt=` publicada y filas cuadradas con la tabla de features.
**Base**: `M6` · **Riesgo**: puntuar con un modelo en `Staging`.

### `T-13` · «¿Por qué este cliente es churn?» — `ds_mlops` · 30 min
**Te piden**: una explicación entendible para atención al cliente.
**Cómo**: obtener las *features* del cliente y las importancias del modelo; traducir a lenguaje natural.
**Cierre**: 3 factores explicados sin jerga.
**Base**: `M6` · **Riesgo**: presentar una probabilidad sin contexto.

### `T-14` · «Quiero un KPI nuevo» — `bi_viz` · 60 min
**Te piden**: ticket medio por canal, con dueño y definición.
**Cómo**: escribir el SQL en `marts`, validar contra `fct_orders` y publicarlo en Metabase/Superset.
**Cierre**: KPI reproducible pegando el SQL documentado.
**Base**: `M7`, `L-14` · **Riesgo**: KPI sin definición → dos versiones del número.

### `T-15` · «El dashboard tarda en abrir» — `bi_viz` + `analytics_engineer` · 45 min
**Te piden**: carga en menos de 3 s.
**Cómo**: identificar la consulta pesada, materializar un agregado en Gold y reducir columnas/filtros.
**Cierre**: medición antes/después y origen del dato documentado.
**Base**: `M7`, `D-11` · **Riesgo**: limitar filas y perder historia.

## Semana 4 · Gobierno y comunicación

### `T-16` · «Auditoría: ¿de dónde sale este número?» — `governance` · 45 min
**Te piden**: la trazabilidad completa de un KPI.
**Cómo**: recorrer `run_id` → `manifest.json` → modelo → tabla → dashboard, con `meta.handoffs` como hilo.
**Cierre**: ruta documentada desde el OLTP hasta el panel.
**Base**: `M8`, `Q-19` · **Riesgo**: respuestas sin evidencia verificable.

### `T-17` · «¿El modelo es justo?» — `governance` · 45 min
**Te piden**: revisar sesgo por género y franja de edad.
**Cómo**: `python /opt/airflow/qa/bias_audit.py --sensitive gender,age_band`.
**Cierre**: informe con paridad por grupo y severidad.
**Base**: `M8` · **Riesgo**: medir solo la métrica global.

### `T-18` · «Documenta este dataset» — `analytics_engineer` · 45 min
**Te piden**: que el equipo entienda qué contiene y quién responde.
**Cómo**: descripciones y tests en `_marts.yml`, contrato en `infra/contracts/marts.yml`, `dbt docs generate`.
**Cierre**: dataset con dueño, granularidad y SLA publicados.
**Base**: `M8`, `D-18` · **Riesgo**: documentación que no se valida automáticamente.

### `T-19` · «Informe mensual para dirección» — `bi_viz` + `orchestrator` · 60 min
**Te piden**: una página con lo esencial del mes.
**Cómo**: 3 números (ingresos, margen, churn) con enlace a su dashboard y una recomendación accionable.
**Cierre**: 3 mensajes, 3 cifras y 1 recomendación; sin jerga técnica.
**Base**: `M7`-`M8` · **Riesgo**: volcar 20 gráficos sin conclusión.

### `T-20` · «Propón una mejora al pipeline» — `platform` · 60 min
**Te piden**: una propuesta justificada, no una opinión.
**Cómo**: redactar una decisión `D-0NN` con contexto, alternativas, pros, contras y **«cuándo NO»**; o una petición `P-00N`.
**Cierre**: propuesta registrada y enlazada, con coste de reversión declarado.
**Base**: `M8`, `D-19` pendiente · **Riesgo**: proponer herramienta nueva sin retirar nada.

## Navegación

| Documento | Contenido |
|---|---|
| [daily-routine.md](daily-routine.md) | Ritmo del día, catálogo de solicitudes y priorización |
| [curriculum.md](curriculum.md) | Módulos que dan la base de cada tarea |
| [decisions/README.md](../decisions/README.md) | Formato de decisión usado en `T-20` |
| [prompt-log.md](../prompts/prompt-log.md) | Cómo se registra una propuesta como `P-00N` |
