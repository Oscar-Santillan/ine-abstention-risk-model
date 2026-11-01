# Hackathon INE - Reto 2: Prediccin y Escenarios de Riesgo de Abstencin

Repositorio analtico para el desarrollo de un modelo predictivo de riesgo de abstencin electoral y simulacin de escenarios basado en los Conteos Censales de Participacin Ciudadana (CCPC) 2009-2024 del INE.

## Estructura del Proyecto

- data/              : archivos RAW y procesados
- src/ingenieria_datos/ : scripts de ingestin y limpieza
- src/modelos/       : modelos de riesgo y simulaciones
- src/visualizaciones/: generacin de graficas
- docs/              : informes y documentacin
- outputs/           : resultados y visualizaciones

## Simulacion 1 - Escenario SIN intervencion

- Script: src/modelos/06_simular_escenario_sin_intervencion.py
- Proyeccion inercial de abstencion a 2030
- Salidas: outputs/escenarios/ccpc_.*EscenarioSinIntervencion.csv

## Simulacion 2 - Escenario CON intervencion

- Script: src/modelos/07_simular_escenario_intervencion.py
- Visualizaciones: src/visualizaciones/08_generar_visualizaciones_intervencion.py
- Informe: docs/informe_simulacion_2.md

### Propuestas de Intervincin

- P1: Arbol de Influencers + Red de Embajadores (-3.0 pp)
- P2: Campaa de Rescate Civico con Monitoreo de Movilidad
- P3: Plataforma Civica Digital Gamificada

## Instalacin de Dependencias

pip install -r requirements.txt

## Uso

python src/modelos/06_simular_escenario_sin_intervencion.py
python src/modelos/07_simular_escenario_intervencion.py
python src/visualizaciones/08_generar_visualizaciones_intervencion.py
