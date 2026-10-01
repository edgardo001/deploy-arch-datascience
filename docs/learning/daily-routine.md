# Rutina Diaria — Cómo Se Trabaja Este Entorno

> No basta con conocer el ecosistema: hay que saber **moverse** en él. Aquí está el ritmo diario, lo que
> normalmente te solicitan, cómo se prioriza y cómo se cierra una tarea con evidencia.
> Backlog diario: [daily-tasks.md](daily-tasks.md) · Módulos: [curriculum.md](curriculum.md) · Rutas: [README.md](README.md).

## 1. El día en tres bloques

| Bloque | Duración | Qué haces | Señal de alarma |
|---|---|---|---|
| **Apertura** | 15 min | Revisar salud, frescura y fallos de la noche | Cualquier servicio no *healthy* o partición sin datos de ayer |
| **Producción** | 5-6 h | Atender 1-3 solicitudes del catálogo (§3) con evidencia | Petición sin definición de KPI ni dueño |
| **Cierre** | 15 min | Registrar evidencia, responder al solicitante, dejar el entorno limpio | Tarea cerrada sin número ni enlace |

## 2. Ritual de apertura (ejecutable)

```bash
docker compose ps                                    # 9/9 healthy
docker compose exec airflow airflow dags list-runs -d ingest_oltp_to_bronze | head -5
docker compose exec oltp-postgres psql -U datalab -d datalab_meta -c \
"SELECT entity, max(dt) AS ultima, sum(rows_read) FROM meta.ingest_audit GROUP BY entity;"
docker compose exec clickhouse clickhouse-client --database marts --query \
"SELECT max(order_date) AS ultimo_dia, count() FROM marts.fct_orders"
```

**Criterio de apertura**: si la última partición no es la de ayer o el conteo cae >20 % respecto a la media,
se atiende **antes** de cualquier petición nueva (es una incidencia, no un ticket).

## 3. Catálogo de solicitudes comunes del área

| Solicitud típica | Quién la pide | Urgencia | Agente | Entregable | Cómo se mide el éxito |
|---|---|---|---|---|---|
| «El dashboard no cuadra con el ERP» | Finanzas | Alta | `analytics_engineer` | Conciliación con causa raíz | Diferencia explicada, no "ajustada" |
| «No veo la venta de ayer» | Comercial | Alta | `data_engineer` | Particiación cargada + frescura | Datos de ayer visibles en Gold |
| «El pipeline falló anoche» | Operación | Crítica | `platform` | DAG en verde + incidente | Causa raíz documentada |
| «Reprocesa el lunes» | Analista | Media | `data_engineer` | Partición reescrita | Mismo `run_id`, sin duplicados |
| «¿Por qué este pedido sale dos veces?» | Comercial | Media | `analytics_engineer` | Diagnóstico de granularidad | Duplicado eliminado en el modelo, no en el informe |
| «Agrega margen al reporte» | Dirección | Media | `analytics_engineer` | Columna nueva + test | Métrica con definición y dueño |
| «El total de clientes no coincide» | Marketing | Media | `analytics_engineer` | Explicación SCD2 | Versiones vs. clientes distintos aclarado |
| «Un test está en rojo» | QA | Alta | `governance` | Test corregido o dato arreglado | Gold bloqueado hasta resolver |
| «Cambió la definición de cliente activo» | Negocio | Media | `analytics_engineer` + `governance` | Contrato y KPI actualizados | Todos los consumidores avisados |
| «Esta consulta tarda 40 s» | BI | Media | `analytics_engineer` | Consulta optimizada | <5 s con el mismo resultado |
| «El modelo predice peor que antes» | Negocio | Alta | `ds_mlops` + `governance` | Informe de drift | PSI y métricas comparadas |
| «Necesito el scoring de hoy» | Marketing | Alta | `ds_mlops` | Tabla `scoring_dt=` | Predicciones disponibles antes de las 8:00 |
| «¿Por qué este cliente es churn?» | Atención al cliente | Baja | `ds_mlops` | Explicación de *features* | Factores citados y comprensibles |
| «Quiero un KPI nuevo» | Dirección | Media | `bi_viz` | Dashboard + SQL reproducible | Cualquiera lo reproduce pegando SQL |
| «El dashboard tarda en abrir» | Dirección | Media | `bi_viz` + `analytics_engineer` | Modelo o consulta optimizados | Carga <3 s |
| «Auditoría: ¿de dónde sale este número?» | Auditoría | Alta | `governance` | Linaje columna a columna | Ruta OLTP → dashboard documentada |
| «¿El modelo es justo?» | Compliance | Alta | `governance` | Informe de sesgo | Paridad por grupo con umbral declarado |
| «Documenta este dataset» | Equipo | Baja | `analytics_engineer` | Contrato + descripción | Publicado en dbt docs y catálogo |
| «Informe mensual para dirección» | Dirección | Media | `bi_viz` + `orchestrator` | 1 página + enlaces | 3 mensajes, 3 números, 1 recomendación |
| «Propón una mejora» | Arquitectura | Baja | `platform` | ADR o petición `P-00N` | Justificada con «cuándo NO» |

## 4. Priorización

| | Impacto alto | Impacto bajo |
|---|---|---|
| **Urgencia alta** | Se atiende ya: incidencias de frescura, cifras que dirección está mirando | Se automatiza o se agenda: consultas repetidas, permisos |
| **Urgencia baja** | Se planifica: nuevos KPI, mejoras de modelo, documentación | Se delega o se rechaza con justificación escrita |

Reglas de convivencia: **una** tarea crítica a la vez · nada se cierra sin número · si una petición no tiene
dueño ni definición, se devuelve con 2 preguntas concretas antes de empezar.

## 5. Cierre del día

1. **Evidencia**: comando ejecutado y salida (o artefacto: tabla, dashboard, modelo).
2. **Respuesta al solicitante** en 3 líneas: *número* + *causa* (si hubo) + *qué sigue*.
3. **Registro**: fila en `meta.session_events` o en el `learning-log`, con la tarea `T-0NN` y su enlace.
4. **Entorno limpio**: sin ficheros temporales, sin tests modificados "a mano", sin contenedores huérfanos.

## 6. Errores típicos de un perfil junior

1. **Arreglar el informe en lugar del modelo**: el número se corrige aguas arriba, nunca en el BI.
2. **Mirar Bronze para responder a negocio**: se responde con marts y se documenta la fuente.
3. **Sumar importes sin revisar granularidad**: el doble conteo es el error más frecuente y más caro.
4. **Cerrar sin evidencia**: "ya está" no es una entrega; vale la salida del comando.
5. **Tocar producción sin avisar**: si algo afecta a un KPI certificado, se comunica antes y después.

## 7. Navegación

| Documento | Contenido |
|---|---|
| [daily-tasks.md](daily-tasks.md) | Backlog `T-01`…`T-20` para cuatro semanas de trabajo |
| [curriculum.md](curriculum.md) | Módulos `M0`…`M8` que dan la base de cada tarea |
| [runbook.md](../operations/runbook.md) | Comandos de operación y diagnóstico de fallos |
| [FAQ.md](../../FAQ.md) | Dudas breves del día a día con enlace a la sección que responde |
