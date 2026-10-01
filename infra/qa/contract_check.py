#!/usr/bin/env python3
"""Valida los contratos de datos de ``infra/contracts/marts.yml`` contra el DW (ClickHouse).

Comprueba, por tabla del contrato: **existencia** de la tabla y de sus columnas, **nulos** en las
columnas ``nullable: false``, **unicidad** de claves (``unique``/``unique_combination``), **rango**
(``accepted_range``) y **frescura** del SLA (``freshness``). El resultado se persiste en
``meta.quality_gates`` (``signed_by = governance``) y el proceso sale con código ≠ 0 si falla algún
contrato de severidad ``critical`` (quality gate duro, AGENTS.md §2.7). Sin secretos: solo variables
de entorno.

Uso:
    python infra/qa/contract_check.py --contracts infra/contracts/marts.yml --run-id "$RUN_ID"
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timezone

import yaml

CONTRATOS_POR_DEFECTO = os.getenv("CONTRACTS_PATH", "infra/contracts/marts.yml")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("contract_check")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Argumentos: ruta del contrato y ``run_id`` con el que se firma el gate."""
    parser = argparse.ArgumentParser(description="Valida los contratos de marts contra ClickHouse")
    parser.add_argument("--contracts", default=CONTRATOS_POR_DEFECTO, help="ruta del YAML de contratos")
    parser.add_argument("--run-id", default=os.getenv("RUN_ID", ""), help="run_id firmado en quality_gates")
    return parser.parse_args(argv)


def ejecutor_clickhouse():
    """Devuelve ``(filas, modo)`` con ``filas(sql) -> list[tuple]``.

    Prefiere ``clickhouse-connect`` y degrada a ``clickhouse-driver``; si no hay ninguno, lanza un
    error explícito en vez de romper en el *import*.
    """
    host, usuario = os.getenv("CLICKHOUSE_HOST", "clickhouse"), os.getenv("CLICKHOUSE_USER", "dbt")
    clave, base = os.getenv("CLICKHOUSE_PASSWORD", ""), os.getenv("CLICKHOUSE_DB", "marts")
    try:
        import clickhouse_connect

        cliente = clickhouse_connect.get_client(host=host, port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
                                                username=usuario, password=clave, database=base)
        return lambda sql: [tuple(f) for f in cliente.query(sql).result_rows], "clickhouse-connect"
    except ImportError:
        logger.warning("clickhouse-connect no está instalado; se intenta clickhouse-driver")
    try:
        from clickhouse_driver import Client

        cliente = Client(host=host, port=int(os.getenv("CLICKHOUSE_NATIVE_PORT", "9000")),
                         user=usuario, password=clave, database=base)
        return lambda sql: [tuple(f) for f in cliente.execute(sql)], "clickhouse-driver"
    except ImportError as exc:
        raise RuntimeError("Se requiere 'clickhouse-connect' o 'clickhouse-driver' para validar "
                           "contratos; ninguna está instalada en este entorno") from exc


def _partir(tabla: str) -> tuple[str, str]:
    """Separa ``base.tabla`` usando la base por defecto cuando falta el prefijo."""
    base, _, nombre = tabla.partition(".")
    return (base or os.getenv("CLICKHOUSE_DB", "marts"), nombre or base)


def _escalar(filas, sql: str):
    """Primer valor de una consulta de agregación (``None`` si no devuelve filas)."""
    resultado = filas(sql)
    return resultado[0][0] if resultado else None


def _check(tabla: str, test_id: str, tipo: str, severidad: str, ok: bool, detalle: str) -> dict:
    """Resultado homogéneo de una comprobación del contrato."""
    return {"tabla": tabla, "id": test_id, "tipo": tipo, "severidad": severidad, "ok": bool(ok), "detalle": detalle}


def validar_tabla(filas, tabla: str, contrato: dict) -> list[dict]:
    """Ejecuta todas las comprobaciones declaradas para una tabla."""
    base, nombre = _partir(tabla)
    existe = int(_escalar(filas, "SELECT count() FROM system.tables "
                                 f"WHERE database = '{base}' AND name = '{nombre}'") or 0)
    if not existe:
        return [_check(tabla, f"{tabla}_existe", "existe", "critical", False, "la tabla no existe en el DW")]

    reales = {f[0] for f in filas("SELECT name FROM system.columns "
                                  f"WHERE database = '{base}' AND table = '{nombre}'")}
    declaradas = [c["name"] for c in contrato.get("columns", [])]
    faltantes = sorted(set(declaradas) - reales)
    detalle = "todas las columnas declaradas existen" if not faltantes else f"faltan columnas: {faltantes}"
    resultados = [_check(tabla, f"{tabla}_columnas", "columnas", "critical", not faltantes, detalle)]

    for columna in contrato.get("columns", []):
        nombre_col = columna["name"]
        if nombre_col in reales and not columna.get("nullable", True):
            nulos = int(_escalar(filas, f"SELECT countIf(isNull(`{nombre_col}`)) FROM {tabla}") or 0)
            resultados.append(_check(tabla, f"{tabla}.{nombre_col}_not_null", "not_null", "critical",
                                     nulos == 0, f"{nulos} nulos en columna no nullable"))
    resultados.extend(_evaluar_test(filas, tabla, test) for test in contrato.get("critical_tests", []))
    return resultados


def _evaluar_test(filas, tabla: str, test: dict) -> dict:
    """Evalúa un test declarado en ``critical_tests`` (unicidad, rango o frescura)."""
    tipo, columnas = test.get("type", ""), test.get("columns", [])
    severidad, test_id = test.get("severity", "warn"), test.get("id", f"{tabla}_{tipo}")
    ref = ", ".join(f"`{c}`" for c in columnas)
    try:
        if tipo == "unique":
            duplicados = int(_escalar(filas, f"SELECT count() - uniqExact({ref}) FROM {tabla}") or 0)
            return _check(tabla, test_id, tipo, severidad, duplicados == 0, f"{duplicados} duplicados")
        if tipo == "unique_combination":
            total, distintas = filas(f"SELECT count(), uniqExact({ref}) FROM {tabla}")[0]
            return _check(tabla, test_id, tipo, severidad, int(total) == int(distintas),
                          f"filas={total} combinaciones_distintas={distintas}")
        if tipo == "accepted_range":
            minimo, maximo = test.get("min"), test.get("max")
            condiciones = ([f"`{columnas[0]}` < {minimo}"] if minimo is not None else []) + \
                          ([f"`{columnas[0]}` > {maximo}"] if maximo is not None else [])
            fuera = int(_escalar(filas, f"SELECT countIf({' OR '.join(condiciones)}) FROM {tabla}") or 0)
            return _check(tabla, test_id, tipo, severidad, fuera == 0,
                          f"{fuera} filas fuera de [{minimo}, {maximo}]")
        if tipo == "freshness":
            ultimo = _escalar(filas, f"SELECT max(`{columnas[0]}`) FROM {tabla}")
            limite = test.get("max_delay_minutes", 1440)
            if ultimo is None:
                return _check(tabla, test_id, tipo, severidad, False, "la columna de frescura está vacía")
            retraso = (datetime.now(timezone.utc).replace(tzinfo=None) - ultimo).total_seconds() / 60
            return _check(tabla, test_id, tipo, severidad, retraso <= limite,
                          f"retraso={retraso:.0f} min (límite {limite} min, último dato {ultimo})")
        return _check(tabla, test_id, tipo, severidad, False, f"tipo de test no soportado: {tipo}")
    except Exception as exc:
        return _check(tabla, test_id, tipo, severidad, False, f"error al evaluar el test: {exc}")


def escribir_gate(run_id: str, estado: str, total: int, fallidos: int) -> None:
    """Persiste el gate en ``meta.quality_gates`` asegurando antes el run referenciado."""
    import psycopg2

    conexion = psycopg2.connect(host=os.getenv("POSTGRES_HOST", "oltp-postgres"),
                                port=int(os.getenv("POSTGRES_PORT", "5432")),
                                dbname=os.getenv("POSTGRES_META_DB", "datalab_meta"),
                                user=os.getenv("POSTGRES_USER", "datalab"),
                                password=os.getenv("POSTGRES_PASSWORD", ""))
    try:
        with conexion, conexion.cursor() as cur:
            cur.execute("INSERT INTO meta.pipeline_runs (run_id, intent, status, current_step, current_agent) "
                        "VALUES (%s, 'assurance', 'validado', 'contract_check', 'governance') "
                        "ON CONFLICT (run_id) DO NOTHING", (run_id,))
            cur.execute("INSERT INTO meta.quality_gates (run_id, scope, status, tests_total, "
                        "tests_failed, signed_by) VALUES (%s, 'marts', %s, %s, %s, 'governance')",
                        (run_id, estado, total, fallidos))
    finally:
        conexion.close()


def main(argv: list[str] | None = None) -> int:
    """Ejecuta la validación completa; devuelve 1 si falla algún contrato crítico."""
    args = parse_args(argv)
    with open(args.contracts, encoding="utf-8") as fh:
        tablas = (yaml.safe_load(fh) or {}).get("tables", {})
    if not tablas:
        logger.error("El contrato %s no declara tablas", args.contracts)
        return 2
    try:
        filas, modo = ejecutor_clickhouse()
    except Exception as exc:
        logger.error("No se pudo conectar a ClickHouse: %s", exc)
        return 2
    logger.info("Validando %s tablas contra ClickHouse (%s)", len(tablas), modo)

    resultados = [r for tabla, contrato in tablas.items() for r in validar_tabla(filas, tabla, contrato)]
    fallidos = [r for r in resultados if not r["ok"]]
    criticos = [r for r in fallidos if r["severidad"] == "critical"]
    for fallo in fallidos:
        logger.warning("[%s] %s (%s): %s", fallo["severidad"].upper(), fallo["id"], fallo["tipo"], fallo["detalle"])

    estado = "rechazado" if criticos else "aprobado"
    if args.run_id:
        try:
            escribir_gate(args.run_id, estado, len(resultados), len(fallidos))
            logger.info("Quality gate persistido: run_id=%s estado=%s", args.run_id, estado)
        except Exception as exc:
            logger.error("No se pudo persistir el gate en meta.quality_gates: %s", exc)

    print(f"contratos={args.contracts}")
    print(f"checks_total={len(resultados)} fallidos={len(fallidos)} criticos={len(criticos)}")
    print(f"estado={estado}")
    if criticos:
        logger.error("CONTRATO CRÍTICO INCUMPLIDO: %s comprobaciones críticas fallidas", len(criticos))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())