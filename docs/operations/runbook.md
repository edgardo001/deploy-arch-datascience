# Runbook Operativo — Operación Diaria, Reglas y Troubleshooting

> Módulo desglosado del [README.md](../../README.md) y de [docker-setup.md](../infrastructure/docker-setup.md)
> para mantener ambos por debajo de 180 líneas. Reúne los comandos del día a día, las reglas de oro del
> repositorio, el diagnóstico de fallos y los *playbooks* de recuperación.

## 1. Operación diaria

| Tarea | Comando |
|---|---|
| Ver estado y salud | `docker compose ps` |
| Seguir logs de orquestación | `docker compose logs -f --tail=100 airflow` |
| Reiniciar un servicio | `docker compose restart clickhouse` |
| Consultar el OLTP | `docker compose exec oltp-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_OLTP_DB" -c '\dt'` |
| Inspeccionar el Data Lake | `docker compose run --rm minio-init 'aws --endpoint-url http://minio:9000 --region us-east-1 s3 ls --recursive s3://datalake/bronze/ \| tail -5'` |
| Reconstruir marts | `docker compose --profile transform run --rm dbt build --select marts` |
| Detener conservando datos | `docker compose down` |
| Borrar todo el estado | `docker compose down -v` (**destructivo**: elimina volúmenes) |

```bash
# Secuencia de arranque recomendada
cp .env.example .env
docker compose up -d --build
docker compose ps                       # esperar 9/9 healthy (dbt es efímero)
docker compose up -d minio-init         # bucket datalake (prefijos bronze/silver/gold/mlflow)
docker compose exec airflow airflow dags list
```

## 2. Ciclo de trabajo con agentes

1. El usuario formula una petición de negocio al **Orchestrator** ([AGENTS.md](../../AGENTS.md)).
2. El Orchestrator resuelve intención → plan → agentes responsables ([reglas de ruteo](../agents/orchestration-rules.md)).
3. Cada agente ejecuta su tramo y devuelve un *handoff* tipado con `run_id`, artefactos y estado.
4. **Governance & QA** valida contratos, sesgo y *data drift* antes de publicar.
5. El resultado se publica en BI y se consolida en la memoria de largo plazo ([MEMORY.md](../../MEMORY.md)).

## 3. Reglas de oro del repositorio

- Un `.md` = un tema; **máximo 200 líneas** y objetivo ≤ 180. Lo que exceda se desglosa en `/docs` (como este runbook).
- Todo enlace entre documentos es **relativo** y bidireccional cuando aplica.
- Los ejemplos de estado, esquemas y contratos viven en el documento del módulo, no duplicados en el README.
- Las credenciales nunca se commitean: solo `.env.example` con valores de relleno.
- Ningún agente escribe en territorio de otro sin un *handoff* válido ([contrato](../agents/orchestration-rules.md)).

## 4. Troubleshooting consolidado

| Síntoma | Causa probable | Acción |
|---|---|---|
| `airflow` en `unhealthy` | `AIRFLOW_UID` sin definir o logs sin permisos | `echo "AIRFLOW_UID=$(id -u)" >> .env` y `docker compose up -d --force-recreate airflow` |
| dbt: `Database Error: Connection refused` | Perfil apuntando a `localhost` dentro de la red Docker | Usar nombre de servicio (`clickhouse`, `minio`) como host |
| MLflow sin artefactos | Falta `MLFLOW_S3_ENDPOINT_URL` o credenciales S3 | Definir `MLFLOW_S3_ENDPOINT_URL=http://minio:9000` y `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` con `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD` |
| Lake responde 403 en S3 | Credenciales desalineadas o bucket inexistente | Reejecutar `docker compose up -d minio-init` (AWS CLI contra `http://minio:9000`) |
| ClickHouse OOM | `max_memory_usage` alto en joins grandes | Reducir `max_bytes_before_external_group_by` |
| Puerto ocupado (`8080`, `3000`, `5000`) | Otro servicio del host | Remapear en `ports:` y actualizar el mapa de servicios del README |
| Bind prohibido en Windows (`forbidden by its access permissions`) | Puerto en rango excluido de WinNAT/Hyper-V (`netsh interface ipv4 show excludedportrange`) | No tocar el compose: fijar `SUPERSET_PORT=18088` o `CLICKHOUSE_HTTP_PORT=18123` en `.env` (solo cambia el lado host) y `docker compose up -d` |
| Metabase lento al inicio | Migración interna de H2 | Esperar 2–3 min; conectar con `jdbc:clickhouse://clickhouse:8123/marts` |
| JupyterLab pide token y no entra | `JUPYTER_TOKEN` distinto al de la URL | Leer el token en `.env` y usar `?token=$JUPYTER_TOKEN` |
| dbt falla por `s3()` | URL del lake mal formada o RustFS no saludable | Verificar `http://minio:9000/datalake/bronze/<entidad>/dt=*/*.parquet` |
| Drift marca `congelar` | PSI > `DRIFT_PSI_THRESHOLD` | Reentrenar y revisar la fuente; ver [mlflow-dbt-pipeline.md](../mlops/mlflow-dbt-pipeline.md) |

## 5. Playbooks de recuperación

| Escenario | Pasos |
|---|---|
| Stack caído tras reinicio del host | `docker compose up -d` → `docker compose ps` → reintentar el DAG fallido con el mismo `run_id` |
| `dbt build` en rojo | `dbt test --select <modelo> --store-failures` → corregir aguas arriba → reejecutar; nunca parchear el DW a mano |
| Modelo degradado en `Production` | Mantener la versión previa, comparar en MLflow y promover solo tras superar el *quality gate* |
| Datos corruptos en Gold | Reproducir desde Bronze (inmutable) con el `run_id` original y validar contratos antes de republicar |
| Fuga de credenciales | Rotar en `.env`, recrear servicios afectados y purgar los secretos del historial de Git |

## 6. Navegación

| Documento | Contenido |
|---|---|
| [docker-setup.md](../infrastructure/docker-setup.md) | Servicios, puertos, variables y volúmenes |
| [data-pipeline.md](../architecture/data-pipeline.md) | Etapas del dato que estos comandos operan |
| [memory-persistence.md](../memory/memory-persistence.md) | Backups, retención y purga |
| [README.md](../../README.md) | Vista general e índice maestro |
| [glossary.md](../glossary.md) | Siglas de los comandos y de cada servicio del stack |
