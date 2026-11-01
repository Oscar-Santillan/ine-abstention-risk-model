# Informe Simulación 2: escenario con intervención

Generado: 2026-10-31 20:45  
Reto 2 INE: predicción y escenarios de riesgo de abstención.

## 1. Qué se simuló

Sobre la abstención proyectada a 2030 (escenario sin intervención) se aplican tres propuestas
según el perfil de cada zona:

| Perfil | Propuestas | Reducción asumida (escenario base) |
|---|---|---|
| A | P1 Árbol de Influencers + Red de Embajadores | -3.0 pp |
| B | P1 + P2 Rescate Cívico con Monitoreo de Movilidad | -1.0 pp (P1) y -4.0 pp x cobertura 60% (P2) |
| C | P1 + P3 Plataforma Cívica Gamificada | -0.5 pp (P1) y -5.0 pp (P3) |

Tope de reducción por zona: 8.0 pp.

## 2. Resultados

### Municipios

| Métrica | Valor |
|---|---|
| Zonas totales | 2,477 |
| Zonas con proyección | 2,465 |
| Zonas sin proyección (sin histórico) | 12 |
| Zonas intervenidas | 1,268 |
| Abstención media 2030, sin intervención (%) | 31.96 |
| Abstención media 2030, con intervención (%) | 30.04 |
| Reducción media (pp) | 1.92 |
| Zonas en nivel alto (base → intervención) | 822 → 707 |
| Zonas que salen del nivel alto | 115 |
| Votos adicionales estimados | 1,858,445 |

**Por perfil**

| Perfil | Descripción | Zonas | Abs. base (%) | Abs. interv. (%) | Reducción (pp) |
|---|---|---|---|---|---|
| A | Abstención base crítica (riesgo alto) | 504 | 47.39 | 44.39 | 3.00 |
| B | Deterioro acelerado (tendencia descendente) | 437 | 32.34 | 28.94 | 3.40 |
| C | Inestabilidad cíclica (participación inestable) | 327 | 23.26 | 17.93 | 5.33 |
| sin_perfil | Con proyección pero sin señal de riesgo específica | 1197 | 27.71 | 27.71 | 0.00 |
### Secciones

| Métrica | Valor |
|---|---|
| Zonas totales | 70,751 |
| Zonas con proyección | 68,646 |
| Zonas sin proyección (sin histórico) | 2,105 |
| Zonas intervenidas | 29,698 |
| Abstención media 2030, sin intervención (%) | 35.42 |
| Abstención media 2030, con intervención (%) | 33.75 |
| Reducción media (pp) | 1.67 |
| Zonas en nivel alto (base → intervención) | 22,882 → 20,149 |
| Zonas que salen del nivel alto | 2,733 |
| Votos adicionales estimados | 1,675,369 |

**Por perfil**

| Perfil | Descripción | Zonas | Abs. base (%) | Abs. interv. (%) | Reducción (pp) |
|---|---|---|---|---|---|
| A | Abstención base crítica (riesgo alto) | 10234 | 50.97 | 47.97 | 3.00 |
| B | Deterioro acelerado (tendencia descendente) | 10611 | 36.76 | 33.36 | 3.40 |
| C | Inestabilidad cíclica (participación inestable) | 8853 | 28.52 | 23.12 | 5.40 |
| sin_perfil | Con proyección pero sin señal de riesgo específica | 38948 | 32.53 | 32.53 | 0.00 |

## 3. Sensibilidad (municipios)

Los efectos de cada propuesta son supuestos de diseño. Se escalan x0.5, x1.0 y x1.5 para mostrar el rango:

| escenario | factor | abs_media_interv_pct | reduccion_media_pp | salen_de_alto |
|---|---|---|---|---|
| conservador | 0.50 | 31.00 | 0.97 | 60 |
| base | 1.00 | 30.04 | 1.92 | 115 |
| optimista | 1.50 | 29.13 | 2.84 | 176 |

## 4. Limitaciones

- Los efectos por propuesta no están estimados con datos experimentales; son hipótesis a validar con pilotos.
- Los perfiles se definen con `risk_level` y `risk_reason`. Los CSV de escenario no traen edad ni volatilidad,
  así que el perfil C es un proxy de inestabilidad, no de juventud.
- Las zonas sin histórico suficiente no tienen proyección y no se simulan; requieren otra estrategia (recolección de datos).
- La cobertura de movilidad es un parámetro, no un dato observado.
