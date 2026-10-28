# Estado real del proyecto frente a los requisitos aspiracionales

## Conclusión ejecutiva

El proyecto ya tiene completo el núcleo reproducible del reto: datos CCPC perfilados,
dataset analítico por municipio y sección, índice de riesgo 0–100, modelo temporal,
escenarios sin/con intervención, salidas explicadas en español y paquete visual.

Lo que falta para convertirlo en un entregable institucional Top 1 no es otra gráfica
aislada: son los componentes de integración, operación y entrega final.

## Matriz de cumplimiento

| Componente | Estado | Evidencia actual | Pendiente concreto |
|---|---|---|---|
| Serie histórica CCPC 2009–2024 | Completo | Seis ejercicios procesados y validados | Documentar catálogo final de variables |
| Unidad territorial sección/municipio | Completo | Riesgo, predicción y escenarios en ambos niveles | Incorporar distrito si se obtiene la llave oficial |
| Modelo predictivo temporal | Completo | Gradient Boosting, Ridge y persistencia comparados | Agregar intervalos de incertidumbre y calibración |
| Explicabilidad | Parcial | Importancia por permutación y justificación por zona | Incorporar SHAP o explicaciones locales equivalentes |
| Escenario sin intervención | Completo | Abstención predicha como línea base | Documentar supuestos y horizonte futuro |
| Escenario con intervención | Completo | Uplift absoluto configurable de 2%, 5% y 10% | Convertirlo en controles interactivos y vincularlo a costos |
| Variables INEGI/contextuales | Pendiente | El modelo usa principalmente CCPC y demografía agregada interna | Integrar marginación, educación, servicios, movilidad y contexto, si existe llave territorial |
| Semáforo territorial | Parcial | PNG y CSV con niveles bajo/medio/alto | Crear mapa interactivo con GeoJSON/SHP |
| Dashboard operativo | Pendiente | No existe Streamlit, Plotly ni Power BI publicado | Crear filtros por entidad, municipio, distrito y sección |
| Priorización de recursos | Parcial | Ranking por score, riesgo alto e impacto simulado | Crear matriz impacto/esfuerzo y catálogo de acciones |
| Recomendaciones institucionales | Parcial | Acciones genéricas por nivel en salidas ejecutivas | Redactar recomendaciones alineadas a ENCÍVICA con responsables, horizonte y evidencia |
| Validación y limitaciones | Parcial | Backtesting temporal y notas de no causalidad | Añadir análisis de estabilidad, sesgo, incertidumbre y sensibilidad territorial |
| Reporte metodológico 10–15 páginas | Pendiente | No existe PDF final | Generar reporte con método, métricas, resultados, escenarios y limitaciones |
| Presentación ejecutiva | Pendiente | No existe presentación de máximo 10 diapositivas | Crear narrativa para jurado y tomadores de decisión |
| Base final entregable | Parcial | CSV técnicos y ejecutivos generados | Consolidar diccionario, manifest, versión y guía de reproducción |
| Publicación limpia | Pendiente | Existe rama limpia local, sin push final confirmado | Verificar remoto, publicar y documentar commit reproducible |

## Lectura correcta de las métricas

- El modelo de sección mejora el MAE de persistencia de **0.1190 a 0.0761** en 2024.
- El modelo municipal mejora de **0.0733 a 0.0691**.
- El R² municipal es **0.3804** y el de sección **0.2786**; el modelo sirve para
  priorizar, no para afirmar certeza individual.
- La intervención de 5 puntos porcentuales es una hipótesis de planeación, no un
  efecto causal observado.

## Prioridad recomendada para cerrar brechas

1. Construir el dashboard filtrable y el mapa territorial.
2. Integrar variables externas agregadas y documentar la llave geográfica.
3. Crear la matriz impacto/esfuerzo y recomendaciones institucionales.
4. Generar el reporte metodológico y la presentación ejecutiva.
5. Empaquetar, probar de extremo a extremo y publicar la rama limpia.
