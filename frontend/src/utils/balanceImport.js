function parseNumber(raw) {
  const cleaned = (raw ?? '').replace(/\s/g, '').replace(',', '.')
  const n = Number(cleaned)
  return Number.isFinite(n) ? n : 0
}

export function parseBalanceCsv(text) {
  const lines = text.split(/\r?\n/).filter((line) => line.trim().length > 0)
  if (lines.length < 2) return []
  return lines
    .slice(1)
    .map((line) => {
      const [compte, libelle, soldeRaw] = line.split(';').map((cell) => cell.trim().replace(/^"|"$/g, ''))
      return { compte: compte ?? '', libelle: libelle ?? '', solde: parseNumber(soldeRaw) }
    })
    .filter((row) => row.compte)
}

export function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsText(file)
  })
}

export function mergeBalances(rowsN, rowsNMoins1) {
  const mapN = new Map(rowsN.map((r) => [r.compte, r]))
  const mapNMoins1 = new Map(rowsNMoins1.map((r) => [r.compte, r]))
  const allComptes = [...new Set([...mapN.keys(), ...mapNMoins1.keys()])].sort()

  return allComptes.map((compte, index) => {
    const rowN = mapN.get(compte)
    const rowNMoins1 = mapNMoins1.get(compte)
    let statut = 'Existant'
    if (rowN && !rowNMoins1) statut = 'Nouveau'
    if (!rowN && rowNMoins1) statut = 'Disparu'
    return {
      n: index + 1,
      compte,
      libelle: rowN?.libelle ?? rowNMoins1?.libelle ?? '',
      soldeN: rowN?.solde ?? 0,
      soldeNMoins1: rowNMoins1?.solde ?? 0,
      statut,
    }
  })
}
