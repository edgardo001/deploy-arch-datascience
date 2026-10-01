# Capa de Aprendizaje — Cómo Aprender Este Proyecto

> Los **7 agentes especialistas son las áreas docentes**; el **Profesor** diseña tu ruta y el **Alumno** ejecuta,
> pregunta y aporta evidencias. Aquí empieza todo: rutas por perfil, cómo pedir una sesión y qué se exige para
> avanzar. Módulos: [curriculum.md](curriculum.md) · Labs: [exercises-labs.md](exercises-labs.md) ·
> Evaluación: [assessment.md](assessment.md) · Agentes: [professor-and-student-agents.md](professor-and-student-agents.md).

## 1. Para qué sirve esta capa

1. **Aprender el proyecto completo**, no solo usarlo: desde qué es un OLTP hasta por qué se eligió cada herramienta.
2. **Aprender con el repo real**: cada concepto se practica sobre los mismos artefactos que ejecuta el pipeline
   (DAGs, modelos dbt, MLflow, dashboards), nunca sobre ejemplos inventados.
3. **Aprender con evidencia**: se aprueba demostrando (comando ejecutado, tabla consultada, modelo registrado)
   y explicando el concepto con palabras propias.
4. **Mejorar la documentación aprendiendo**: cada duda o fricción alimenta el [FAQ.md](../../FAQ.md) y los módulos,
   así que estudiar el proyecto también lo hace más claro.
5. **Trabajar como en un equipo real**: la [rutina diaria](daily-routine.md) y las 20 tareas `T-0NN` reproducen las
   solicitudes que te harán en el área (incidencias, KPIs nuevos, auditorías, informes).

## 2. Quién enseña qué

| Rol | Enseña | Ejemplo de petición |
|---|---|---|
| `professor` | Rutas, conceptos, labs, evaluación y feedback | «Enséñame M3 en 90 minutos, nivel intermedio» |
| `student` | Nada: aprende, pregunta y audita la documentación | «Actúa como alumno y sigue `L-05` al pie de la letra» |
| `data_engineer` (área) | Ingesta, Airflow, lake, idempotencia | «Explícame por qué reejecutar el DAG no duplica filas» |
| `analytics_engineer` (área) | dbt, tests, modelado dimensional | «¿Por qué `fct_orders` es incremental y `stg_orders` vista?» |
| `ds_mlops` (área) | Features, entrenamiento, MLflow, drift | «¿Qué métrica mira el gate para promover el modelo?» |
| `bi_viz` (área) | KPIs, dashboards, conexiones JDBC | «¿Cómo certifico este KPI en Metabase?» |
| `governance` (área) | Linaje, contratos, sesgo, calidad | «¿Qué contratos se romperían si cambio un enum?» |
| `platform` (área) | Compose, puertos, volúmenes, perfiles | «¿Por qué Airflow no arranca y qué reviso?» |
| `orchestrator` (área) | Ruteo, planes, memoria, bitácora | «¿Cómo se registra una petición `P-00N`?» |

## 3. Cómo pedir una sesión de aprendizaje

| Quieres… | Pídelo así |
|---|---|
| Empezar de cero | «Soy nuevo: dame la ruta de `M0` con labs y evidencia, en sesiones de 60 min» |
| Ir a lo tuyo | «Vengo de SQL/BI: ruta corta hasta `M7` y sáltate lo que ya domino» |
| Practicar | «Dame el lab `L-11` con pistas en lugar de la solución» |
| Evaluarte | «Hazme el quiz de `M4` (`Q-10`…`Q-14`) y dime el nivel `N0`-`N3` con la rúbrica» |
| Entender el *porqué* | «Contraejemplo: ¿cuándo ClickHouse sería un error aquí?» (`D-05`) |
| Auditar la documentación | «Actúa como alumno simulado y ejecuta `L-06`; reporta cada fricción» |
| Repasar | «Repaso espiral: 5 preguntas al azar del banco con sus referencias» |

## 4. Rutas por perfil

| Perfil | Módulos | Duración | Evidencia final |
|---|---|---|---|
| Analista de negocio | `M0 → M1 → M4 → M7` | ~6 h | KPI publicado y reproducible por SQL (`L-14`) |
| Ingeniero de datos | `M0 → M1 → M2 → M3 → M5` | ~9 h | DAG en verde + gate bloqueando Gold (`L-05`, `L-11`) |
| Científico de datos | `M0 → M1 → M3 → M4 → M6` | ~9 h | Modelo registrado con `run_id` y decisión argumentada (`L-13`) |
| Responsable de plataforma | `M0 → M1 → M5 → M6 → M8` | ~10 h | ADR nuevo + informe de drift (`M8`) |
| Curioso total | `M0 … M8` | ~18 h | Los 14 labs aprobados |
| Práctica laboral | `M0 → M1 → M2` + [rutina diaria](daily-routine.md) | 4 semanas a tiempo parcial | Las 20 tareas `T-01`…`T-20` cerradas con evidencia |

## 5. Estructura de esta carpeta

| Archivo | Contenido | Cuándo abrirlo |
|---|---|---|
| [README.md](README.md) | Este índice: cómo pedir sesión y rutas | Siempre, al empezar |
| [curriculum.md](curriculum.md) | Los 9 módulos con objetivos y evidencias | Para planificar |
| [professor-and-student-agents.md](professor-and-student-agents.md) | Fichas de los agentes, protocolo de sesión y `learning-log` | Para saber cómo se enseña y se evalúa |
| [exercises-labs.md](exercises-labs.md) | Labs `L-01`…`L-08`: entorno, lake, ingesta y dbt | Al practicar la base |
| [labs-quality-ml-bi.md](labs-quality-ml-bi.md) | Labs `L-09`…`L-14`: modelado, calidad, ML y BI | Al practicar el ciclo completo |
| [daily-routine.md](daily-routine.md) | Ritmo diario, catálogo de solicitudes y priorización | Al empezar a operar el entorno |
| [daily-tasks.md](daily-tasks.md) | Backlog `T-01`…`T-20` repartido en 4 semanas | Cada día laborable |
| [assessment.md](assessment.md) | Rúbrica `N0`-`N3` y 24 preguntas | Al cerrar cada módulo |

## 6. Reglas de la capa de aprendizaje

1. **Sin evidencia no hay aprobado**: vale una salida real de comando o un artefacto del repo.
2. **El Profesor da pistas, no soluciones**: la primera respuesta a un bloqueo es una pregunta.
3. **Un lab fallido es material didáctico**: se documenta la causa raíz y se enlaza al módulo.
4. **Toda duda repetida va al FAQ** (`F-0NN`) y, si la respuesta crece, se amplía el módulo de `docs/`.
5. **El material envejece con el repo**: si cambia un artefacto, el módulo afectado se reabre.
6. **Ningún archivo de esta carpeta supera 180 líneas**: si crece, se parte por tema y se indexa aquí.

## 7. Cómo se mantiene actualizada

| Situación | Acción | Responsable |
|---|---|---|
| El alumno se atasca con un documento | Nueva fila en el [FAQ.md](../../FAQ.md) y, si procede, aclaración en el módulo | `professor` + `governance` |
| El repositorio cambia (`marts`, DAG, contrato) | Reabrir el módulo y actualizar el lab afectado | Área docente correspondiente |
| Falta un ejercicio intermedio | Nuevo lab `L-0NN` en [exercises-labs.md](exercises-labs.md) | `professor` |
| Cambia el perfil del alumno | Ajustar ruta en [curriculum.md](curriculum.md) §Rutas | `professor` |
| Se detecta una decisión técnica mal explicada | Revisar el ADR `D-0NN` afectado | `governance` |

## 8. Navegación

| Documento | Contenido |
|---|---|
| [AGENTS.md](../../AGENTS.md) | Catálogo de los 9 agentes (7 especialistas + Profesor + Alumno) |
| [glossary.md](../glossary.md) | Siglas del proyecto, incluidas las de esta capa (`M-0N`, `L-0N`, `Q-0N`) |
| [decisions/README.md](../decisions/README.md) | Por qué cada herramienta y cuándo deja de servir |
| [case-study.md](../case-study.md) | Por qué existe el proyecto y qué cargos de la industria representa |
| [FAQ.md](../../FAQ.md) | Dudas breves con respuesta y enlace |
