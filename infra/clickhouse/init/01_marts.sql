-- =====================================================================
-- DataLab Productivo Local — Inicialización del Data Warehouse OLAP
-- Documento: docs/infrastructure/docker-setup.md (servicio `clickhouse`)
--            docs/architecture/data-pipeline.md §5 (modelado Gold)
--
-- Se ejecuta una sola vez al crear el volumen `clickhouse_data`
-- (clickhouse-server lee *.sql de /docker-entrypoint-initdb.d).
-- Sin secretos: el usuario/clave llegan por CLICKHOUSE_USER y
-- CLICKHOUSE_PASSWORD, y la imagen ya provisiona ese usuario con
-- todos los privilegios sobre CLICKHOUSE_DB.
-- =====================================================================

-- Base destino de los modelos dbt (`profile: datalab`, `schema: marts`).
CREATE DATABASE IF NOT EXISTS marts;

-- dbt-clickhouse crea el esquema destino del perfil (por defecto `marts`)
-- y, si se declara `+schema` por capa, los esquemas derivados. El proyecto
-- `infra/dbt/dbt_project.yml` usa `+schema: marts_staging` para staging e
-- intermediate, así que ese esquema se prepara aquí de forma idempotente.
CREATE DATABASE IF NOT EXISTS marts_staging;

-- El bootstrap de la imagen ya hace:
--   GRANT ALL ON marts.* TO <CLICKHOUSE_USER> WITH GRANT OPTION
-- (con CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT=1). Como el nombre del rol es
-- dinámico, no se repite el GRANT con un literal; si se necesita un rol
-- adicional de solo lectura para BI (Metabase/Superset), se ejecuta como
-- administrador y con el nombre resuelto en tiempo de despliegue:
--
--   CREATE ROLE IF NOT EXISTS bi_reader;
--   GRANT SELECT ON marts.* TO bi_reader;
--   CREATE USER IF NOT EXISTS bi_user IDENTIFIED BY '<desde .env>';
--   GRANT bi_reader TO bi_user;
--
-- `currentUser()` refleja el usuario con el que corre este script
-- (el propio CLICKHOUSE_USER) y queda registrado para auditoría:
SELECT currentUser() AS init_user, currentDatabase() AS init_database, version() AS ch_version;

-- ---------------------------------------------------------------------
-- NOTA IMPORTANTE (comentario, no ejecutable)
-- Las tablas del esquema en estrella NO se crean aquí: las materializa
-- dbt con el perfil `datalab` (infra/dbt/profiles.yml) sobre esta base.
--
--   staging/       → vistas efímeras sobre Parquet Bronze (s3(...))
--   intermediate/  → vistas de integración (joins, sin agregación final)
--   marts/         → tablas e incrementales del esquema en estrella:
--                      marts.fct_orders        (1 fila por línea de pedido)
--                      marts.fct_payments      (1 fila por pago)
--                      marts.dim_customer      (SCD2, 1 fila por versión)
--                      marts.dim_product       (1 fila por producto)
--                      marts.dim_date          (1 fila por día)
--                      marts.dim_seller        (1 fila por vendedor)
--                      marts.customer_features (1 fila por cliente, features)
--
-- Comandos de referencia:
--   docker compose run --rm dbt build            # + tests genéricos
--   docker compose run --rm dbt test --select tag:gold
--   docker compose run --rm dbt docs generate
-- ---------------------------------------------------------------------
