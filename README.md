# Sistema de Modelado Predictivo y Simulación de Escenarios Electorales (CCPC-INE)

## Equipo de desarrollo: Loop-E

* **Integrantes:**
    * Santillán Sánchez, Oscar Ariel
    * Hernández López, Alejandro
* **Institución:** Ingeniería en Computación, Facultad de Ingeniería, UNAM (3er semestre)

---

## 1. Descripción del proyecto

Este repositorio contiene el framework analítico desarrollado para el **Reto 2 del INE: Predicción y escenarios de riesgo de abstención**. El sistema construye indicadores de riesgo y proyecciones a partir de la serie histórica de los Conteos Censales de Participación Ciudadana (CCPC 2009-2024).

El objetivo es ofrecer a la Dirección Ejecutiva de Capacitación Electoral y Educación Cívica (DECEYEC) una herramienta para identificar zonas con riesgo de abstención y comparar escenarios de intervención, a nivel de entidad, municipio y sección electoral.

## 2. Estado del proyecto

| Fase | Estado |
|---|---|
| Ingeniería de datos y perfilado de calidad | Completada |
| Modelo e índice de riesgo | Completada |
| Simulación 1: escenario sin intervención (2030) | Completada |
| Simulación 2: escenario con intervención (2030) | Completada |
| Dashboard de diagnóstico (Tableau) | En desarrollo |

## 3. Flujo de procesamiento

1. **Ingeniería de datos:** carga, unificación histórica, normalización de nombres territoriales y perfilado de calidad.
2. **Modelo de riesgo:** variables históricas por zona, índice de riesgo, entrenamiento y validación temporal.
3. **Simulación de escenarios:**
    * **Escenario sin intervención (inercial):** proyección de la participación y la abstención a 2030 suponiendo que continúa la pendiente histórica de cada zona.
    * **Escenario con intervención:** aplicación de tres propuestas según el perfil de riesgo de cada zona, con análisis de sensibilidad.
4. **Visualización:** gráficas por entidad y comparativas entre ambos escenarios.

### Perfiles de riesgo (Simulación 2)

Los perfiles son excluyentes y se asignan con prioridad A, B, C:

| Perfil | Criterio | Propuestas aplicadas |
|---|---|---|
| A. Abstención base crítica | Nivel de riesgo alto | P1 |
| B. Deterioro acelerado | Tendencia descendente de participación | P1 y P2 |
| C. Inestabilidad cíclica | Participación inestable | P1 y P3 |

* **P1:** Árbol de Influencers + Red de Embajadores Electorales.
* **P2:** Campaña de Rescate Cívico con Monitoreo de Movilidad.
* **P3:** Plataforma Cívica Digital Gamificada.

Las zonas sin histórico suficiente no tienen proyección y no se simulan.

## 4. Guía de ejecución

Los CSV de `outputs/` **no se versionan** (ver `.gitignore`): se regeneran con el pipeline. Todos los comandos se ejecutan desde la raíz del repositorio y en este orden.

### Paso 1: Datasets analíticos

```bash
python src/ingenieria_datos/03_construir_dataset_analitico.py
python src/ingenieria_datos/normalizar_nombres_territoriales.py
```

El segundo script unifica nombres territoriales que cambian entre años (por ejemplo, "DISTRITO FEDERAL" y "CIUDAD DE MEXICO") y repara texto mal codificado. Sin este paso, el histórico de esas zonas queda partido y no se proyectan.

### Paso 2: Variables y modelo de riesgo

```bash
python src/modelos/01_creacion_variables_modelo.py
python src/modelos/02_construir_indice_riesgo.py
python src/modelos/03_entrenar_y_validar_modelo.py
python src/modelos/04_integrar_resultados_modelo.py
python src/modelos/05_generar_rankings_territoriales.py
```

### Paso 3: Simulación de escenarios

```bash
# Escenario sin intervención (2030)
python src/modelos/06_simular_escenario_sin_intervencion.py

# Escenario con intervención (2030) + informe en docs/informe_simulacion_2.md
python src/modelos/07_simular_escenario_intervencion.py
```

Parámetros útiles del escenario con intervención:

```bash
python src/modelos/07_simular_escenario_intervencion.py --cobertura-movilidad 1.0 --factor 0.5 --tope-pp 6
```

### Paso 4: Visualizaciones

```bash
# Escenario sin intervención, por entidad
python src/visualizaciones/02_generar_visualizaciones_escenario.py
python src/visualizaciones/03_empaquetar_entidades.py

# Comparación sin vs con intervención
python src/visualizaciones/08_generar_visualizaciones_intervencion.py --solo-nacional
```

Sin `--solo-nacional` también se generan las gráficas de cada entidad. Con `--entidad "Oaxaca"` se genera una sola.

## 5. Salidas principales

| Ruta | Contenido |
|---|---|
| `outputs/escenarios/` | Escenarios sin y con intervención (municipios y secciones) y sensibilidad |
| `outputs/entidades/<entidad>/` | Paquete por entidad: datos, resumen y gráficas |
| `outputs/visualizaciones/intervencion/` | Gráficas comparativas nacionales |
| `docs/informe_simulacion_2.md` | Informe de la Simulación 2 con tablas generadas por el script |

## 6. Limitaciones

* Los efectos de cada propuesta de intervención son **supuestos de diseño**, no estimaciones causales. Por eso se reporta un análisis de sensibilidad (efectos multiplicados por 0.5, 1.0 y 1.5), y se recomienda validarlos con un piloto antes de escalar.
* Las proyecciones asumen continuidad lineal de la tendencia histórica y no incorporan cambios en la normatividad ni choques externos.
* Las zonas sin dato base o con histórico insuficiente no se proyectan.

## 7. Requerimientos

```bash
pip install "pandas>=2.2.0" "numpy>=1.26.0" "matplotlib>=3.8.0"
```

Este proyecto fue desarrollado con estándares de analítica predictiva aplicada a la toma de decisiones institucionales.
