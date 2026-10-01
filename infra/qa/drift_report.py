#!/usr/bin/env python3
"""Informe de *data drift* (PSI) por feature entre una ventana de referencia y la actual.

Clasificación de cada feature (docs/agents/specialists-deep-dive.md §7):

===========================  ==========================================
PSI                           Acción
===========================  ==========================================
``< 0.1``                     estable
``0.1 – 0.2``                 vigilar
``> DRIFT_PSI_THRESHOLD``     congelar el scoring y des-certificar el dashboard
===========================  ==========================================

Uso:
    python infra/qa/drift_report.py --reference gold.customer_features \\
        --current gold.customer_features_recent \\
        --features recency_days,orders_last_30d,monetary_365d,avg_ticket,tickets_support_90d

El proceso sale con código ≠ 0 si alguna feature queda en estado ``congelar`` (guardrail de
drift de AGENTS.md §5). Sin secretos: todo por variables de entorno.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

import numpy as np

FEATURES_POR_DEFECTO = [
    "recency_days",
    "orders_last_30d",
    "monetary_365d",
    "avg_ticket",
    "tickets_support_90d",
]
UMBRAL_CONGELAR = float(os.getenv("DRIFT_PSI_THRESHOLD", "0.2"))
UMBRAL_ESTABLE = 0.1

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("drift_report")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Argumentos del informe: tablas, features, bins y umbral."""
    parser = argparse.ArgumentParser(description="Calcula el PSI por feature entre dos ventanas")
    parser.add_argument("--reference", default="gold.customer_features",
                        help="tabla de referencia (baseline del modelo)")
    parser.add_argument("--current", default="gold.customer_features_recent",
                        help="tabla de la ventana actual")
    parser.add_argument("--features", default=",".join(FEATURES_POR_DEFECTO),
                        help="features a comparar, separadas por coma")
    parser.add_argument("--bins", type=int, default=10, help="número de bins (deciles por defecto)")
    parser.add_argument("--threshold", type=float, default=UMBRAL_CONGELAR,
                        help="PSI a partir del cual se congela el scoring")
    parser.add_argument("--sample-limit", type=int, default=200_000,
                        help="máximo de filas leídas por tabla (control de presupuesto)")
    return parser.parse_args(argv)


def ejecutor_clickhouse():
    """Devuelve ``(filas, modo)`` con ``filas(sql) -> list[tuple]``.

    Prefiere ``clickhouse-connect`` y degrada a ``clickhouse-driver``; si no hay ninguno, lanza un
    error explícito en vez de romper en el *import* (no se instalan dependencias en ejecución).
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
        raise RuntimeError("Se requiere 'clickhouse-connect' o 'clickhouse-driver' para calcular el "
                           "PSI; ninguna está instalada en este entorno") from exc


def leer_features(filas, tabla: str, features: list[str], limite: int) -> dict[str, np.ndarray]:
    """Lee las features numéricas de una tabla y las devuelve como arrays de ``float``."""
    columnas = ", ".join(f"`{c}`" for c in features)
    resultados = filas(f"SELECT {columnas} FROM {tabla} LIMIT {int(limite)}")
    if not resultados:
        raise RuntimeError(f"La tabla {tabla} no devolvió filas para las features {features}")
    matriz = np.array([[np.nan if v is None else float(v) for v in fila] for fila in resultados], dtype=float)
    logger.info("Leídas %s filas de %s", matriz.shape[0], tabla)
    return {feature: matriz[:, i] for i, feature in enumerate(features)}


def calcular_psi(referencia: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    """PSI entre dos muestras usando cortes por cuantiles de la distribución de referencia."""
    referencia = referencia[~np.isnan(referencia)]
    actual = actual[~np.isnan(actual)]
    if referencia.size == 0 or actual.size == 0:
        return float("nan")
    cortes = np.unique(np.quantile(referencia, np.linspace(0, 1, bins + 1)))
    if cortes.size < 2:  # distribución degenerada: sin variación que comparar
        return 0.0
    cortes = cortes.astype(float)
    cortes[0], cortes[-1] = -np.inf, np.inf

    proporcion_ref = np.histogram(referencia, bins=cortes)[0] / referencia.size
    proporcion_act = np.histogram(actual, bins=cortes)[0] / actual.size
    epsilon = 1e-6  # evita log(0) en bins vacíos
    proporcion_ref = np.clip(proporcion_ref, epsilon, None)
    proporcion_act = np.clip(proporcion_act, epsilon, None)
    return float(np.sum((proporcion_act - proporcion_ref) * np.log(proporcion_act / proporcion_ref)))


def clasificar(valor: float, umbral: float) -> str:
    """Traduce el PSI a la acción operativa: estable, vigilar o congelar."""
    if valor != valor:  # NaN
        return "sin_datos"
    if valor < UMBRAL_ESTABLE:
        return "estable"
    if valor <= umbral:
        return "vigilar"
    return "congelar"


def main(argv: list[str] | None = None) -> int:
    """Calcula el PSI de cada feature, imprime el informe y devuelve 1 si hay congelación."""
    args = parse_args(argv)
    features = [f.strip() for f in args.features.split(",") if f.strip()]
    try:
        filas, modo = ejecutor_clickhouse()
        logger.info("Comparando ventanas con %s", modo)
        referencia = leer_features(filas, args.reference, features, args.sample_limit)
        actual = leer_features(filas, args.current, features, args.sample_limit)
    except Exception as exc:
        logger.error("No se pudo leer las ventanas de comparación: %s", exc)
        return 2

    print(f"referencia={args.reference}  actual={args.current}  umbral_congelar={args.threshold}")
    print(f"{'feature':<24}{'psi':>9}{'estado':>12}{'n_ref':>10}{'n_act':>10}")
    congeladas: list[str] = []
    for feature in features:
        if feature not in referencia or feature not in actual:
            print(f"{feature:<24}{'—':>9}{'sin_datos':>12}{'—':>10}{'—':>10}")
            continue
        valor = calcular_psi(referencia[feature], actual[feature], args.bins)
        estado = clasificar(valor, args.threshold)
        if estado == "congelar":
            congeladas.append(feature)
        psi_txt = "nan" if valor != valor else f"{valor:.4f}"
        print(f"{feature:<24}{psi_txt:>9}{estado:>12}{referencia[feature].size:>10}{actual[feature].size:>10}")

    if congeladas:
        logger.error(
            "CONGELAR scoring: PSI > %.2f en %s. Reentrenar y revisar la fuente antes de publicar "
            "(docs/operations/runbook.md §4).", args.threshold, ", ".join(congeladas),
        )
        return 1
    logger.info("Drift dentro de umbral (%.2f) en las %s features evaluadas", args.threshold, len(features))
    return 0


if __name__ == "__main__":
    sys.exit(main())
