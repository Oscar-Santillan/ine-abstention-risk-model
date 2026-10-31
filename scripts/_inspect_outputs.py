from pathlib import Path
import csv
import json

root = Path(".")

print("=== MUNI COLS ===")
with open(root / "outputs/resultadosIntegrados/ccpc_municipioResultadosIntegrados.csv", encoding="utf-8") as f:
    h = next(csv.reader(f))
    row = next(csv.reader(f))
print("\n".join(h))
print("n_cols", len(h))

print("\n=== SEC COLS ===")
with open(root / "outputs/resultadosIntegrados/ccpc_seccionResultadosIntegrados.csv", encoding="utf-8") as f:
    r = csv.reader(f)
    h = next(r)
print("\n".join(h))

print("\n=== SCENARIO MUNI COLS ===")
with open(root / "outputs/escenarios/ccpc_municipioEscenarioSinIntervencion.csv", encoding="utf-8") as f:
    print("\n".join(next(csv.reader(f))))

print("\n=== RANKINGS ===")
for p in Path("outputs/rankings").rglob("*"):
    if p.is_file():
        print(p, p.stat().st_size)

print("\n=== MODELOS ===")
for p in Path("outputs/modelos").rglob("*"):
    if p.is_file():
        print(p, p.stat().st_size)

print("\n=== MAPAS ===")
for p in Path("data/mapas").rglob("*"):
    if p.is_file():
        print(p, p.stat().st_size)

print("\n=== HISTORICO ===")
h = json.loads(Path("outputs/resultadosIntegrados/historicoNacional.json").read_text(encoding="utf-8"))
print(type(h), h.keys() if isinstance(h, dict) else "")
if isinstance(h, dict):
    for k, v in h.items():
        if isinstance(v, dict):
            print(k, "dict keys", list(v.keys())[:12])
        elif isinstance(v, list):
            print(k, "list", len(v), v[0] if v else None)
        else:
            print(k, type(v).__name__, str(v)[:120])
