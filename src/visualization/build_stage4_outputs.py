"""Build Stage-IV semáforo, charts, territorial cards and static dashboard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


DISPLAY_COLUMNS = [
    "EDONOM",
    "MPIONOM",
    "SECCION",
    "risk_score",
    "risk_level",
    "latest_abstention",
    "predicted_abstention",
    "trend_reliable",
    "risk_reason",
]


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_scope(input_root: Path, scope: str) -> pd.DataFrame:
    data = pd.read_csv(input_root / f"ccpc_{scope}_integrated.csv", low_memory=False)
    if scope == "municipality":
        data["SECCION"] = pd.NA
        data["TIPOSEC"] = pd.NA
    data["display_zone"] = data["MPIONOM"]
    data.loc[data["SECCION"].notna(), "display_zone"] = (
        data.loc[data["SECCION"].notna(), "MPIONOM"]
        + " · sección "
        + data.loc[data["SECCION"].notna(), "SECCION"].astype(str)
    )
    return data


def build_semaforo(data: pd.DataFrame, output_path: Path) -> int:
    result = data[
        [
            "EDONOM",
            "MPIONOM",
            "SECCION",
            "TIPOSEC",
            "risk_score",
            "risk_level",
            "latest_abstention",
            "predicted_abstention",
            "trend_reliable",
            "prediction_available",
            "risk_reason",
            "display_zone",
        ]
    ].copy()
    result["semaforo"] = result["risk_level"].map(
        {"alto": "rojo", "medio": "amarillo", "bajo": "verde"}
    ).fillna("gris")
    result["consulta_status"] = result["risk_level"].map(
        {
            "alto": "prioridad de intervención",
            "medio": "monitoreo preventivo",
            "bajo": "seguimiento regular",
            "sin_historico": "sin histórico suficiente",
        }
    )
    result.sort_values(
        ["risk_score", "EDONOM", "MPIONOM"], ascending=[False, True, True], na_position="last"
    ).to_csv(output_path, index=False)
    return len(result)


def build_charts(data: pd.DataFrame, output_root: Path, scope: str) -> list[str]:
    chart_paths = []
    reliable = data.loc[data["risk_score"].notna()]
    counts = data["risk_level"].value_counts().reindex(
        ["bajo", "medio", "alto", "sin_historico"], fill_value=0
    )
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(counts.index, counts.values, color=["#2e7d32", "#f9a825", "#c62828", "#607d8b"])
    ax.set_title(f"Distribución del semáforo territorial · {scope}")
    ax.set_xlabel("Nivel de riesgo")
    ax.set_ylabel("Número de zonas")
    fig.tight_layout()
    path = output_root / f"{scope}_risk_distribution.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    chart_paths.append(str(path))

    top = reliable.nlargest(15, "risk_score").sort_values("risk_score")
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(top["display_zone"], top["risk_score"], color="#c62828")
    ax.set_title(f"Top 15 zonas por índice de riesgo · {scope}")
    ax.set_xlabel("Índice de riesgo (0–100)")
    ax.set_ylabel("Zona")
    fig.tight_layout()
    path = output_root / f"{scope}_top_risk.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    chart_paths.append(str(path))

    predicted = data.loc[data["predicted_abstention"].notna()].nlargest(
        15, "predicted_abstention"
    ).sort_values("predicted_abstention")
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(
        predicted["display_zone"],
        predicted["predicted_abstention"].mul(100),
        color="#1565c0",
    )
    ax.set_title(f"Top 15 zonas por abstención predicha · {scope}")
    ax.set_xlabel("Abstención predicha (%)")
    ax.set_ylabel("Zona")
    fig.tight_layout()
    path = output_root / f"{scope}_top_predicted_abstention.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    chart_paths.append(str(path))
    return chart_paths


def build_cards(data: pd.DataFrame, output_root: Path, scope: str) -> int:
    cards = data.loc[data["risk_score"].notna()].nlargest(20, "risk_score").copy()
    cards[DISPLAY_COLUMNS].to_csv(output_root / f"{scope}_territorial_cards.csv", index=False)
    cards[DISPLAY_COLUMNS].to_json(
        output_root / f"{scope}_territorial_cards.json",
        orient="records",
        force_ascii=False,
        indent=2,
    )
    return len(cards)


def build_dashboard(data_by_scope: dict[str, pd.DataFrame], output_path: Path) -> None:
    payload = {}
    for scope, data in data_by_scope.items():
        records = data.loc[
            data["risk_score"].notna() | data["predicted_abstention"].notna()
        ].copy()
        records["SECCION"] = records["SECCION"].where(records["SECCION"].notna(), "")
        records = records[
            [
                "EDONOM",
                "MPIONOM",
                "SECCION",
                "risk_score",
                "risk_level",
                "latest_abstention",
                "predicted_abstention",
                "trend_reliable",
                "risk_reason",
            ]
        ].head(1000)
        payload[scope] = records.where(records.notna(), None).to_dict(orient="records")
    html = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>Semáforo territorial INE</title>
<style>body{font-family:Arial,sans-serif;margin:2rem;color:#263238}label{margin-right:1rem}
table{border-collapse:collapse;width:100%;margin-top:1rem}th,td{border:1px solid #cfd8dc;padding:.45rem;text-align:left}
th{background:#eceff1}.alto{color:#c62828;font-weight:700}.medio{color:#f57f17;font-weight:700}
.bajo{color:#2e7d32;font-weight:700}.sin_historico{color:#607d8b;font-weight:700}
small{color:#546e7a}</style></head><body>
<h1>Semáforo territorial de abstención</h1>
<p>Consulta exploratoria basada en resultados de Stage-II. La abstención predicha no es un resultado observado.</p>
<label>Nivel territorial <select id="scope"><option value="municipality">Municipio</option><option value="section">Sección</option></select></label>
<label>Entidad <select id="state"><option value="">Todas</option></select></label>
<label>Riesgo <select id="risk"><option value="">Todos</option><option>alto</option><option>medio</option><option>bajo</option><option>sin_historico</option></select></label>
<table><thead><tr><th>Entidad</th><th>Municipio</th><th>Sección</th><th>Riesgo</th><th>Nivel</th><th>Abstención reciente</th><th>Abstención predicha</th><th>Razón</th></tr></thead><tbody id="rows"></tbody></table>
<script>
const DATA = __DATA__;
const scope = document.getElementById('scope'), state = document.getElementById('state'), risk = document.getElementById('risk'), rows = document.getElementById('rows');
function pct(x){return x == null ? '—' : (x*100).toFixed(1)+'%'}
function refreshStates(){const states=[...new Set((DATA[scope.value]||[]).map(x=>x.EDONOM))].sort(); state.innerHTML='<option value="">Todas</option>'+states.map(x=>`<option>${x}</option>`).join('')}
function render(){const values=(DATA[scope.value]||[]).filter(x=>(!state.value||x.EDONOM===state.value)&&(!risk.value||x.risk_level===risk.value)).sort((a,b)=>(b.risk_score??-1)-(a.risk_score??-1)).slice(0,200); rows.innerHTML=values.map(x=>`<tr><td>${x.EDONOM}</td><td>${x.MPIONOM}</td><td>${x.SECCION||'—'}</td><td>${x.risk_score==null?'—':x.risk_score.toFixed(2)}</td><td class="${x.risk_level}">${x.risk_level||'—'}</td><td>${pct(x.latest_abstention)}</td><td>${pct(x.predicted_abstention)}</td><td>${x.risk_reason||'—'}</td></tr>`).join('')}
scope.onchange=()=>{refreshStates();render()}; state.onchange=render; risk.onchange=render; refreshStates(); render();
</script></body></html>"""
    output_path.write_text(html.replace("__DATA__", json.dumps(payload, ensure_ascii=False)), encoding="utf-8")


def build_notebook(path: Path) -> None:
    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Etapa 4 · Exploración territorial\n",
                "Consulta rankings, semáforo y predicciones de Stage-II. Las zonas `sin_historico` no se interpretan como riesgo confiable.",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import pandas as pd\n",
                "import matplotlib.pyplot as plt\n",
                "scope = 'municipality'\n",
                "data = pd.read_csv(f'../outputs/integrated/ccpc_{scope}_integrated.csv', low_memory=False)\n",
                "data.head()",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "data['risk_level'].value_counts(dropna=False).reindex(['bajo','medio','alto','sin_historico'], fill_value=0).plot.bar(title='Distribución del riesgo')\n",
                "plt.xlabel('Nivel de riesgo'); plt.ylabel('Número de zonas'); plt.show()",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "data.loc[data.risk_score.notna()].nlargest(20, 'risk_score')[['EDONOM','MPIONOM','risk_score','risk_level','risk_reason']]",
            ],
        },
    ]
    notebook = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    root = project_root()
    parser.add_argument("--input-root", type=Path, default=root / "outputs" / "integrated")
    parser.add_argument("--output-root", type=Path, default=root / "outputs" / "stage4")
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)
    charts = []
    validation = {"stage": "Stage-II", "step": "stage4_visualization_and_consultation", "scopes": {}}
    data_by_scope = {}
    for scope in ("section", "municipality"):
        data = load_scope(args.input_root, scope)
        data_by_scope[scope] = data
        semaforo_rows = build_semaforo(data, args.output_root / f"{scope}_semaforo.csv")
        charts += build_charts(data, args.output_root, scope)
        cards = build_cards(data, args.output_root, scope)
        validation["scopes"][scope] = {
            "rows": int(len(data)),
            "semaforo_rows": semaforo_rows,
            "cards": cards,
            "duplicate_rows": int(data.duplicated(["EDOCVE", "MPIOCVE"] + (["SECCION", "TIPOSEC"] if scope == "section" else [])).sum()),
            "unreliable_rows": int((~data["trend_reliable"]).sum()),
            "risk_rows_with_score": int(data["risk_score"].notna().sum()),
            "prediction_rows": int(data["predicted_abstention"].notna().sum()),
        }
    build_dashboard(data_by_scope, args.output_root / "territorial_dashboard.html")
    notebook_dir = root / "notebooks"
    notebook_dir.mkdir(parents=True, exist_ok=True)
    build_notebook(notebook_dir / "04_exploracion_territorial.ipynb")
    validation["charts"] = charts
    validation["dashboard"] = str(args.output_root / "territorial_dashboard.html")
    validation["notebook"] = str(notebook_dir / "04_exploracion_territorial.ipynb")
    validation["checks"] = [
        "Los duplicados territoriales deben ser cero.",
        "Las zonas sin histórico conservan nivel sin_historico.",
        "La abstención predicha se etiqueta como predicción, no como observación.",
    ]
    (args.output_root / "stage4_validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Stage 4: {len(charts)} gráficos, dashboard y fichas generados")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
