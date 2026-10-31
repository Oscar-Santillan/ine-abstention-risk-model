const fs = require("fs");
const path = require("path");

// Source: INEGI-geojson (MacWilliXD) AGEE.geojson — 32 estados, 30MB raw.
// Output: a compact state-level choropleth map for the dashboard.
// Each state geometry is decimated to a fixed budget of points per ring so the
// resulting file stays small enough to ship inside the Vite build (~100KB).

// Source path is passed as an argument so the script never assumes a fixed
// location for the downloaded (untrusted) upstream file.
const SRC = path.resolve(process.argv[2] || "/tmp/agee.geojson");
const OUT = path.resolve(__dirname, "..", "data", "mapas", "estados.json");

const BUDGET_PER_RING = 100; // max points kept per ring

/**
 * Ramer-Douglas-Peucker simplification for a polyline of [x,y] points.
 * Keeps the shape while dropping far fewer points than uniform sampling.
 */
function simplify(points, epsilon) {
  if (points.length <= 2) return points.slice();
  let maxDist = 0;
  let idx = 0;
  const end = points.length - 1;
  const a = points[0];
  const b = points[end];
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const denom = dx * dx + dy * dy;
  for (let i = 1; i < end; i += 1) {
    const p = points[i];
    let dist;
    if (denom === 0) {
      dist = (p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2;
    } else {
      const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / denom));
      const projx = a[0] + t * dx;
      const projy = a[1] + t * dy;
      dist = (p[0] - projx) ** 2 + (p[1] - projy) ** 2;
    }
    if (dist > maxDist) {
      maxDist = dist;
      idx = i;
    }
  }
  if (maxDist <= epsilon * epsilon) return [a, b];
  const left = simplify(points.slice(0, idx + 1), epsilon);
  const right = simplify(points.slice(idx), epsilon);
  return left.slice(0, -1).concat(right);
}

function simplifyRing(ring, budget) {
  if (ring.length <= budget) return ring;
  // DP simplification collapses a ring to its two endpoints once epsilon is large
  // enough, so "largest epsilon under budget" always wins with 2 points. Instead we
  // want the SMALLEST epsilon that satisfies the budget: that keeps the most detail
  // while still fitting. lo starts unsatisfied, hi starts satisfied.
  let lo = 0,
    hi = 8000;
  let best = ring;
  for (let iter = 0; iter < 32; iter += 1) {
    const mid = (lo + hi) / 2;
    const cand = simplify(ring, mid);
    if (cand.length <= budget) {
      best = cand;
      hi = mid; // satisfied — try a smaller epsilon for more detail
    } else {
      lo = mid; // too many points — need a larger epsilon
    }
  }
  return best;
}

function main() {
  if (!fs.existsSync(SRC)) {
    console.error("Missing source:", SRC);
    process.exit(1);
  }
  const raw = JSON.parse(fs.readFileSync(SRC, "utf8"));
  // Map INEGI state names onto the EDONOM keys used throughout the dashboard CSVs.
  const NAME_TO_EDONOM = {
    "Aguascalientes": "AGUASCALIENTES",
    "Baja California": "BAJA CALIFORNIA",
    "Baja California Sur": "BAJA CALIFORNIA SUR",
    "Campeche": "CAMPECHE",
    "Chiapas": "CHIAPAS",
    "Chihuahua": "CHIHUAHUA",
    "Ciudad de México": "CIUDAD DE MEXICO",
    "Coahuila de Zaragoza": "COAHUILA",
    "Colima": "COLIMA",
    "Durango": "DURANGO",
    "Guanajuato": "GUANAJUATO",
    "Guerrero": "GUERRERO",
    "Hidalgo": "HIDALGO",
    "Jalisco": "JALISCO",
    "México": "MEXICO",
    "Michoacán de Ocampo": "MICHOACAN",
    "Morelos": "MORELOS",
    "Nayarit": "NAYARIT",
    "Nuevo León": "NUEVO LEON",
    "Oaxaca": "OAXACA",
    "Puebla": "PUEBLA",
    "Querétaro": "QUERETARO",
    "Quintana Roo": "QUINTANA ROO",
    "San Luis Potosí": "SAN LUIS POTOSI",
    "Sinaloa": "SINALOA",
    "Sonora": "SONORA",
    "Tabasco": "TABASCO",
    "Tamaulipas": "TAMAULIPAS",
    "Tlaxcala": "TLAXCALA",
    "Veracruz de Ignacio de la Llave": "VERACRUZ",
    "Yucatán": "YUCATAN",
    "Zacatecas": "ZACATECAS",
  };

  const features = raw.features.map((f) => {
    const geom = f.geometry;
    const coordinates = geom.coordinates.map((polygon) =>
      polygon.map((ring) => simplifyRing(ring, BUDGET_PER_RING))
    );
    return {
      type: "Feature",
      properties: {
        cvegeo: f.properties.cvegeo,
        nom_agee: f.properties.nom_agee,
        nom_abrev: f.properties.nom_abrev,
        edonom: NAME_TO_EDONOM[f.properties.nom_agee] || "",
      },
      geometry: { type: geom.type, coordinates },
    };
  });

  const out = {
    type: "FeatureCollection",
    features,
    meta: {
      source: "INEGI-geojson (MacWilliXD/INEGI-geojson) · AGEE.geojson",
      license: "INEGI datos abiertos",
      decimated: true,
      budget_per_ring: BUDGET_PER_RING,
    },
  };

  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(out));
  const sizeKB = (fs.statSync(OUT).size / 1024).toFixed(0);
  let totalPoints = 0;
  features.forEach((f) => {
    f.geometry.coordinates.forEach((p) => p.forEach((r) => (totalPoints += r.length)));
  });
  console.log(`Wrote ${OUT} — ${features.length} estados, ${sizeKB} KB, ${totalPoints} total points`);
}

main();