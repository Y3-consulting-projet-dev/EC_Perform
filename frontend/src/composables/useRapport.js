// Phase 6 (restitution client, émission du rapport final) : appels API et utilitaires partagés.

const apiUrl = import.meta.env.VITE_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`

function authHeaders(json = true) {
  const headers = { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
  if (json) headers['Content-Type'] = 'application/json'
  return headers
}

// Comme apiFetch (useCycleRevision), mais conserve le code d'erreur métier quand le backend
// renvoie un détail structuré { code, message } (ex. régénération bloquée).
export async function api(path, { method = 'GET', body, form, params } = {}) {
  const query = params ? `?${new URLSearchParams(params)}` : ''
  let response
  try {
    response = await fetch(`${apiUrl}${path}${query}`, {
      method,
      headers: authHeaders(!form),
      body: form ?? (body === undefined ? undefined : JSON.stringify(body)),
    })
  } catch {
    throw Object.assign(new Error('Impossible de contacter le serveur.'), { status: 0 })
  }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = data.detail
    let message = 'Une erreur est survenue.'
    let code = null
    if (typeof detail === 'string') message = detail
    else if (Array.isArray(detail)) message = detail.map((d) => d.msg).join(' · ') || 'Données invalides.'
    else if (detail && typeof detail === 'object') {
      message = detail.message ?? message
      code = detail.code ?? null
    }
    throw Object.assign(new Error(message), { status: response.status, code })
  }
  return data
}

// Téléchargement d'un fichier protégé par le jeton (les liens directs n'envoient pas l'en-tête).
export async function telecharger(path, nomParDefaut) {
  const response = await fetch(`${apiUrl}${path}`, { headers: authHeaders(false) })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(typeof data.detail === 'string' ? data.detail : 'Téléchargement impossible.')
  }
  const disposition = response.headers.get('Content-Disposition') ?? ''
  const nom = /filename="?([^"]+)"?/.exec(disposition)?.[1] ?? nomParDefaut
  const url = URL.createObjectURL(await response.blob())
  const lien = Object.assign(document.createElement('a'), { href: url, download: nom })
  document.body.appendChild(lien)
  lien.click()
  lien.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export async function imageObjectUrl(path) {
  const response = await fetch(`${apiUrl}${path}`, { headers: authHeaders(false) })
  if (!response.ok) return null
  return URL.createObjectURL(await response.blob())
}

// Collage depuis Excel : lignes séparées par des retours à la ligne, cellules par des tabulations.
export function parseCollage(texte) {
  return (texte ?? '')
    .replace(/\r/g, '')
    .split('\n')
    .filter((ligne) => ligne.trim() !== '')
    .map((ligne) => ligne.split('\t').map((c) => c.trim()))
}

// « 1 234 567,50 » / « -1234567.5 » -> nombre ; vide -> null.
export function parseMontant(valeur) {
  const texte = String(valeur ?? '').replace(/[\s  ]/g, '')
  if (!texte || texte === '-') return null
  const n = Number(texte.replace(',', '.'))
  return Number.isFinite(n) ? n : null
}

export function formatMontant(n) {
  if (n === null || n === undefined || n === '') return ''
  return Math.round(Number(n)).toLocaleString('fr-FR').replace(/ /g, ' ')
}

export const ORIGINES = {
  generation: 'Génération',
  edition_onlyoffice: 'Édition ONLYOFFICE',
  emission: 'Émission',
}

export const STATUTS = {
  genere: { label: 'Généré', classes: 'bg-[#e6f0f7] text-[#2c6e8f]' },
  en_finition: { label: 'En finition', classes: 'bg-[#fbeee0] text-[#c9862c]' },
  emis: { label: 'Émis', classes: 'bg-[#eef6e6] text-[#5a8a2c]' },
}

export function nouvelId() {
  return Math.random().toString(16).slice(2) + Date.now().toString(16)
}
