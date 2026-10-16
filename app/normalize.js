// Mirrors scripts/normalize.py; both must pass scripts/normalize_cases.json.
export const LEGAL_SUFFIXES = new Set([
  "LLC", "LTD", "LIMITED", "INC", "INCORPORATED", "CORP", "CORPORATION",
  "CO", "COMPANY", "PLC", "GMBH", "SA", "SAS", "SARL", "SRL", "SPA",
  "BV", "NV", "AG", "KG", "OY", "AB", "AS", "PTY", "PJSC", "JSC",
  "OJSC", "PAO", "ZAO", "OOO", "OAO", "PC", "LP", "LLP", "SDN", "BHD",
  "KFT", "DOO", "EOOD", "AD", "SP", "ZOO", "TOO",
]);

export function normalizeName(name) {
  if (!name) return "";
  return name
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")
    .replace(/[^\x00-\x7F]/g, "")
    .toUpperCase()
    .replace(/[^A-Z0-9_\s]/g, " ")
    .split(/\s+/)
    .filter((t) => t && !LEGAL_SUFFIXES.has(t))
    .join(" ");
}

export function parseImo(text) {
  const match = /^\s*(?:IMO\s*)?(\d{7})\s*$/i.exec(text || "");
  return match ? match[1] : null;
}
