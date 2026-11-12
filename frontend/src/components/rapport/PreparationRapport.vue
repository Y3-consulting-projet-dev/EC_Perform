<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  api,
  formatMontant,
  imageObjectUrl,
  nouvelId,
  parseCollage,
  parseMontant,
} from '../../composables/useRapport'

// Saisie complémentaire du rapport final : tout ce que le rapport contient sans source dans les
// phases 1 à 5. Rien n'est pré-rédigé : un champ vide fait simplement disparaître l'élément du
// rapport. Enregistrement explicite (verrouillage optimiste côté serveur).
const props = defineProps({
  missionId: { type: String, required: true },
  rapport: { type: Object, default: null },
})
const emit = defineEmits(['rapport', 'enregistre'])

const ONGLETS = [
  { id: 'generalites', label: 'Généralités' },
  { id: 'ci', label: 'Contrôle interne' },
  { id: 'points', label: 'Points par cycle' },
  { id: 'ecritures', label: 'Écritures' },
]
const TYPES_BLOC = [
  { id: 'balance', label: 'Extrait de balance' },
  { id: 'variation', label: 'Tableau de variation' },
  { id: 'papier', label: 'Feuille de papier de travail' },
  { id: 'ecriture', label: 'Écriture proposée' },
  { id: 'grand_livre', label: 'Extrait du grand livre' },
  { id: 'tableau', label: 'Tableau libre' },
]
const COLONNES_GL = ['Date', 'Journal', 'N° pièce', 'Compte', 'Compte tiers', 'Libellé', 'Débit', 'Crédit']
const FAMILLES_CI = ["Gouvernance", "Système d'information"]

const onglet = ref('generalites')
const chargement = ref(false)
const erreur = ref('')
const message = ref('')
const enregistrement = ref(false)
const saisie = ref(null)
const version = ref(0)
const modifiable = ref(false)
const referentiels = ref({ cycles: [], constats: [], ajustements: [], papiers: [] })
const initial = ref('')
const cycleActif = ref('A')
const collages = reactive({}) // texte collé par bloc (non enregistré)
const enTetes = reactive({}) // tableau libre : 1re ligne = en-têtes
const apercus = reactive({ logo: null, photo: null })
const depotMedia = ref('')

const modifie = computed(() => saisie.value && JSON.stringify(saisie.value) !== initial.value)
const libelleCycle = (code) => referentiels.value.cycles.find((c) => c.code === code)?.libelle ?? code
const ajustementsParId = computed(() => Object.fromEntries(referentiels.value.ajustements.map((a) => [a.id, a])))

function appliquer(data) {
  const s = data.saisie
  s.evenements ??= []
  s.constats ??= {}
  s.points ??= {}
  s.ecritures ??= []
  s.lettreMission ??= { date: '', prestations: '' }
  // Entrées créées ici (et non au rendu) pour que l'état initial serve de référence « non modifié ».
  for (const c of data.referentiels.constats) s.constats[c.id] ??= { titre: '', risques: [], retenirCI: null }
  for (const c of data.referentiels.cycles) s.points[c.code] ??= []
  saisie.value = s
  version.value = data.version
  modifiable.value = data.modifiable
  referentiels.value = data.referentiels
  initial.value = JSON.stringify(s)
}

async function charger() {
  chargement.value = true
  erreur.value = ''
  try {
    appliquer(await api(`/missions/${props.missionId}/rapport/saisie`))
  } catch (e) {
    erreur.value = e.message
  } finally {
    chargement.value = false
  }
}

async function enregistrer() {
  enregistrement.value = true
  erreur.value = ''
  message.value = ''
  try {
    appliquer(
      await api(`/missions/${props.missionId}/rapport/saisie`, {
        method: 'PUT',
        body: { saisie: saisie.value, version: version.value },
      }),
    )
    message.value = 'Saisie enregistrée. Régénérez le rapport pour l’y intégrer.'
    emit('enregistre')
  } catch (e) {
    erreur.value = e.message
  } finally {
    enregistrement.value = false
  }
}

onMounted(charger)

// --- Médias ---------------------------------------------------------------------------------

async function rafraichirApercus() {
  for (const cle of ['logo', 'photo']) {
    if (apercus[cle]) URL.revokeObjectURL(apercus[cle])
    apercus[cle] = props.rapport?.medias?.[cle]
      ? await imageObjectUrl(`/missions/${props.missionId}/rapport/medias/${cle}`)
      : null
  }
}
watch(() => JSON.stringify(props.rapport?.medias ?? {}), rafraichirApercus, { immediate: true })

async function deposerMedia(cle, event) {
  const fichier = event.target.files?.[0]
  event.target.value = ''
  if (!fichier) return
  depotMedia.value = cle
  erreur.value = ''
  try {
    const form = new FormData()
    form.append('fichier', fichier)
    emit('rapport', await api(`/missions/${props.missionId}/rapport/medias/${cle}`, { method: 'POST', form }))
  } catch (e) {
    erreur.value = e.message
  } finally {
    depotMedia.value = ''
  }
}

async function supprimerMedia(cle) {
  try {
    emit('rapport', await api(`/missions/${props.missionId}/rapport/medias/${cle}`, { method: 'DELETE' }))
  } catch (e) {
    erreur.value = e.message
  }
}

// --- Contrôle interne -----------------------------------------------------------------------

function saisieConstat(id) {
  saisie.value.constats[id] ??= { titre: '', risques: [], retenirCI: null }
  return saisie.value.constats[id]
}

function estRetenu(constat) {
  const choix = saisie.value.constats[constat.id]?.retenirCI
  return choix === null || choix === undefined ? FAMILLES_CI.includes(constat.famille) : choix
}

function ajouterRisque(constat, texte = '') {
  const s = saisieConstat(constat.id)
  if (texte && s.risques.includes(texte)) return
  s.risques.push(texte)
}

// --- Points par cycle -----------------------------------------------------------------------

const pointsCycle = computed(() => saisie.value?.points[cycleActif.value] ?? [])

function ajouterPoint() {
  pointsCycle.value.push({ id: nouvelId(), titre: '', texte: '', blocs: [] })
}

function deplacer(liste, index, delta) {
  const cible = index + delta
  if (cible < 0 || cible >= liste.length) return
  const [element] = liste.splice(index, 1)
  liste.splice(cible, 0, element)
}

function ajouterBloc(point, type) {
  const bloc = { id: nouvelId(), type, titre: '', prefixes: [], colonnes: [], lignes: [] }
  if (type === 'grand_livre') bloc.grandLivre = { source: 'saisie', filtre: { comptes: [], du: '', au: '' }, lignes: [] }
  if (type === 'tableau') enTetes[bloc.id] = true
  point.blocs.push(bloc)
}

function prefixesTexte(bloc) {
  return (bloc.prefixes ?? []).join(', ')
}
function majPrefixes(bloc, texte) {
  bloc.prefixes = texte.split(/[,;\s]+/).filter(Boolean)
}

function appliquerCollage(bloc) {
  const lignes = parseCollage(collages[bloc.id])
  if (bloc.type === 'tableau') {
    const avecEntetes = enTetes[bloc.id] ?? true
    bloc.colonnes = avecEntetes ? (lignes[0] ?? []) : []
    bloc.lignes = avecEntetes ? lignes.slice(1) : lignes
  } else if (bloc.type === 'grand_livre') {
    // Ligne d'en-têtes éventuelle ignorée : une ligne sans aucun montant n'est pas une écriture.
    bloc.grandLivre.lignes = lignes
      .map((c) => ({
        date: c[0] ?? '', journal: c[1] ?? '', piece: c[2] ?? '', compte: c[3] ?? '', compteTiers: c[4] ?? '',
        libelle: c[5] ?? '', debit: parseMontant(c[6]), credit: parseMontant(c[7]),
      }))
      .filter((l) => l.debit !== null || l.credit !== null)
  }
  collages[bloc.id] = ''
}

function totauxGrandLivre(bloc) {
  const lignes = bloc.grandLivre?.lignes ?? []
  return {
    debit: lignes.reduce((s, l) => s + (l.debit ?? 0), 0),
    credit: lignes.reduce((s, l) => s + (l.credit ?? 0), 0),
  }
}

function feuillesPapier(paperId) {
  return referentiels.value.papiers.find((p) => p.id === paperId)?.feuilles ?? []
}

const ecrituresCycle = computed(() =>
  (saisie.value?.ecritures ?? []).filter((e) => e.cycleCode === cycleActif.value && e.id),
)

// --- Écritures ------------------------------------------------------------------------------

function ajouterEcriture() {
  saisie.value.ecritures.push({ id: null, cycleCode: cycleActif.value, libelle: '', ajustementIds: [] })
}

function ajustementsDisponibles(ecriture) {
  const ailleurs = new Set(
    saisie.value.ecritures.filter((e) => e !== ecriture).flatMap((e) => e.ajustementIds),
  )
  return referentiels.value.ajustements.filter((a) => a.cycleCode === ecriture.cycleCode && !ailleurs.has(a.id))
}

function basculerAjustement(ecriture, id) {
  const i = ecriture.ajustementIds.indexOf(id)
  if (i >= 0) ecriture.ajustementIds.splice(i, 1)
  else ecriture.ajustementIds.push(id)
}

function equilibre(ecriture) {
  let debit = 0
  let credit = 0
  for (const id of ecriture.ajustementIds) {
    const a = ajustementsParId.value[id]
    if (!a) continue
    if (a.sens === 'Débit') debit += Number(a.montant || 0)
    else credit += Number(a.montant || 0)
  }
  return { debit, credit, ok: Math.abs(debit - credit) < 0.5 }
}

defineExpose({ modifie })
</script>

<template>
  <div class="rounded-xl bg-white p-5 shadow-sm">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h3 class="text-sm font-bold text-[#0d3b56]">Préparation du rapport</h3>
        <p class="text-xs text-gray-400">
          Éléments absents des phases 1 à 5. Un champ laissé vide est omis du rapport.
        </p>
      </div>
      <div class="flex items-center gap-3">
        <span v-if="modifie" class="text-xs font-semibold text-[#c9862c]">Modifications non enregistrées</span>
        <button
          type="button"
          :disabled="!modifiable || !modifie || enregistrement"
          class="rounded-lg bg-[#0d3b56] px-4 py-2 text-sm font-semibold text-white hover:bg-[#0a2f45] disabled:opacity-50"
          @click="enregistrer"
        >
          {{ enregistrement ? 'Enregistrement...' : 'Enregistrer' }}
        </button>
      </div>
    </div>

    <p v-if="erreur" class="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">{{ erreur }}</p>
    <p v-if="message" class="mt-3 rounded-lg bg-[#eef6e6] px-3 py-2 text-xs text-[#5a8a2c]">{{ message }}</p>
    <p v-if="saisie && !modifiable" class="mt-3 rounded-lg bg-[#fbeee0] px-3 py-2 text-xs text-[#c9862c]">
      Lecture seule : rapport émis, ou vous n'êtes pas affecté(e) à la mission.
    </p>
    <p v-if="chargement && !saisie" class="mt-3 text-sm text-gray-400">Chargement...</p>

    <template v-if="saisie">
      <div class="mt-4 flex flex-wrap gap-1 border-b border-gray-100">
        <button
          v-for="o in ONGLETS"
          :key="o.id"
          type="button"
          class="rounded-t-lg px-4 py-2 text-sm font-semibold transition"
          :class="onglet === o.id ? 'bg-[#0d3b56] text-white' : 'text-[#2f5875] hover:bg-[#eef2f6]'"
          @click="onglet = o.id"
        >
          {{ o.label }}
        </button>
      </div>

      <fieldset :disabled="!modifiable" class="mt-4 space-y-5">
        <!-- Généralités -->
        <template v-if="onglet === 'generalites'">
          <div class="grid gap-4 md:grid-cols-3">
            <label class="block text-xs font-semibold text-gray-600">
              Date du rapport (couverture)
              <input v-model="saisie.dateRapport" type="month" class="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
              <span class="font-normal text-gray-400">Vide : mois de génération.</span>
            </label>
            <label class="block text-xs font-semibold text-gray-600">
              Date de la lettre de mission
              <input v-model="saisie.lettreMission.date" type="text" placeholder="ex. 15 janvier 2026" class="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
            </label>
            <label class="block text-xs font-semibold text-gray-600 md:col-span-1">
              Prestations (lettre de mission)
              <input v-model="saisie.lettreMission.prestations" type="text" placeholder="ex. une mission de révision des comptes" class="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
            </label>
          </div>
          <label class="block text-xs font-semibold text-gray-600">
            Complément au contexte de la mission
            <textarea v-model="saisie.contexteComplement" rows="3" class="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
          </label>
          <label class="block text-xs font-semibold text-gray-600">
            Actionnariat
            <textarea v-model="saisie.actionnariat" rows="3" placeholder="Une ligne par actionnaire. Vide : associés de la fiche signalétique." class="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
          </label>
          <label class="block text-xs font-semibold text-gray-600">
            Commentaire sur l'intangibilité du bilan
            <textarea v-model="saisie.intangibiliteCommentaire" rows="2" class="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
          </label>

          <div>
            <div class="flex items-center justify-between">
              <p class="text-xs font-bold text-[#0d3b56]">Évènements significatifs</p>
              <button type="button" class="text-xs font-semibold text-[#2c6e8f] hover:underline" @click="saisie.evenements.push({ id: nouvelId(), titre: '', texte: '' })">
                + Ajouter un évènement
              </button>
            </div>
            <p v-if="!saisie.evenements.length" class="mt-2 text-xs text-gray-400">Aucun : la slide est omise.</p>
            <div v-for="(e, i) in saisie.evenements" :key="e.id ?? i" class="mt-2 space-y-2 rounded-lg border border-gray-100 p-3">
              <div class="flex gap-2">
                <input v-model="e.titre" type="text" placeholder="Titre" class="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm" />
                <button type="button" class="text-xs text-red-500 hover:underline" @click="saisie.evenements.splice(i, 1)">Retirer</button>
              </div>
              <textarea v-model="e.texte" rows="3" placeholder="Description" class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
            </div>
          </div>

          <div class="grid gap-4 md:grid-cols-2">
            <div v-for="cle in ['logo', 'photo']" :key="cle" class="rounded-lg border border-gray-100 p-3">
              <p class="text-xs font-bold text-[#0d3b56]">{{ cle === 'logo' ? 'Logo du client (couverture)' : 'Photo du client (séparateurs)' }}</p>
              <img v-if="apercus[cle]" :src="apercus[cle]" alt="" class="mt-2 h-20 rounded object-contain" />
              <p v-else class="mt-2 text-xs text-gray-400">Aucune image : l'emplacement est omis.</p>
              <div class="mt-2 flex items-center gap-3">
                <label class="cursor-pointer text-xs font-semibold text-[#2c6e8f] hover:underline">
                  {{ depotMedia === cle ? 'Envoi...' : 'Déposer une image (PNG, JPG)' }}
                  <input type="file" accept=".png,.jpg,.jpeg" class="hidden" :disabled="!modifiable" @change="deposerMedia(cle, $event)" />
                </label>
                <button v-if="rapport?.medias?.[cle]" type="button" class="text-xs text-red-500 hover:underline" @click="supprimerMedia(cle)">Retirer</button>
              </div>
            </div>
          </div>
        </template>

        <!-- Contrôle interne -->
        <template v-if="onglet === 'ci'">
          <p class="text-xs text-gray-500">
            Constats saisis en Phase 4. Les constats retenus font l'objet d'une fiche dans la partie
            « Appréciation du dispositif de contrôle interne » (par défaut : familles Gouvernance et
            Système d'information). Les commentaires du client sont saisis dans la Restitution client.
          </p>
          <p v-if="!referentiels.constats.length" class="text-sm text-gray-400">Aucun constat en Phase 4.</p>
          <div v-for="c in referentiels.constats" :key="c.id" class="space-y-2 rounded-lg border border-gray-100 p-3">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <p class="text-xs font-bold text-[#0d3b56]">
                {{ c.cycleCode }} – {{ libelleCycle(c.cycleCode) }} · {{ c.famille }} · {{ c.severite }}
              </p>
              <label class="flex items-center gap-2 text-xs font-semibold text-gray-600">
                <input
                  type="checkbox"
                  :checked="estRetenu(c)"
                  @change="saisieConstat(c.id).retenirCI = $event.target.checked"
                />
                Retenir dans le contrôle interne
              </label>
            </div>
            <p class="text-sm text-gray-700">{{ c.constat }}</p>
            <input
              v-model="saisieConstat(c.id).titre"
              type="text"
              placeholder="Titre court (ex. Absence d'inventaire de caisse)"
              class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
            />
            <div>
              <p class="text-xs font-semibold text-gray-600">Risques</p>
              <div v-for="(r, i) in saisieConstat(c.id).risques" :key="i" class="mt-1 flex gap-2">
                <input v-model="saisieConstat(c.id).risques[i]" type="text" class="flex-1 rounded-lg border border-gray-200 px-3 py-1.5 text-sm" />
                <button type="button" class="text-xs text-red-500 hover:underline" @click="saisieConstat(c.id).risques.splice(i, 1)">Retirer</button>
              </div>
              <div class="mt-1 flex flex-wrap items-center gap-2">
                <button type="button" class="text-xs font-semibold text-[#2c6e8f] hover:underline" @click="ajouterRisque(c)">+ Risque</button>
                <button
                  v-for="r in c.risquesCycle ?? []"
                  :key="r"
                  type="button"
                  class="rounded-full bg-[#eef2f6] px-2 py-0.5 text-[11px] text-[#2f5875] hover:bg-[#dce6ee]"
                  title="Risque identifié en prise de connaissance (4a)"
                  @click="ajouterRisque(c, r)"
                >
                  + {{ r }}
                </button>
              </div>
            </div>
          </div>
        </template>

        <!-- Points par cycle -->
        <template v-if="onglet === 'points'">
          <div class="flex flex-wrap gap-1">
            <button
              v-for="c in referentiels.cycles"
              :key="c.code"
              type="button"
              class="rounded-lg px-3 py-1.5 text-xs font-semibold"
              :class="cycleActif === c.code ? 'bg-[#0d3b56] text-white' : 'bg-[#eef2f6] text-[#2f5875] hover:bg-[#dce6ee]'"
              :title="c.libelle"
              @click="cycleActif = c.code"
            >
              {{ c.code }}<span v-if="saisie.points[c.code]?.length"> · {{ saisie.points[c.code].length }}</span>
            </button>
          </div>
          <p class="text-xs text-gray-500">
            Le chapitre {{ cycleActif }} – {{ libelleCycle(cycleActif) }} reprend automatiquement la synthèse (4f),
            l'extrait de balance, les constats et les écritures. Ajoutez ici les points détaillés du rapport.
          </p>

          <div v-for="(p, i) in pointsCycle" :key="p.id" class="space-y-3 rounded-lg border border-gray-200 p-4">
            <div class="flex flex-wrap items-center gap-2">
              <input v-model="p.titre" type="text" placeholder="Titre du point (obligatoire)" class="min-w-[240px] flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm font-semibold" />
              <button type="button" class="text-xs text-gray-500 hover:underline" @click="deplacer(pointsCycle, i, -1)">↑</button>
              <button type="button" class="text-xs text-gray-500 hover:underline" @click="deplacer(pointsCycle, i, 1)">↓</button>
              <button type="button" class="text-xs text-red-500 hover:underline" @click="pointsCycle.splice(i, 1)">Retirer le point</button>
            </div>
            <textarea v-model="p.texte" rows="4" placeholder="Texte d'analyse (repris tel quel dans le rapport)" class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />

            <div v-for="(b, j) in p.blocs" :key="b.id" class="space-y-2 rounded-lg bg-[#f6f8fa] p-3">
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-xs font-bold text-[#0d3b56]">{{ TYPES_BLOC.find((t) => t.id === b.type)?.label }}</span>
                <input v-model="b.titre" type="text" placeholder="Légende (facultative)" class="min-w-[200px] flex-1 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs" />
                <button type="button" class="text-xs text-gray-500 hover:underline" @click="deplacer(p.blocs, j, -1)">↑</button>
                <button type="button" class="text-xs text-gray-500 hover:underline" @click="deplacer(p.blocs, j, 1)">↓</button>
                <button type="button" class="text-xs text-red-500 hover:underline" @click="p.blocs.splice(j, 1)">Retirer</button>
              </div>

              <label v-if="b.type === 'balance' || b.type === 'variation'" class="block text-xs text-gray-600">
                Préfixes de comptes (vide = tout le cycle)
                <input :value="prefixesTexte(b)" type="text" placeholder="ex. 401, 408" class="mt-1 w-full rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs" @change="majPrefixes(b, $event.target.value)" />
              </label>

              <div v-if="b.type === 'papier'" class="grid gap-2 md:grid-cols-2">
                <select v-model="b.paperId" class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs" @change="b.feuille = feuillesPapier(b.paperId)[0] ?? null">
                  <option :value="null" disabled>Papier de travail</option>
                  <option v-for="pt in referentiels.papiers" :key="pt.id" :value="pt.id">{{ pt.cycleCode }} · {{ pt.etape }} — {{ pt.titre }}</option>
                </select>
                <select v-model="b.feuille" class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs">
                  <option :value="null" disabled>Onglet</option>
                  <option v-for="f in feuillesPapier(b.paperId)" :key="f" :value="f">{{ f }}</option>
                </select>
              </div>

              <select v-if="b.type === 'ecriture'" v-model="b.ecritureId" class="w-full rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs">
                <option :value="null" disabled>Écriture (onglet Écritures, enregistrée)</option>
                <option v-for="e in ecrituresCycle" :key="e.id" :value="e.id">{{ e.libelle || 'Sans libellé' }}</option>
              </select>

              <template v-if="b.type === 'tableau' || b.type === 'grand_livre'">
                <p v-if="b.type === 'grand_livre'" class="text-[11px] text-gray-500">
                  Collez depuis Excel les colonnes dans cet ordre : {{ COLONNES_GL.join(' · ') }}.
                </p>
                <textarea v-model="collages[b.id]" rows="3" placeholder="Collez ici les cellules copiées depuis Excel" class="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 font-mono text-xs" />
                <div class="flex items-center gap-3">
                  <label v-if="b.type === 'tableau'" class="flex items-center gap-1 text-xs text-gray-600">
                    <input v-model="enTetes[b.id]" type="checkbox" :true-value="true" :false-value="false" />
                    1re ligne = en-têtes
                  </label>
                  <button type="button" :disabled="!collages[b.id]" class="rounded-lg bg-[#2c6e8f] px-3 py-1 text-xs font-semibold text-white disabled:opacity-50" @click="appliquerCollage(b)">
                    Importer le collage
                  </button>
                </div>
                <div v-if="b.type === 'tableau' && (b.colonnes.length || b.lignes.length)" class="max-h-48 overflow-auto rounded border border-gray-200 bg-white">
                  <table class="w-full text-[11px]">
                    <thead v-if="b.colonnes.length" class="bg-[#0d3b56] text-white">
                      <tr><th v-for="(h, k) in b.colonnes" :key="k" class="px-2 py-1 text-left">{{ h }}</th></tr>
                    </thead>
                    <tbody>
                      <tr v-for="(l, k) in b.lignes" :key="k" class="border-t border-gray-100">
                        <td v-for="(v, m) in l" :key="m" class="px-2 py-0.5">{{ v }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-if="b.type === 'grand_livre' && b.grandLivre?.lignes.length" class="max-h-48 overflow-auto rounded border border-gray-200 bg-white">
                  <table class="w-full text-[11px]">
                    <thead class="bg-[#0d3b56] text-white">
                      <tr><th v-for="h in COLONNES_GL" :key="h" class="px-2 py-1 text-left">{{ h }}</th></tr>
                    </thead>
                    <tbody>
                      <tr v-for="(l, k) in b.grandLivre.lignes" :key="k" class="border-t border-gray-100">
                        <td class="px-2 py-0.5">{{ l.date }}</td><td class="px-2">{{ l.journal }}</td><td class="px-2">{{ l.piece }}</td>
                        <td class="px-2">{{ l.compte }}</td><td class="px-2">{{ l.compteTiers }}</td><td class="px-2">{{ l.libelle }}</td>
                        <td class="px-2 text-right">{{ formatMontant(l.debit) }}</td><td class="px-2 text-right">{{ formatMontant(l.credit) }}</td>
                      </tr>
                      <tr class="border-t border-gray-300 font-bold">
                        <td colspan="6" class="px-2 py-0.5">Total</td>
                        <td class="px-2 text-right">{{ formatMontant(totauxGrandLivre(b).debit) }}</td>
                        <td class="px-2 text-right">{{ formatMontant(totauxGrandLivre(b).credit) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </template>
            </div>

            <div class="flex flex-wrap items-center gap-2">
              <span class="text-xs text-gray-500">Ajouter :</span>
              <button v-for="t in TYPES_BLOC" :key="t.id" type="button" class="rounded-full bg-[#eef2f6] px-2.5 py-1 text-[11px] font-semibold text-[#2f5875] hover:bg-[#dce6ee]" @click="ajouterBloc(p, t.id)">
                + {{ t.label }}
              </button>
            </div>
          </div>
          <button type="button" class="rounded-lg border border-dashed border-[#2c6e8f] px-4 py-2 text-sm font-semibold text-[#2c6e8f] hover:bg-[#eef2f6]" @click="ajouterPoint">
            + Ajouter un point au cycle {{ cycleActif }}
          </button>
        </template>

        <!-- Écritures -->
        <template v-if="onglet === 'ecritures'">
          <p class="text-xs text-gray-500">
            Regroupez les ajustements de la conclusion du cycle (4f) en écritures équilibrées. Les ajustements non
            regroupés figurent tels quels dans le rapport. Partie « Travaux de régularisation » : récapitulatif de
            toutes les écritures.
          </p>
          <p v-if="!referentiels.ajustements.length" class="text-sm text-gray-400">Aucun ajustement en Phase 4.</p>
          <div v-for="(e, i) in saisie.ecritures" :key="e.id ?? `n${i}`" class="space-y-2 rounded-lg border border-gray-200 p-3">
            <div class="flex flex-wrap items-center gap-2">
              <select v-model="e.cycleCode" class="rounded-lg border border-gray-200 px-2 py-1.5 text-xs" @change="e.ajustementIds = []">
                <option v-for="c in referentiels.cycles" :key="c.code" :value="c.code">{{ c.code }} – {{ c.libelle }}</option>
              </select>
              <input v-model="e.libelle" type="text" placeholder="Libellé de l'écriture" class="min-w-[220px] flex-1 rounded-lg border border-gray-200 px-3 py-1.5 text-sm" />
              <span
                class="rounded-full px-2 py-0.5 text-[11px] font-bold"
                :class="equilibre(e).ok && e.ajustementIds.length ? 'bg-[#eef6e6] text-[#5a8a2c]' : 'bg-red-50 text-red-600'"
              >
                D {{ formatMontant(equilibre(e).debit) || 0 }} · C {{ formatMontant(equilibre(e).credit) || 0 }}
                {{ equilibre(e).ok && e.ajustementIds.length ? '· équilibrée' : '· à équilibrer' }}
              </span>
              <button type="button" class="text-xs text-red-500 hover:underline" @click="saisie.ecritures.splice(i, 1)">Retirer</button>
            </div>
            <label v-for="a in ajustementsDisponibles(e)" :key="a.id" class="flex items-center gap-2 text-xs text-gray-700">
              <input type="checkbox" :checked="e.ajustementIds.includes(a.id)" @change="basculerAjustement(e, a.id)" />
              <span class="w-20 font-mono">{{ a.compte }}</span>
              <span class="flex-1">{{ a.libelle }}</span>
              <span class="w-16 text-gray-500">{{ a.sens }}</span>
              <span class="w-28 text-right font-semibold">{{ formatMontant(a.montant) }}</span>
            </label>
            <p v-if="!ajustementsDisponibles(e).length" class="text-xs text-gray-400">Aucun ajustement disponible dans ce cycle.</p>
          </div>
          <button type="button" class="rounded-lg border border-dashed border-[#2c6e8f] px-4 py-2 text-sm font-semibold text-[#2c6e8f] hover:bg-[#eef2f6]" @click="ajouterEcriture">
            + Nouvelle écriture
          </button>
        </template>
      </fieldset>
    </template>
  </div>
</template>
