import { cp, mkdir, access } from "node:fs/promises";
import { createReadStream, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import readline from "node:readline";

const root = resolve(import.meta.dirname, "..");

async function ensureSeccionesSummary() {
  const jsonPath = resolve(root, "outputs/resultadosIntegrados/seccionesPorEntidad.json");
  const csvPath = resolve(root, "outputs/resultadosIntegrados/ccpc_seccionResultadosIntegrados.csv");
  try {
    await access(jsonPath);
  } catch {
    console.log("Generating seccionesPorEntidad.json from section CSV...");
    const fileStream = createReadStream(csvPath);
    const rl = readline.createInterface({ input: fileStream, crlfDelay: Infinity });
    let isHeader = true;
    let edonomIdx = -1;
    const byEntity = {};
    let total = 0;
    for await (const line of rl) {
      if (isHeader) {
        edonomIdx = line.split(",").indexOf("EDONOM");
        isHeader = false;
        continue;
      }
      const parts = line.split(",");
      const edo = parts[edonomIdx];
      if (edo) {
        byEntity[edo] = (byEntity[edo] || 0) + 1;
        total++;
      }
    }
    writeFileSync(jsonPath, JSON.stringify({ total, byEntity }, null, 2));
  }
}

await ensureSeccionesSummary();

const files = [
  "outputs/resultadosIntegrados/ccpc_municipioResultadosIntegrados.csv",
  "outputs/resultadosIntegrados/ccpc_seccionResultadosIntegrados.csv",
  "outputs/resultadosIntegrados/seccionesPorEntidad.json",
];

for (const relativePath of files) {
  const source = resolve(root, relativePath);
  const destination = resolve(root, "dist", relativePath);
  await mkdir(dirname(destination), { recursive: true });
  await cp(source, destination);
}

console.log(`Copied ${files.length} dashboard data sources into dist/.`);
