# Hackathon INE - Reto 2: Predicción y Escenarios de Riesgo de Abstención

Repositorio analítico para el desarrollo de un modelo predictivo de riesgo de abstención electoral y simulación de escenarios basada en los Conteos Censales de Participación Ciudadana (CCPC) 2009-2024 del INE.

## 📂 Estructura del Proyecto

```text
hackathon-ine/
├── data/
│   ├── raw/            # Archivos ZIP originales descargados del INE
│   ├── interim/        # Archivos CSV descompuestos por año y entidad
│   └── processed/      # Datasets limpios y unificados listos para modelado
├── src/
│   ├── data_engineering/ # Scripts de extracción, limpieza y unificación
│   ├── models/         # Modelos predictivos de riesgo de abstención
│   └── visualization/  # Generación de mapas de riesgo y reportes
├── notebooks/          # Jupyter Notebooks para análisis exploratorio (EDA)
├── outputs/            # Resultados, figuras y recomendaciones estratégicas
├── Project.txt         # Documento base del reto
└── README.md           # Este archivo
```

## 🚀 Objetivo
Construir un modelo de análisis predictivo que identifique zonas con mayor riesgo futuro de abstención, permitiendo al INE realizar una planeación anticipada y priorización estratégica de recursos.

## Estado actual

La rama `Stage-II` contiene las etapas 1 a 4 del modelo de riesgo:

- feature engineering histórico sin fuga temporal;
- índice interpretable 0–100 con semáforo y zonas sin histórico separadas;
- modelo temporal de abstención con baseline, Random Forest y métricas;
- integración territorial, rankings, visualizaciones Matplotlib, fichas y notebook.

La rama `Stage-I` permanece separada y conserva únicamente Data Engineering.

Los artefactos generados de Stage-II se encuentran en `outputs/features`,
`outputs/risk`, `outputs/models`, `outputs/integrated`, `outputs/rankings` y
`outputs/stage4`. Las gráficas se exportan en PNG y PDF; el notebook exploratorio de la Etapa 4 está en
`notebooks/04_exploracion_territorial.ipynb`.
