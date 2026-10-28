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
