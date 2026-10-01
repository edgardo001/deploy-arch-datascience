-- =====================================================================
-- DataLab Productivo Local — marts.dim_date
-- Documento: docs/architecture/data-pipeline.md §4 (modelo dimensional)
--
-- Materialización: table · tag: gold · esquema: marts
-- Granularidad: 1 fila por día (date_key = YYYYMMDD).
-- Calendario generado con numbers(): cubre desde 2023-01-01 hasta 2 años
-- después de hoy, para que las fechas futuras de scoring sigan existiendo.
-- =====================================================================
{{ config(
    materialized='table',
    tags=['gold', 'marts', 'dimension', 'date'],
    schema='marts',
    order_by='date_key'
) }}

WITH bounds AS (
    SELECT
        toDate('2023-01-01')                     AS start_day,
        addYears(today(), 2)                     AS end_day
),

days AS (
    SELECT
        addDays(b.start_day, toInt32(number)) AS date_day
    FROM bounds AS b
    CROSS JOIN numbers(dateDiff('day', b.start_day, b.end_day) + 1) AS n(number)
)

SELECT
    toUInt32(toYYYYMMDD(date_day))                                  AS date_key,
    date_day                                                        AS date_day,
    toUInt16(toYear(date_day))                                      AS year,
    toUInt8(toQuarter(date_day))                                    AS quarter,
    concat(toString(toYear(date_day)), '-Q', toString(toQuarter(date_day))) AS year_quarter,
    toUInt8(toMonth(date_day))                                      AS month,
    formatDateTime(date_day, '%Y-%m')                               AS year_month,
    toUInt8(toDayOfMonth(date_day))                                 AS day_of_month,
    toUInt8(toDayOfWeek(date_day))                                  AS day_of_week,       -- 1=lunes
    formatDateTime(date_day, '%a')                                  AS day_name,
    toUInt16(toISOWeek(date_day))                                   AS iso_week,
    toUInt8(toDayOfYear(date_day))                                  AS day_of_year,
    toUInt8(toDayOfWeek(date_day) >= 6)                             AS is_weekend
FROM days
