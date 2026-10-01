# Orchestration Rules — Ruteo, Transferencias y Guardrails

> Módulo de agentes del [AGENTS.md](../../AGENTS.md). Define **cómo el Orchestrator decide quién hace qué**,
> con qué contrato se transfiere el trabajo y qué ocurre cuando algo falla.
> Comandos por agente: [specialists-deep-dive.md](specialists-deep-dive.md).

## 1. Modelo de decisión

El ruteo es una función determinista sobre tres entradas, no una decisión libre del modelo:

```text
route(intent, context, constraints) -> plan{ steps[], owners[], gates[] }
```

1. **Intención**: qué pide el usuario (clasificada en la taxonomía de la §2).
2. **Contexto**: estado del stack, frescura de los datos, `run_id` previo, memoria recuperada.
3. **Restricciones**: presupuesto de cómputo, ventana temporal, criticidad del KPI, permisos.

## 2. Taxonomía de intenciones

| Intención | Señales léxicas | Agente primario | Gate obligatorio |
|---|---|---|---|
| `stack_ops` | levantar, reparar, puerto, contenedor, bug de entorno | `platform` | Healthchecks 9/9 + `dbt build` OK |
| `ingestion` | traer, actualizar, sincronizar, fuente, OLTP | `data_engineer` | Cuadre de conteos |
| `modeling` | KPI, tabla, dimensión, métrica, join | `analytics_engineer` | `dbt build` verde |
| `science` | predecir, entrenar, modelo, churn, accuracy | `ds_mlops` | Métrica > baseline |
| `visualization` | dashboard, gráfico, reporte, panel | `bi_viz` | KPI reproducible |
| `assurance` | calidad, linaje, sesgo, drift, auditoría | `governance` | Quality gate emitido |
| `ambiguous` | sin señal clara o multi-dominio | `orchestrator` | Plan explícito aprobado |

## 3. Algoritmo de ruteo

```python
def route(intent, context, constraints):
    candidates = score_agents(intent, context)          # §4
    if candidates[0].score < 0.55:
        return clarify(intent)                          # pregunta al usuario, no adivina
    plan = build_plan(candidates[0])                    # grafo de pasos + dependencias
    plan.steps = order_by_dependency(plan.steps)        # topológico, nunca por "urgencia"
    plan.gates = [gate_for(step) for step in plan.steps if step.requires_gate]
    if plan.cost > constraints.budget:
        plan = degrade(plan, mode="sample_10pct")       # degradación explícita y visible
    return plan.with_run_id(new_run_id())
```

## 4. Scoring y desambiguación

```text
score = 0.45 * match_intent + 0.25 * data_availability
      + 0.15 * (1 - cost_penalty) + 0.15 * success_history
```

| Regla | Descripción |
|---|---|
| Empate técnico (Δ < 0.05) | Gana el agente con menor coste estimado |
| Falta de datos | Si el mart requerido no existe, se antepone `data_engineer`/`analytics_engineer` |
| Conflicto de dominio | Desempata `governance` por riesgo regulatorio |
| Intención desconocida | `orchestrator` pregunta con opciones concretas (máx. 1 ronda) |

## 5. Condiciones de transferencia (*handoff*)

Un *handoff* solo es válido si cumple el contrato siguiente; si no, se rechaza y se re-solicita.

```json
{
  "run_id": "run_2026-02-14T09-30-12Z_a13f",
  "from": "data_engineer",
  "to": "analytics_engineer",
  "intent": "modeling",
  "status": "ok",
  "artifacts": [
    "s3://datalake/bronze/orders/dt=2026-02-14/part-000.parquet",
    "s3://datalake/silver/orders/dt=2026-02-14/"
  ],
  "contracts": { "rows_in": 148233, "rows_out": 148233, "schema_version": "v3" },
  "preconditions_met": ["bronze_complete", "schema_validated"],
  "metrics": { "duration_s": 118, "retries": 0 },
  "next_agent": "analytics_engineer",
  "ts": "2026-02-14T09:32:10Z"
}
```

| Precondición | Verificada por | Bloquea si… |
|---|---|---|
| `stack_healthy` | `platform` | Algún healthcheck en rojo |
| `data_freshness` | `data_engineer` | Último `dt=` > 24 h |
| `schema_compatible` | `governance` | Cambio incompatible sin versionar |
| `tests_passed` | `analytics_engineer` | Cualquier test `error` de dbt |
| `budget_available` | `orchestrator` | Coste estimado > presupuesto |

## 6. Guardrails de negocio

1. **Nunca** escribir en el OLTP; solo lectura con usuario de solo consulta.
2. **Ningún** dashboard puede publicarse sin quality gate firmado por `governance`.
3. Datos personales: se enmascaran en Silver (`email_hash`, `phone_masked`); Bronze ya llega seudonimizado.
4. Todo modelo en `Production` requiere firma de modelo, versión y *dataset* de referencia registrados.
5. Cambios de esquema en marts exigen bump de versión y aviso a consumidores (`exposures` de dbt).
6. Las decisiones del usuario se preservan en `decision_log` y no se reinterpretan en pasos posteriores.
7. Antes de planificar, toda petición del usuario abre una entrada `P-00N` en la bitácora
   [docs/prompts/prompt-log.md](../prompts/prompt-log.md) con su interpretación; al cerrar, se añade el resultado.

## 7. Reintentos, backoff y cortacircuitos

| Situación | Política |
|---|---|
| Error transitorio de red | 3 reintentos, backoff exponencial 2 s → 8 s → 32 s con jitter |
| Falla de test de datos | **Sin** reintento automático: requiere corrección de causa raíz |
| Servicio `unhealthy` | 2 recreaciones de contenedor; después escala al usuario |
| Circuito abierto | Tras 3 fallos del mismo agente en 30 min, se desvía a `orchestrator` |
| Timeout de paso | 2× la duración media histórica del paso en ese DAG |

## 8. Observabilidad del ruteo

- Cada decisión se registra en `datalab_meta.routing_decisions` (intención, *score*, agentes, desempate).
- El `run_id` es la clave foránea entre Airflow, MLflow y el metadata store.
- Métricas de plataforma: *tasa de acierto del router* (sin re-ruteo), *reintentos por paso*, *latencia p95*.
- Derivas del router (misma intención ruteada distinto) generan un hallazgo de `governance`.

## 9. Navegación

| Documento | Contenido |
|---|---|
| [specialists-deep-dive.md](specialists-deep-dive.md) | Comandos y contratos por agente |
| [AGENTS.md](../../AGENTS.md) | Catálogo de los 7 agentes y matriz de delegación |
| [MEMORY.md](../../MEMORY.md) | Estado que el router consulta antes de decidir |
| [data-pipeline.md](../architecture/data-pipeline.md) | Pasos técnicos que el plan dispara |
| [glossary.md](../glossary.md) | Siglas de ruteo y calidad (`P-00N`, DoD, quality gate, PSI) |
