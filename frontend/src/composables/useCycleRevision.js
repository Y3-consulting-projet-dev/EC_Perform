import { reactive } from 'vue'

// État partagé de la révision d'un cycle (Phase 4) et de sa revue (Phase 5). Les 9 écrans
// d'un même cycle lisent et modifient la même entrée, mise en cache par `missionId:code`,
// ce qui évite de recharger le cycle à chaque changement d'onglet.

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const ETAPES = [
  { code: '4a', stepId: 'prise-connaissance', label: 'Prise de connaissance' },
  { code: '4b', stepId: 'lead-cycle', label: 'Lead du cycle' },
  { code: '4c', stepId: 'justification-solde', label: 'Justification du solde' },
  { code: '4d', stepId: 'controle-detaille', label: 'Contrôles détaillés' },
  { code: '4e', stepId: 'constats-risques', label: 'Constats / Risques' },
  { code: '4f', stepId: 'conclusion-cycle', label: 'Conclusion du cycle' },
]

export const NIVEAUX = [
  { code: 'senior', stepId: 'revue-senior', label: 'Senior' },
  { code: 'manager', stepId: 'revue-manager', label: 'Manager' },
  { code: 'associe', stepId: 'revue-associe', label: 'Associé' },
]

const AUTOSAVE_DELAY_MS = 800

function authHeaders(json = true) {
  const headers = { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
  if (json) headers['Content-Type'] = 'application/json'
  return headers
}

export async function apiFetch(path, { method = 'GET', body, form } = {}) {
  let response
  try {
    response = await fetch(`${apiUrl}${path}`, {
      method,
      headers: authHeaders(!form),
      body: form ?? (body === undefined ? undefined : JSON.stringify(body)),
    })
  } catch {
    throw Object.assign(new Error('Impossible de contacter le serveur.'), { status: 0 })
  }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = Array.isArray(data.detail) ? 'Données invalides.' : data.detail
    throw Object.assign(new Error(detail ?? 'Une erreur est survenue.'), { status: response.status })
  }
  return data
}

export function fileUrl(path) {
  return path ? `${apiUrl}${path}` : null
}

export function newId() {
  return crypto.randomUUID().replaceAll('-', '')
}

// Champs de section renvoyés par le serveur -> corps attendu par PATCH /revision.
const PAYLOADS = {
  priseConnaissance: (r) => r.priseConnaissance,
  lead: (r) => r.lead,
  justification: (r) => ({
    assertions: Object.fromEntries(r.justification.assertions.map((a) => [a.cle, a.coche])),
    pieces: r.justification.pieces,
    commentaire: r.justification.commentaire.texte,
  }),
  constats: (r) => ({ constats: r.constats }),
  conclusion: (r) => ({
    ...r.conclusion,
    ajustements: r.conclusion.ajustements.map((a) => ({ ...a, montant: Number(a.montant) || 0 })),
  }),
}

// Champs calculés côté serveur, toujours rafraîchis après une écriture.
const META_FIELDS = [
  'statut', 'verrouille', 'niveauActif', 'retourDe', 'chaine', 'checklists', 'pointsOuverts',
  'alertes', 'historique', 'droits', 'version', 'updatedAt', 'updatedBy', 'collaborateur',
]

const entries = new Map()
const summaries = new Map()

// Le cache vit dans le module, donc survit à une déconnexion / reconnexion (navigation SPA sans
// rechargement). Il est lié au jeton : un autre utilisateur ne doit jamais hériter des droits
// (`droits`) ni des données chargées pour le précédent.
let cacheToken = null

function checkCacheOwner() {
  const token = localStorage.getItem('access_token')
  if (token !== cacheToken) {
    resetRevisionCache()
    cacheToken = token
  }
}

export function resetRevisionCache() {
  entries.clear()
  summaries.clear()
}

function createEntry(missionId, code) {
  const timers = {}
  const editSeq = {}
  let saveChain = Promise.resolve()

  const entry = reactive({
    missionId,
    code,
    revision: null,
    points: [],
    loading: false,
    error: '',
    conflict: false,
    saving: 0,
    lastSavedAt: null,

    async load() {
      entry.loading = true
      entry.error = ''
      entry.conflict = false
      try {
        const [revision, points] = await Promise.all([
          apiFetch(`/missions/${missionId}/cycles/${code}/revision`),
          apiFetch(`/missions/${missionId}/cycles/${code}/points`),
        ])
        entry.revision = revision
        entry.points = points
      } catch (e) {
        entry.error = e.message
      } finally {
        entry.loading = false
      }
    },

    async ensureLoaded() {
      if (!entry.revision && !entry.loading) await entry.load()
    },

    async reloadPoints() {
      entry.points = await apiFetch(`/missions/${missionId}/cycles/${code}/points`)
    },

    applyMeta(revision) {
      for (const field of META_FIELDS) entry.revision[field] = revision[field]
    },

    // Enregistrement automatique : chaque modification relance un délai par section, puis les
    // écritures partent l'une après l'autre (la version renvoyée sert à l'écriture suivante).
    scheduleSave(section) {
      editSeq[section] = (editSeq[section] ?? 0) + 1
      clearTimeout(timers[section])
      timers[section] = setTimeout(() => entry.flush(section), AUTOSAVE_DELAY_MS)
    },

    flush(section) {
      clearTimeout(timers[section])
      delete timers[section]
      saveChain = saveChain.then(() => entry.saveNow(section))
      return saveChain
    },

    async saveNow(section) {
      if (!entry.revision || entry.conflict) return
      const seq = editSeq[section]
      entry.saving += 1
      try {
        const revision = await apiFetch(`/missions/${missionId}/cycles/${code}/revision`, {
          method: 'PATCH',
          body: { section, data: PAYLOADS[section](entry.revision), version: entry.revision.version },
        })
        entry.applyMeta(revision)
        // On ne remplace la section que si l'utilisateur ne l'a pas modifiée pendant l'envoi
        // (sinon sa saisie en cours serait écrasée) ; les horodatages arrivent à l'écriture suivante.
        if (editSeq[section] === seq) entry.revision[section] = revision[section]
        entry.lastSavedAt = revision.updatedAt
        entry.error = ''
        refreshSummary(missionId)
      } catch (e) {
        entry.error = e.message
        if (e.status === 409) entry.conflict = true
      } finally {
        entry.saving -= 1
      }
    },

    async flushAll() {
      await Promise.all(Object.keys(timers).map((section) => entry.flush(section)))
      await saveChain
    },

    async action(path, { method = 'POST', body } = {}) {
      await entry.flushAll()
      const revision = await apiFetch(`/missions/${missionId}/cycles/${code}${path}`, { method, body: body ?? {} })
      entry.revision = revision
      await entry.reloadPoints()
      refreshSummary(missionId)
      return revision
    },

    soumettre() {
      return entry.action('/revision/soumettre')
    },
    valider(niveau) {
      return entry.action(`/revue/${niveau}/valider`)
    },
    retour(niveau, commentaire) {
      return entry.action(`/revue/${niveau}/retour`, { body: { commentaire } })
    },
    async cocherChecklist(niveau, cle, coche) {
      const revision = await apiFetch(`/missions/${missionId}/cycles/${code}/revue/${niveau}/checklist`, {
        method: 'PATCH',
        body: { items: { [cle]: coche } },
      })
      entry.applyMeta(revision)
    },

    async creerPoint(niveau, corps, cible) {
      const point = await apiFetch(`/missions/${missionId}/cycles/${code}/points`, {
        method: 'POST',
        body: { niveau, corps, cible },
      })
      entry.points.push(point)
      refreshSummary(missionId)
      return point
    },
    async repondre(pointId, texte, ptRef, fichiers) {
      const form = new FormData()
      form.append('texte', texte)
      form.append('ptRef', ptRef)
      for (const fichier of fichiers) form.append('fichiers', fichier)
      const point = await apiFetch(`/missions/${missionId}/cycles/${code}/points/${pointId}/reponses`, {
        method: 'POST',
        form,
      })
      entry.replacePoint(point)
    },
    async changerStatutPoint(pointId, statut) {
      const point = await apiFetch(`/missions/${missionId}/cycles/${code}/points/${pointId}`, {
        method: 'PATCH',
        body: { statut },
      })
      entry.replacePoint(point)
      refreshSummary(missionId)
    },
    replacePoint(point) {
      const index = entry.points.findIndex((p) => p.id === point.id)
      if (index >= 0) entry.points[index] = point
    },
  })
  return entry
}

export function getCycleRevision(missionId, code) {
  checkCacheOwner()
  const key = `${missionId}:${code}`
  if (!entries.has(key)) entries.set(key, createEntry(missionId, code))
  return entries.get(key)
}

// Résumé de tous les cycles de la mission (statut, points ouverts, alertes) pour le sélecteur.
export function getMissionRevisions(missionId) {
  checkCacheOwner()
  if (!summaries.has(missionId)) {
    summaries.set(missionId, reactive({ cycles: [], loaded: false, error: '' }))
    refreshSummary(missionId)
  }
  return summaries.get(missionId)
}

export async function refreshSummary(missionId) {
  const summary = summaries.get(missionId)
  if (!summary) return
  try {
    summary.cycles = await apiFetch(`/missions/${missionId}/revisions`)
    summary.loaded = true
    summary.error = ''
  } catch (e) {
    summary.error = e.message
  }
}

export function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.toLocaleDateString('fr-FR')} ${date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}`
}

export function formatNumber(n) {
  if (n === null || n === undefined || n === '') return '—'
  const rounded = Math.round(Number(n))
  if (Number.isNaN(rounded)) return n
  const sign = rounded < 0 ? '-' : ''
  return sign + Math.abs(rounded).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
}
