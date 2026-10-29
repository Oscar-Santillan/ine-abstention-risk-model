# Reto 2 INE: riesgo territorial de abstención

Pipeline reproducible para analizar y priorizar el riesgo territorial de abstención electoral a partir de los Conteos Censales de Participación Ciudadana (CCPC) 2009–2024. El proyecto utiliza datos agregados; no procesa información personal.

## Arquitectura

```text
hackathon-ine/
├── data/                         # Fuentes crudas, intermedias y procesadas (no versionadas)
├── src/
│   ├── ingenieriaDatos/
│   │   ├── procesarDatos.py
│   │   ├── perfilarDatos.py
│   │   └── construirDatasetAnalitico.py
│   ├── modelos/
│   │   ├── crearVariablesModelo.py
│   │   ├── construirIndiceRiesgo.py
│   │   ├── entrenarModeloAbstencion.py
│   │   ├── integrarResultadosTerritoriales.py
│   │   └── construirRankingsTerritoriales.py
│   └── visualizaciones/
│       ├── generarVisualizaciones.py
│       └── empaquetarEntidades.py
├── notebooks/exploracionTerritorial.ipynb
└── outputs/
    ├── datosAnaliticos/
    ├── variables/
    ├── indiceRiesgo/
    ├── modelos/
    ├── resultadosIntegrados/
    ├── rankings/
    ├── visualizaciones/
    └── entidades/
```

## Orden de ejecución y flujo de datos

1. `procesarDatos.py`: unifica los CSV estatales por elección en `data/processed`.
2. `perfilarDatos.py`: valida columnas, faltantes, rangos y conciliación; escribe el perfil de calidad.
3. `construirDatasetAnalitico.py`: agrega observaciones por sección-año y municipio-año en `outputs/datosAnaliticos`.
4. `crearVariablesModelo.py`: crea variables históricas sin fuga temporal en `outputs/variables`.
5. `construirIndiceRiesgo.py`: calcula el índice interpretable 0–100 en `outputs/indiceRiesgo`.
6. `entrenarModeloAbstencion.py`: entrena y valida modelos temporales en `outputs/modelos`.
7. `integrarResultadosTerritoriales.py`: combina índice y predicciones en `outputs/resultadosIntegrados`.
8. `construirRankingsTerritoriales.py`: genera rankings territoriales en `outputs/rankings`.
9. `generarVisualizaciones.py`: crea semáforos, gráficas y fichas ligeras en `outputs/visualizaciones`.
10. `empaquetarEntidades.py`: produce paquetes por entidad en `outputs/entidades`.

Ejecutar desde la raíz del repositorio:

```powershell
python src/ingenieriaDatos/procesarDatos.py
python src/ingenieriaDatos/perfilarDatos.py
python src/ingenieriaDatos/construirDatasetAnalitico.py
python src/modelos/crearVariablesModelo.py
python src/modelos/construirIndiceRiesgo.py
python src/modelos/entrenarModeloAbstencion.py
python src/modelos/integrarResultadosTerritoriales.py
python src/modelos/construirRankingsTerritoriales.py
python src/visualizaciones/generarVisualizaciones.py
python src/visualizaciones/empaquetarEntidades.py
```

Para revisar sintaxis sin ejecutar el pipeline completo:

```powershell
python -m compileall src
```

## Convenciones

- Los archivos nuevos usan nombres descriptivos en español y `lowerCamelCase`.
- Las funciones y variables internas siguen `lowerCamelCase` cuando es práctico.
- Se conservan sin traducir las columnas externas del INE, como `EDOCVE`, `MPIOCVE`, `LN`, `SV`, `NV` y `NS`.
- Los artefactos derivados se escriben en `outputs` y se regeneran desde los scripts.
- Los CSV masivos, ZIP y cachés no deben agregarse al repositorio.

## Limitaciones y uso responsable

El índice es una herramienta de priorización, no una probabilidad causal ni una certeza sobre el comportamiento electoral. Los pesos son una configuración inicial interpretable y requieren validación institucional. La validación del modelo respeta el orden temporal, pero los resultados no sustituyen análisis cualitativo, revisión territorial ni decisiones del INE. Las variables externas socioeconómicas no forman parte de esta versión y los escenarios de intervención son simulaciones, no estimaciones causales.

## Reproducibilidad

Se requieren Python 3.11 o posterior y las dependencias declaradas en `requisitos-mios.txt`. Coloque las fuentes del INE en `data/raw`, ejecute las etapas en orden y conserve los manifiestos JSON para auditar entradas, filas y parámetros.
