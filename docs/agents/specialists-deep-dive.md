# Specialists Deep Dive — Guía Técnica por Agente

> Módulo de agentes del [AGENTS.md](../../AGENTS.md). Para cada especialista: **responsabilidades,
> comandos exactos, artefactos que produce y criterios de aceptación**.
> Reglas de ruteo que los activan: [orchestration-rules.md](orchestration-rules.md).

## 1. `orchestrator` — Orchestrator & Workflow Agent

```bash
python -m agents.orchestrator run --intent "revenue_by_category_and_churn" --budget 30m
python -m agents.orchestrator plan --show-dod          # imprime plan.json con criterios
python -m agents.orchestrator resume --run-id "$RUN_ID" --from-checkpoint
```

| Produce | Verifica | Criterio de aceptación |
|---|---|---|
| `plan.json`, `run_id`, resumen ejecutivo | Estado del stack y frescura | Cada paso con dueño, entrada, salida y DoD |

Regla dura: si una intención obtiene `score < 0.55`, **pregunta** en lugar de asumir (ver §3 del módulo de ruteo).

## 2. `platform` — Data Platform & Infrastructure Agent

```bash
docker compose up -d && docker compose ps --format 'table {{.Name}}\t{{.Status}}'
docker compose exec minio mc mb -p local/datalake/{bronze,silver,gold,mlflow}
docker compose exec minio mc admin info local
curl -s 'http://localhost:8123/?query=SELECT%20version()'
psql "$DSN_OLTP" -c '\d+ public.orders'
```

| Produce | Verifica | Criterio de aceptación |
|---|---|---|
| Stack *healthy*, buckets, DSN efímeros | 9 healthchecks + conectividad | 9/9 en verde y smoke test del README OK |

Credenciales efímeras: usuario de solo lectura en OLTP y *access key* temporal de MinIO por `run_id`.

## 3. `data_engineer` — Data Engineer Agent

```bash
airflow dags list | grep ingest_
airflow dags trigger ingest_oltp_to_bronze --conf '{"entities":["orders","customers"],"mode":"incremental"}'
airflow tasks test ingest_oltp_to_bronze extract_orders 2026-02-14
docker compose exec minio mc ls --recursive local/datalake/bronze/orders/ | tail -5
```

```sql
-- Cuadre obligatorio antes del handoff
SELECT (SELECT count(*) FROM public.orders WHERE updated_at > :wm) AS origen,
       (SELECT sum(rows_read) FROM datalab_meta.ingest_audit WHERE run_id = :run_id) AS destino;
```

| Produce | Verifica | Criterio de aceptación |
|---|---|---|
| Parquet Bronze particionado + `ingest_audit` | `origen == destino` por partición | DAG en verde y *watermark* avanzado |

## 4. `analytics_engineer` — Analytics Engineer Agent

```bash
dbt deps && dbt build --select staging --target dev
dbt build --select intermediate marts --target dev --fail-fast
dbt test --select marts.fct_orders --store-failures
dbt docs generate && dbt docs serve --port 8082
dbt ls --select marts --output json > /tmp/marts.json
```

```sql
-- Test singular de volumen (tests/anomaly_volume.sql, vía test-paths)
SELECT order_date, count(*) AS filas
FROM {{ ref('fct_orders') }}
GROUP BY 1
HAVING count(*) < 0.8 * (SELECT avg(c) FROM (SELECT count(*) c FROM {{ ref('fct_orders') }}
                                             GROUP BY order_date))
```

| Produce | Verifica | Criterio de aceptación |
|---|---|---|
| `dim_*`/`fct_*` en ClickHouse, `manifest.json`, docs | Unicidad, FK, rango, frescura | `dbt build` sin `error` y granularidad declarada |

## 5. `ds_mlops` — Data Science & MLOps Agent

```bash
jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --NotebookApp.token="$JUPYTER_TOKEN"
python pipelines/train_churn.py --run-id "$RUN_ID" --features marts.customer_features --algo xgboost
mlflow models serve -m "models:/churn_classifier/Production" -p 5001 --no-conda
mlflow runs list --experiment-id 3 --order-by "metrics.roc_auc DESC"
```

```python
import mlflow, mlflow.sklearn
with mlflow.start_run(run_name=f"churn_{run_id}", tags={"run_id": run_id, "dbt_manifest": manifest_hash}):
    mlflow.log_params({"algo": "xgboost", "n_estimators": 400, "max_depth": 5})
    mlflow.log_metrics({"roc_auc": auc, "pr_auc": pr_auc, "brier": brier})
    mlflow.sklearn.log_model(model, "model", signature=signature,
                             registered_model_name="churn_classifier")
```

| Produce | Verifica | Criterio de aceptación |
|---|---|---|
| `model_uri`, métricas, tabla de *scoring*, model card | Métrica vs. baseline (IC 95 %) | Supera baseline y queda registrado con firma |

## 6. `bi_viz` — BI & Data Visualization Agent

```bash
curl -s -X POST http://localhost:3000/api/session -H 'Content-Type: application/json' \
  -d '{"username":"admin@datalab.local","password":"'"$METABASE_PWD"'"}' | jq -r .id
curl -s -X POST http://localhost:3000/api/card -H "X-Metabase-Session: $MB_TOKEN" \
  -H 'Content-Type: application/json' -d @dashboards/revenue_by_category.json
superset import-dashboards -p dashboards/revenue.zip -u admin
```

| Produce | Verifica | Criterio de aceptación |
|---|---|---|
| Dashboard publicado, `metrics.yml`, alertas | Reproducibilidad SQL del KPI | Todo KPI con definición, dueño y fuente |

## 7. `governance` — Governance & QA Agent

```bash
dbt test --select tag:critical --store-failures      # quality gate duro
dbt ls --resource-type test --output json | jq 'length'
python -m qa.contract_check --run-id "$RUN_ID" --contracts contracts/
python -m qa.drift_report --model churn_classifier --reference gold.customer_features --current gold.customer_features_recent
python -m qa.bias_audit --model churn_classifier --sensitive gender,age_band --metric demographic_parity
```

| Produce | Verifica | Criterio de aceptación |
|---|---|---|
| Reporte de calidad, *quality gate*, alertas de drift/sesgo | Contratos + PSI + paridad demográfica | Cero tests críticos fallidos; PSI < 0.2 |

Umbrales: PSI < 0.1 estable · 0.1–0.2 vigilar · > 0.2 congelar *scoring* y marcar el dashboard como no certificado.

## 8. Contratos compartidos entre agentes

| Contrato | Definido en | Validado por |
|---|---|---|
| `handoff.schema.json` | [orchestration-rules.md §5](orchestration-rules.md) | `orchestrator` |
| `contracts/*.yml` (datos) | `analytics_engineer` | `governance` |
| Firma y versión de modelo | `ds_mlops` | `governance` |
| `metrics.yml` (KPI certificados) | `bi_viz` | `governance` |

## 9. Navegación

| Documento | Contenido |
|---|---|
| [orchestration-rules.md](orchestration-rules.md) | Ruteo, precondiciones y guardrails |
| [mlflow-dbt-pipeline.md](../mlops/mlflow-dbt-pipeline.md) | Del mart Gold al modelo en `Production` |
| [AGENTS.md](../../AGENTS.md) | Catálogo, secuencia y protocolos de error |
| [glossary.md](../glossary.md) | Siglas de los comandos (DAG, dbt, MLflow, PSI, SK/BK) |
