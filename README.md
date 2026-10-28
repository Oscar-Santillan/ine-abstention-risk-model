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

## Resultados en español

Los resultados explicados para consulta institucional se generan en:

```text
outputs/ejecutivo/
```

Cada archivo incluye la zona, sus datos principales, el nivel de riesgo, la justificación,
la interpretación sencilla y la acción recomendada. Los reportes disponibles son:

- riesgo explicado por sección y municipio;
- predicciones explicadas por sección y municipio;
- escenarios explicados por sección y municipio;
- resumen general en `outputs/ejecutivo/README.md`.

El diagnóstico de lo que ya cumple el proyecto y de las brechas restantes frente a
los requisitos aspiracionales está en:

```text
outputs/ejecutivo/analisis_brechas_estado.md
```

El paquete visual ampliado se genera con:

```powershell
python src\visualization\generate_visualizations.py
```

Ahora incluye tableros ejecutivos, evolución histórica, comparación de modelos,
sensibilidad de escenarios, semáforo territorial, relaciones entre factores,
calidad predictiva, impacto simulado y matriz de componentes del riesgo.
