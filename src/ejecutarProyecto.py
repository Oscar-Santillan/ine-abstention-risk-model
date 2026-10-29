"""Orquesta el flujo completo del proyecto de riesgo de abstención.

Corre las etapas en orden: perfilado -> dataset analítico -> variables ->
índice de riesgo -> modelo predictivo -> integración -> escenario ->
visualizaciones -> paquetes territoriales.  Cada etapa es un módulo
independiente que puede ejecutarse por separado; este script solo las
invoca en secuencia y falla al primer error para que sea fácil localizarlo.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _python() -> str:
    """Nombre del ejecutable que está corriendo este proceso."""

    return sys.executable


def _run(script: Path, *args: str) -> None:
    """Ejecuta un script de la pipeline y lanza si falla."""

    command = [_python(), str(script), *args]
    print(f"\n>>> {' '.join(command)}")
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise SystemExit(f"Falló {script.name} (código {result.returncode})")


def main() -> int:
    raiz = Path(__file__).resolve().parents[1]
    scripts = [
        # Etapa 1 · Datos
        raiz / "src" / "ingenieriaDatos" / "procesarDatos.py",
        raiz / "src" / "ingenieriaDatos" / "perfilarDatos.py",
        raiz / "src" / "ingenieriaDatos" / "construirDatasetAnalitico.py",
        # Etapa 2 · Modelo
        raiz / "src" / "modelos" / "crearVariablesModelo.py",
        raiz / "src" / "modelos" / "construirIndiceRiesgo.py",
        raiz / "src" / "modelos" / "entrenarModeloAbstencion.py",
        raiz / "src" / "modelos" / "integrResultadoTerritoriales.py",
        raiz / "src" / "modelos" / "construirRankingsTerritoriales.py",
        # Etapa 3 · Escenarios
        raiz / "src" / "modelos" / "simularEscenarioSinIntervencion.py",
        # Etapa 4 · Visualización y entrega
        raiz / "src" / "visualizaciones" / "generarVisualizaciones.py",
        raiz / "src" / "visualizaciones" / "generarVisualizacionesEscenarioSinIntervencion.py",
        raiz / "src" / "visualizaciones" / "empaquetarEntidades.py",
    ]
    for script in scripts:
        if not script.is_file():
            raise SystemExit(f"Script no encontrado: {script}")
        _run(script)
    print("\nFlujo completo ejecutado con éxito.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())