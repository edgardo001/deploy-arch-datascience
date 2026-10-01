# Evaluación — Rúbrica de Niveles y Banco de Preguntas

> Cómo el agente `professor` evalúa sin autoengaño: **evidencia + explicación con palabras propias + repaso**.
> Contexto: [professor-and-student-agents.md](professor-and-student-agents.md) · Módulos: [curriculum.md](curriculum.md) ·
> Labs: [exercises-labs.md](exercises-labs.md).

## 1. Rúbrica de niveles

| Nivel | Ejecuta | Explica | Corrige | Diseña |
|---|---|---|---|---|
| `N0` Novato | Solo con la receta delante | Repite definiciones | No detecta errores | No opina sobre alternativas |
| `N1` Aprendiz | Adapta comandos y parámetros | Explica con sus palabras y un ejemplo | Detecta errores evidentes con ayuda | Repite el patrón en un caso nuevo |
| `N2` Autónomo | Resuelve sin guía y depura solo | Justifica decisiones y límites | Corrige causa raíz sin ayuda | Propone mejoras al modelo o al DAG |
| `N3` Referente | Automatiza y documenta | Explica *trade-offs* citando evidencia del repo | Anticipa fallos y los previene | Decide y **revoca** decisiones (ADR) y enseña a otros |

Un módulo se aprueba en el nivel que declare el `professor`, como mínimo `N1`; para rutas de "responsable de
plataforma" se exige `N2` en `M5`, `M6` y `M8`.

## 2. Cómo se evalúa un módulo

1. **Evidencia primaria**: el artefacto exigido por el módulo (salida de comando, tabla, modelo, dashboard).
2. **Explicación**: el alumno describe el concepto **sin leer** la documentación, en 3 frases.
3. **Repaso espiral**: 2 preguntas `Q-0NN` de módulos anteriores (no se avisa cuáles).
4. **Contraejemplo**: el `professor` plantea una situación en la que la herramienta **no** se recomienda
   (todas las decisiones tienen su sección «Cuándo NO» en [decisions/](../decisions/README.md)).
5. **Registro**: se anota nivel, evidencia, dudas y fecha en el `learning-log`.

## 3. Banco de preguntas de autoevaluación

| ID | Pregunta | Respuesta esperada (breve) | Referencia |
|---|---|---|---|
| `Q-01` | ¿Por qué existen capas Bronze, Silver y Gold? | Separar crudo inmutable, conformado y modelado para consumo | [data-pipeline.md](../architecture/data-pipeline.md) §1 |
| `Q-02` | ¿Qué diferencia hay entre OLTP y OLAP? | Transaccional fila a fila vs. analítico columnar y agregado | [glossary.md](../glossary.md) §2 |
| `Q-03` | ¿Por qué Bronze está particionado por `dt=`? | Idempotencia (reemplazo de partición) y poda de lectura | `D-04` |
| `Q-04` | ¿Qué garantiza el *watermark*? | Extraer solo lo nuevo usando `updated_at`, sin releer todo | `D-10` |
| `Q-05` | ¿Qué no captura la ingesta por *watermark*? | Los borrados físicos (no hay `updated_at` que los registre) | `D-10` |
| `Q-06` | ¿Qué hace `minio-init`? | Crea los 4 buckets y termina (servicio *one-shot*) | [docker-setup.md](../infrastructure/docker-setup.md) §2 |
| `Q-07` | ¿Por qué el servicio `dbt` no tiene *healthcheck*? | Es efímero: se valida con `dbt build` exit 0 | [docker-setup.md](../infrastructure/docker-setup.md) §7 |
| `Q-08` | ¿Por qué Bronze no se consume desde BI? | Es crudo y sin contrato de calidad; BI lee marts | [data-pipeline.md](../architecture/data-pipeline.md) §6 |
| `Q-09` | ¿Qué diferencia `stg_`, `int_`, `dim_` y `fct_`? | Limpieza, integración, dimensión y hecho | [glossary.md](../glossary.md) §9 |
| `Q-10` | ¿Por qué las dimensiones llevan clave sustituta (`_sk`)? | Independizar el DW de la clave natural y permitir SCD2 | `L-10` |
| `Q-11` | ¿Qué significa que `dim_customer` sea SCD2? | Guarda versiones con `valid_from`/`valid_to`, no sobreescribe | [data-pipeline.md](../architecture/data-pipeline.md) §4 |
| `Q-12` | ¿Qué granularidad tiene `fct_orders`? | Una fila por **línea** de pedido (`order_id` + `product_id`) | `D-11` |
| `Q-13` | ¿Qué test bloquea la publicación de Gold? | Los que llevan `tag: critical` | `D-11` |
| `Q-14` | ¿Por qué `staging` es vista y `fct_orders` incremental? | Evitar duplicar almacenamiento vs. acelerar hechos crecientes | `D-11` |
| `Q-15` | ¿De dónde salen las *features* del modelo? | Solo de marts Gold (`customer_features`) | `D-13` |
| `Q-16` | ¿Qué riesgo se evita usando Gold como fuente de features? | *Training/serving skew* (distribuciones distintas) | [mlflow-dbt-pipeline.md](../mlops/mlflow-dbt-pipeline.md) §1 |
| `Q-17` | ¿Qué se exige para promover un modelo a `Production`? | ROC-AUC sobre *baseline* + PSI < 0.2 + paridad aceptable | [mlflow-dbt-pipeline.md](../mlops/mlflow-dbt-pipeline.md) §4 |
| `Q-18` | ¿Qué significa PSI 0.25? | Deriva fuerte: se congela *scoring* y el dashboard deja de certificarse | [glossary.md](../glossary.md) §6 |
| `Q-19` | ¿Cómo se traza un dato de extremo a extremo? | Con el `run_id` que une Airflow, dbt, MLflow y *scoring* | [MEMORY.md](../../MEMORY.md) §5 |
| `Q-20` | ¿Qué contiene un *handoff*? | `run_id`, agentes, artefactos, contratos, precondiciones y estado | [orchestration-rules.md](../agents/orchestration-rules.md) §5 |
| `Q-21` | ¿Cuándo **no** conviene ClickHouse? | OLTP, updates fila a fila o `JOIN` de altísima cardinalidad | `D-05` |
| `Q-22` | ¿Cuándo **no** conviene Docker Compose? | Alta disponibilidad, multiusuario o multi-nodo | `D-07` |
| `Q-23` | ¿Qué distingue un ADR de un documento normal? | Declara decisión, «cuándo NO» y alternativas con pros y contras | [decisions/README.md](../decisions/README.md) §2 |
| `Q-24` | ¿Dónde se registra una duda recurrente y dónde una petición? | Duda en `FAQ.md`; petición en `prompt-log.md` (`P-00N`) | [FAQ.md](../../FAQ.md) §1 |

## 4. Criterios de promoción

| Situación | Decisión del `professor` |
|---|---|
| Evidencia correcta pero explicación memorística | Repetir el módulo con un lab distinto, no avanzar |
| Evidencia correcta y explicación con ejemplo propio | `N1` aprobado; siguiente módulo |
| Corrige un fallo propio sin ayuda y justifica límites | `N2`; se le asignan labs de otro perfil |
| Propone mejora al repo y la justifica con evidencia | `N3`; puede redactar un ADR o una petición `P-00N` |
| No consigue evidencia | Se degrada el lab (versión más simple) y se registra la fricción de la documentación |

## 5. Señales de aprendizaje superficial (a vigilar)

1. Pegar una salida que no se ha ejecutado (fechas, rutas o conteos incoherentes con el entorno).
2. Explicar usando el texto de la documentación palabra por palabra, sin ejemplo propio.
3. Aprobar el lab sin poder decir **qué pasaría si** un parámetro, una partición o un test cambia.
4. No poder nombrar una sola alternativa a la herramienta usada (señal de que no se leyó «Cuándo NO»).
5. No registrar ninguna duda: en este proyecto, **cero dudas en un módulo indica revisión insuficiente**.

## 6. Cadencia y repaso

| Momento | Acción |
|---|---|
| Fin de cada módulo | Rúbrica + 2 preguntas de módulos previos |
| Semanal | Repaso de 5 preguntas al azar del banco |
| Al cambiar un artefacto del repo | Se reabre el módulo afectado (el material debe reflejar el estado real) |
| Cada vez que una duda se repite | Se convierte en `F-0NN` del [FAQ.md](../../FAQ.md) |

## 7. Navegación

| Documento | Contenido |
|---|---|
| [README.md](README.md) | Cómo pedir una sesión de aprendizaje |
| [professor-and-student-agents.md](professor-and-student-agents.md) | Roles, fichas y protocolo de sesión |
| [curriculum.md](curriculum.md) | Módulos y rutas por perfil |
| [exercises-labs.md](exercises-labs.md) | Los laboratorios `L-01`…`L-08` |
| [labs-quality-ml-bi.md](labs-quality-ml-bi.md) | Los laboratorios `L-09`…`L-14` |
