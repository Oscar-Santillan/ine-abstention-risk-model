# INE — Modelo de riesgo de abstención y escenarios electorales

Proyecto analítico para el Reto 2 del INE. Integra los Conteos Censales de
Participación Ciudadana (CCPC) de 2009 a 2024 para construir variables
territoriales, estimar riesgo de abstención, proyectar un escenario inercial a
2030 y comparar intervenciones simuladas.

El análisis se realiza a nivel de sección electoral y municipio. El proyecto
incluye un tablero web autocontenido que se genera localmente a partir de los
resultados del pipeline.

## Requisitos

- Python 3.10 o superior.
- `pip`.
- Datos CCPC colocados en la estructura esperada bajo `data\interim\`.

Instala las dependencias desde la raíz del repositorio:

```powershell
python -m pip install -r requirements.txt
```

Las dependencias principales son:

- `pandas` y `numpy` para procesamiento.
- `matplotlib` para visualizaciones.
- `scikit-learn` para el modelo temporal con `RandomForestRegressor`,
  imputación, métricas y pipelines.

## Estructura del proyecto

```text
data\
  interim\                 Archivos CCPC de entrada, organizados por año
src\
  ingenieria_datos\        Carga, validación y datasets analíticos
  modelos\                 Variables, riesgo, predicción y escenarios
  visualizaciones\         Gráficas, paquetes y tablero web
outputs\                   Resultados generados localmente; no se versionan
docs\                      Informes metodológicos y de simulación
notebooks\                 Exploraciones auxiliares
```

Los archivos de `outputs\` se crean automáticamente al ejecutar los scripts y
están excluidos de Git mediante `.gitignore`.

## Ejecución completa

Ejecuta los comandos desde la raíz del repositorio y en este orden:

### 1. Cargar y unificar los datos

Si los archivos fuente están organizados por año dentro de `data\interim\`:

```powershell
python src\ingenieria_datos\01_cargar_y_unificar_datos_ine.py
```

Este paso genera los archivos agregados por año en `data\processed\`.

### 2. Perfilar la calidad de los datos (opcional)

```powershell
python src\ingenieria_datos\02_perfilar_y_validar_calidad.py
```

### 3. Construir los datasets analíticos

```powershell
python src\ingenieria_datos\03_construir_dataset_analitico.py
```

Genera tablas de sección-año y municipio-año en
`outputs\analytical\`.

### 4. Crear variables e índice de riesgo

```powershell
python src\modelos\01_creacion_variables_modelo.py
python src\modelos\02_construir_indice_riesgo.py
```

### 5. Entrenar y validar el modelo

```powershell
python src\modelos\03_entrenar_y_validar_modelo.py
```

El modelo usa los años anteriores a 2024 para entrenamiento y valida contra
2024. Los modelos, predicciones, métricas y manifiestos se guardan en
`outputs\models\`.

### 6. Integrar resultados y generar rankings

```powershell
python src\modelos\04_integrar_resultados_modelo.py
python src\modelos\05_generar_rankings_territoriales.py
```

### 7. Ejecutar los escenarios

Escenario sin intervención:

```powershell
python src\modelos\06_simular_escenario_sin_intervencion.py
```

Escenario con intervención:

```powershell
python src\modelos\07_simular_escenario_intervencion.py
```

Parámetros disponibles para el escenario con intervención:

```powershell
python src\modelos\07_simular_escenario_intervencion.py `
  --cobertura-movilidad 1.0 `
  --factor 0.5 `
  --tope-pp 6
```

El escenario con intervención genera también el informe
`docs\informe_simulacion_2.md`.

## Visualizaciones y tablero web

Genera las visualizaciones generales:

```powershell
python src\visualizaciones\01_generar_panorama_general.py
python src\visualizaciones\02_generar_visualizaciones_escenario.py
python src\visualizaciones\03_empaquetar_entidades.py
```

Genera las visualizaciones comparativas:

```powershell
python src\visualizaciones\08_generar_visualizaciones_intervencion.py --solo-nacional
```

Para generar también las visualizaciones por entidad:

```powershell
python src\visualizaciones\08_generar_visualizaciones_intervencion.py
```

Finalmente, genera el tablero web y las tablas anonimizadas:

```powershell
python src\visualizaciones\09_empaquetar_mapa_escenarios.py
```

El resultado principal es:

```text
outputs\entregable_escenarios\mapa_escenarios.html
```

Abre el tablero directamente en el navegador o utiliza un servidor local:

```powershell
python -m http.server 5500
```

Después visita:

```text
http://127.0.0.1:5500/outputs/entregable_escenarios/mapa_escenarios.html
```

El tablero permite consultar municipios y secciones, filtrar por entidad,
comparar escenarios y revisar niveles de riesgo, perfiles e intervenciones.

## Salidas generadas

El pipeline crea, entre otras, las siguientes carpetas:

```text
outputs\analytical\
outputs\features\
outputs\risk\
outputs\models\
outputs\integrated\
outputs\rankings\
outputs\escenarios\
outputs\visualizaciones\
outputs\entidades\
outputs\entregable_escenarios\
```

Estas salidas no se almacenan en el repositorio. Después de clonar el proyecto
es normal que `outputs\` no exista hasta ejecutar el pipeline.

## Consideraciones

- Las salidas se regeneran localmente y no forman parte del código fuente.
- Las proyecciones suponen continuidad de las tendencias históricas.
- Los efectos de las intervenciones son supuestos de simulación, no efectos
  causales estimados.
- Las zonas con histórico insuficiente pueden quedar sin proyección.
- Los datos fuente y los archivos grandes no se versionan; deben estar
  disponibles localmente antes de ejecutar el pipeline.
