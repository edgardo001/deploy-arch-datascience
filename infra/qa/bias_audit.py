#!/usr/bin/env python3
"""Auditoría de sesgo del scoring: paridad demográfica y *disparate impact* por grupo.

Métricas calculadas sobre la tabla de *scoring* (``silver.scoring``), para cada columna
sensible indicada en ``--sensitive``:

* **Paridad demográfica (DPD)**: diferencia entre la tasa de selección (proporción de
  predicciones positivas) del grupo más favorecido y el menos favorecido.
* **Disparate impact (DI)**: cociente ``tasa_min / tasa_max``; la *regla 4/5* exige ``DI >= 0.8``.

Severidad de los hallazgos:

============================  ==========  ==========
Métrica                       Umbral      Severidad
============================  ==========  ==========
DPD                           ``<= 0.05`` baja · ``<= 0.10`` media · resto alta
DI                            ``>= 0.80`` baja · ``>= 0.70`` media · resto alta
============================  ==========  ==========

Uso:
    python infra/qa/bias_audit.py --table silver.scoring --sensitive gender,age_band \\
        --metric demographic_parity,disparate_impact

El proceso sale con código ≠ 0 si hay algún hallazgo de severidad ``alta`` (AGENTS.md §2.7).
Sin secretos: todo por variables de entorno.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections import defaultdict

DPD_BAJA, DPD_MEDIA = 0.05, 0.10
DI_BAJA, DI_MEDIA = 0.80, 0.70

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("bias_audit")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Argumentos de la auditoría: tabla, columnas sensibles y métricas a calcular."""
    parser = argparse.ArgumentParser(description="Paridad demográfica y disparate impact del scoring")
    parser.add_argument("--table", default="silver.scoring", help="tabla con scoring y columnas sensibles")
    parser.add_argument("--sensitive", default="gender,age_band", help="columnas sensibles separadas por coma")
    parser.add_argument("--prediction-col", default="churn_pred", help="columna binaria de predicción (0/1)")
    parser.add_argument("--score-col", default="churn_score", help="columna de probabilidad (alternativa)")
    parser.add_argument("--score-threshold", type=float, default=float(os.getenv("CHURN_SCORE_THRESHOLD", "0.5")),
                        help="umbral para derivar la predicción si solo hay probabilidad")
    parser.add_argument("--metric", default="demographic_parity,disparate_impact",
                        help="métricas a calcular separadas por coma")
    parser.add_argument("--sample-limit", type=int, default=500_000, help="máximo de filas leídas")
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
        raise RuntimeError("Se requiere 'clickhouse-connect' o 'clickhouse-driver' para auditar "
                           "sesgo; ninguna está instalada en este entorno") from exc


def leer_grupos(filas, tabla: str, sensibles: list[str], args: argparse.Namespace):
    """Lee sensibles + predicción y agrega ``{sensible: {grupo: (n, positivos)}}``."""
    disponibles = {f[0] for f in filas(f"SELECT name FROM system.columns "
                                       f"WHERE table = '{tabla.split('.')[-1]}'")}
    falta = [c for c in [*sensibles, args.prediction_col, args.score_col] if c not in disponibles]
    logger.info("Columnas ausentes en %s (se resolverán si es posible): %s", tabla, falta)
    if any(c not in disponibles for c in sensibles):
        raise RuntimeError(f"La tabla {tabla} no expone las columnas sensibles {sensibles}")

    if args.prediction_col in disponibles:
        expresion = f"`{args.prediction_col}`"
    elif args.score_col in disponibles:
        expresion = f"toUInt8(`{args.score_col}` >= {args.score_threshold})"
    else:
        raise RuntimeError(f"La tabla {tabla} no tiene '{args.prediction_col}' ni '{args.score_col}': "
                           "ejecuta antes infra/pipelines/score.py")

    seleccion = ", ".join(f"`{c}`" for c in sensibles)
    consulta = f"SELECT {seleccion}, {expresion} AS pred FROM {tabla} LIMIT {int(args.sample_limit)}"
    agregados: dict[str, dict[str, list[int]]] = {c: defaultdict(lambda: [0, 0]) for c in sensibles}
    for fila in filas(consulta):
        pred = int(fila[-1] or 0)
        for indice, sensible in enumerate(sensibles):
            grupo = str(fila[indice]) if fila[indice] is not None else "(sin dato)"
            agregados[sensible][grupo][0] += 1
            agregados[sensible][grupo][1] += pred
    return agregados


def severidad_dpd(valor: float) -> str:
    """Severidad de la brecha de paridad demográfica."""
    if valor <= DPD_BAJA:
        return "baja"
    return "media" if valor <= DPD_MEDIA else "alta"


def severidad_di(valor: float) -> str:
    """Severidad del disparate impact (regla 4/5)."""
    if valor >= DI_BAJA:
        return "baja"
    return "media" if valor >= DI_MEDIA else "alta"


def analizar(sensible: str, grupos: dict[str, list[int]], metricas: list[str]) -> list[dict]:
    """Calcula las métricas pedidas y emite los hallazgos con severidad."""
    if not grupos:
        return []
    print(f"\nsensible={sensible}  grupos={len(grupos)}")
    print(f"  {'grupo':<16}{'n':>10}{'positivos':>11}{'tasa_seleccion':>16}")
    for grupo, (total, positivos) in sorted(grupos.items()):
        print(f"  {grupo:<16}{total:>10}{positivos:>11}{(positivos / total if total else 0):>16.4f}")

    tasas = {g: (p / n if n else 0.0) for g, (n, p) in grupos.items()}
    maximo, minimo = max(tasas.values()), min(tasas.values())
    dpd = maximo - minimo
    di = (minimo / maximo) if maximo else 1.0
    grupo_max = max(tasas, key=tasas.get)
    grupo_min = min(tasas, key=tasas.get)

    hallazgos: list[dict] = []
    if "demographic_parity" in metricas:
        sev = severidad_dpd(dpd)
        print(f"  DPD={dpd:.4f} ({grupo_max} vs {grupo_min})  severidad={sev}")
        hallazgos.append({"metrica": "demographic_parity", "sensible": sensible, "valor": round(dpd, 4),
                          "severidad": sev, "detalle": f"{grupo_max} (tasa {maximo:.4f}) vs {grupo_min} "
                                                          f"(tasa {minimo:.4f})"})
    if "disparate_impact" in metricas:
        sev = severidad_di(di)
        print(f"  DI={di:.4f} ({grupo_min}/{grupo_max})  severidad={sev}  regla_4_5={'cumple' if di >= DI_BAJA else 'INCUMPLE'}")
        hallazgos.append({"metrica": "disparate_impact", "sensible": sensible, "valor": round(di, 4),
                          "severidad": sev, "detalle": f"tasa {grupo_min}/{grupo_max} = {di:.4f}"})
    return hallazgos


def main(argv: list[str] | None = None) -> int:
    """Ejecuta la auditoría de sesgo; devuelve 1 si hay hallazgos de severidad alta."""
    args = parse_args(argv)
    sensibles = [c.strip() for c in args.sensitive.split(",") if c.strip()]
    metricas = [m.strip() for m in args.metric.split(",") if m.strip()]
    try:
        filas, modo = ejecutor_clickhouse()
        logger.info("Auditando %s con %s", args.table, modo)
        agregados = leer_grupos(filas, args.table, sensibles, args)
    except Exception as exc:
        logger.error("No se pudo leer la tabla de scoring: %s", exc)
        return 2

    print(f"tabla={args.table}  prediccion={args.prediction_col}  metricas={metricas}")
    hallazgos: list[dict] = []
    for sensible in sensibles:
        hallazgos.extend(analizar(sensible, agregados.get(sensible, {}), metricas))

    altas = [h for h in hallazgos if h["severidad"] == "alta"]
    print(f"\nhallazgos={len(hallazgos)} altos={len(altas)}")
    if altas:
        logger.error("Hallazgos de sesgo ALTA: %s. Documentar remediación antes de certificar el KPI.",
                     [f"{h['sensible']}:{h['metrica']}={h['valor']}" for h in altas])
        return 1
    logger.info("Auditoría de sesgo sin hallazgos de severidad alta")
    return 0


if __name__ == "__main__":
    sys.exit(main())
