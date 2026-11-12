<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { formatDateTime } from '../../composables/useCycleRevision'
import { ORIGINES, STATUTS, api, telecharger } from '../../composables/useRapport'
import EditeurOnlyoffice from '../rapport/EditeurOnlyoffice.vue'
import PreparationRapport from '../rapport/PreparationRapport.vue'

// Phase 6 – Émission du rapport final : génération du PPTX depuis les données de la mission,
// finition dans ONLYOFFICE (co-édition, versions), puis émission (version figée, PDF).
const props = defineProps({
  mission: { type: Object, required: true },
})

const rapport = ref(null)
const chargement = ref(false)
const erreur = ref('')
const action = ref('') // 'generer' | 'emettre' | 'pdf'
const editeurOuvert = ref(false)
const confirmation = ref(null) // null | 'regenerer' | 'emettre'
const avertissementRegeneration = ref('')
const attenteEnregistrement = ref(false)
let minuteur = null

const base = computed(() => `/missions/${props.mission.id}/rapport`)
const statut = computed(() => (rapport.value?.statut ? STATUTS[rapport.value.statut] : null))
const aDesVersions = computed(() => !!rapport.value?.versions?.length)
const emis = computed(() => rapport.value?.statut === 'emis')
const nonClotures = computed(() => rapport.value?.cyclesNonClotures ?? [])
const derniereGeneration = computed(() => rapport.value?.derniereGeneration ?? null)
const versionsOnlyoffice = computed(() => {
  const out = []
  for (const v of rapport.value?.versions ?? []) {
    if (v.origine === 'generation') break
    if (v.origine === 'edition_onlyoffice') out.push(v)
  }
  return out
})

async function charger({ silencieux = false } = {}) {
  if (!silencieux) chargement.value = true
  try {
    rapport.value = await api(base.value)
    erreur.value = ''
  } catch (e) {
    erreur.value = e.message
  } finally {
    chargement.value = false
  }
}

onMounted(() => charger())
onBeforeUnmount(() => clearInterval(minuteur))

async function generer(force = false) {
  action.value = 'generer'
  erreur.value = ''
  confirmation.value = null
  try {
    rapport.value = await api(`${base.value}/generer`, { method: 'POST', params: force ? { force: true } : undefined })
  } catch (e) {
    if (e.code === 'modifications_onlyoffice') {
      avertissementRegeneration.value = e.message
      confirmation.value = 'regenerer'
    } else {
      erreur.value = e.message
    }
  } finally {
    action.value = ''
  }
}

function demanderGeneration() {
  if (rapport.value?.modificationsOnlyoffice) {
    avertissementRegeneration.value = ''
    confirmation.value = 'regenerer'
  } else {
    generer(false)
  }
}

async function emettre() {
  action.value = 'emettre'
  erreur.value = ''
  confirmation.value = null
  try {
    rapport.value = await api(`${base.value}/emettre`, { method: 'POST' })
  } catch (e) {
    erreur.value = e.message
  } finally {
    action.value = ''
  }
}

async function relancerPdf() {
  action.value = 'pdf'
  try {
    rapport.value = await api(`${base.value}/pdf`, { method: 'POST' })
  } catch (e) {
    erreur.value = e.message
  } finally {
    action.value = ''
  }
}

async function telechargerVersion(numero) {
  try {
    await telecharger(`${base.value}/versions/${numero}/fichier`, `rapport_v${numero}.pptx`)
  } catch (e) {
    erreur.value = e.message
  }
}

async function telechargerPdf() {
  try {
    await telecharger(`${base.value}/pdf`, 'rapport.pdf')
  } catch (e) {
    erreur.value = e.message
  }
}

// À la fermeture de l'éditeur, le Document Server enregistre le fichier quelques secondes plus
// tard (callback) : on recharge l'état jusqu'à l'apparition de la nouvelle version.
function fermerEditeur({ mode } = {}) {
  editeurOuvert.value = false
  if (mode !== 'edit') return charger({ silencieux: true })
  const avant = rapport.value?.derniereVersion
  attenteEnregistrement.value = true
  let essais = 0
  clearInterval(minuteur)
  minuteur = setInterval(async () => {
    essais += 1
    await charger({ silencieux: true })
    const fini = rapport.value?.derniereVersion !== avant || !rapport.value?.sessionEdition
    if ((fini && essais >= 2) || essais >= 10) {
      clearInterval(minuteur)
      attenteEnregistrement.value = false
    }
  }, 3000)
}
</script>

<template>
  <div class="mt-4 space-y-4">
    <div class="rounded-xl bg-white p-5 shadow-sm">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 class="text-sm font-bold text-[#0d3b56]">Émission du rapport final</h3>
          <p class="text-xs text-gray-400">
            Rapport PowerPoint généré depuis les données de la mission, finalisé dans l'éditeur, puis émis.
          </p>
        </div>
        <span v-if="statut" class="rounded-full px-2.5 py-0.5 text-[11px] font-bold" :class="statut.classes">
          {{ statut.label }}
        </span>
        <span v-else-if="rapport" class="rounded-full bg-gray-100 px-2.5 py-0.5 text-[11px] font-bold text-gray-500">
          Non généré
        </span>
      </div>

      <p v-if="chargement && !rapport" class="mt-3 text-sm text-gray-400">Chargement...</p>
      <p v-if="erreur" class="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">{{ erreur }}</p>

      <template v-if="rapport">
        <div v-if="emis" class="mt-3 rounded-lg bg-[#eef6e6] px-3 py-2 text-xs text-[#5a8a2c]">
          Rapport émis le {{ formatDateTime(rapport.emission?.le) }} par {{ rapport.emission?.par?.nom }}
          (version {{ rapport.emission?.version }}). Il est figé et consultable en lecture seule.
        </div>
        <div v-else-if="nonClotures.length" class="mt-3 rounded-lg bg-[#fbeee0] px-3 py-2 text-xs text-[#c9862c]">
          <p class="font-semibold">
            Cycles non clôturés : le rapport est généré en brouillon (mention « PROJET » en couverture).
          </p>
          <p class="mt-1">{{ nonClotures.map((c) => `${c.code} – ${c.libelle}`).join(' · ') }}</p>
          <p class="mt-1">L'émission exige que tous les cycles soient clôturés.</p>
        </div>

        <div v-if="rapport.sessionEdition" class="mt-3 rounded-lg bg-[#e6f0f7] px-3 py-2 text-xs text-[#2c6e8f]">
          En cours d'édition par
          {{ rapport.sessionEdition.utilisateurs.map((u) => u.name).join(', ') || 'un collaborateur' }}.
        </div>
        <div v-if="attenteEnregistrement" class="mt-3 rounded-lg bg-[#e6f0f7] px-3 py-2 text-xs text-[#2c6e8f]">
          Enregistrement des modifications par le serveur d'édition... la nouvelle version apparaîtra dans quelques secondes.
        </div>

        <div v-if="derniereGeneration" class="mt-3 text-xs text-gray-500">
          Dernière génération le {{ formatDateTime(derniereGeneration.le) }} par {{ derniereGeneration.par?.nom }}
          · {{ derniereGeneration.nbSlides }} slides
          <ul v-if="derniereGeneration.avertissements?.length" class="mt-2 list-disc space-y-0.5 pl-5 text-[#c9862c]">
            <li v-for="(a, i) in derniereGeneration.avertissements" :key="i">{{ a }}</li>
          </ul>
        </div>

        <div class="mt-4 flex flex-wrap gap-2">
          <button
            v-if="!emis"
            type="button"
            :disabled="!rapport.droits.generer || !!action || !!rapport.sessionEdition"
            :title="!rapport.droits.generer ? 'Réservé aux grades senior et au-dessus affectés à la mission' : rapport.sessionEdition ? 'Fermez l’éditeur avant de régénérer' : ''"
            class="rounded-lg bg-[#0d3b56] px-4 py-2 text-sm font-semibold text-white hover:bg-[#0a2f45] disabled:opacity-50"
            @click="demanderGeneration"
          >
            {{ action === 'generer' ? 'Génération...' : aDesVersions ? 'Régénérer' : 'Générer le rapport' }}
          </button>
          <button
            v-if="aDesVersions"
            type="button"
            class="rounded-lg bg-[#2c6e8f] px-4 py-2 text-sm font-semibold text-white hover:bg-[#245b76]"
            @click="editeurOuvert = true"
          >
            {{ rapport.droits.editer ? "Ouvrir dans l'éditeur" : 'Consulter dans l’éditeur' }}
          </button>
          <button
            v-if="!emis && rapport.droits.emettre"
            type="button"
            :disabled="!aDesVersions || nonClotures.length > 0 || !!action || !!rapport.sessionEdition"
            :title="nonClotures.length ? 'Tous les cycles doivent être clôturés' : ''"
            class="rounded-lg bg-[#7cb342] px-4 py-2 text-sm font-semibold text-white hover:bg-[#6ca038] disabled:opacity-50"
            @click="confirmation = 'emettre'"
          >
            {{ action === 'emettre' ? 'Émission...' : 'Émettre le rapport final' }}
          </button>
          <button v-if="rapport.pdf" type="button" class="rounded-lg border border-[#0d3b56] px-4 py-2 text-sm font-semibold text-[#0d3b56] hover:bg-[#eef2f6]" @click="telechargerPdf">
            Télécharger le PDF
          </button>
          <button v-if="emis && !rapport.pdf" type="button" :disabled="!!action" class="rounded-lg border border-[#c9862c] px-4 py-2 text-sm font-semibold text-[#c9862c] hover:bg-[#fbeee0] disabled:opacity-50" @click="relancerPdf">
            {{ action === 'pdf' ? 'Export...' : 'Relancer l’export PDF' }}
          </button>
        </div>
        <p v-if="emis && rapport.pdfErreur" class="mt-2 text-xs text-[#c9862c]">{{ rapport.pdfErreur }}</p>
      </template>
    </div>

    <div v-if="aDesVersions" class="rounded-xl bg-white p-5 shadow-sm">
      <h3 class="text-sm font-bold text-[#0d3b56]">Versions</h3>
      <table class="mt-3 w-full text-left text-sm">
        <thead class="text-xs text-gray-400">
          <tr>
            <th class="py-1 pr-3 font-semibold">N°</th>
            <th class="py-1 pr-3 font-semibold">Date</th>
            <th class="py-1 pr-3 font-semibold">Auteur</th>
            <th class="py-1 pr-3 font-semibold">Origine</th>
            <th class="py-1 pr-3 font-semibold"></th>
            <th class="py-1"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="v in rapport.versions" :key="v.numero" class="border-t border-gray-100">
            <td class="py-2 pr-3 font-bold text-[#0d3b56]">v{{ v.numero }}</td>
            <td class="py-2 pr-3 text-gray-600">{{ formatDateTime(v.date) }}</td>
            <td class="py-2 pr-3 text-gray-600">{{ v.auteur?.nom }}</td>
            <td class="py-2 pr-3">
              <span
                class="rounded-full px-2 py-0.5 text-[11px] font-semibold"
                :class="{
                  'bg-[#e6f0f7] text-[#2c6e8f]': v.origine === 'generation',
                  'bg-[#fbeee0] text-[#c9862c]': v.origine === 'edition_onlyoffice',
                  'bg-[#eef6e6] text-[#5a8a2c]': v.origine === 'emission',
                }"
              >
                {{ ORIGINES[v.origine] }}
              </span>
            </td>
            <td class="py-2 pr-3 text-xs text-gray-400">
              <span v-if="v.nbSlides">{{ v.nbSlides }} slides</span>
              <span v-if="v.brouillon"> · brouillon</span>
              <span v-if="v.force"> · régénération forcée</span>
              <span v-if="v.origine === 'emission'"> · figée (v{{ v.baseeSur }})</span>
            </td>
            <td class="py-2 text-right">
              <button type="button" class="text-xs font-semibold text-[#2c6e8f] hover:underline" @click="telechargerVersion(v.numero)">
                Télécharger
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <PreparationRapport
      v-if="rapport"
      :mission-id="mission.id"
      :rapport="rapport"
      @rapport="rapport = $event"
    />

    <!-- Confirmations -->
    <div v-if="confirmation" class="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 p-6" @click.self="confirmation = null">
      <div class="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
        <template v-if="confirmation === 'regenerer'">
          <h2 class="text-lg font-bold text-[#c9862c]">Régénérer le rapport ?</h2>
          <p class="mt-3 text-sm text-gray-700">
            {{ avertissementRegeneration || 'Des modifications ont été faites dans l’éditeur depuis la dernière génération.' }}
          </p>
          <p class="mt-3 text-sm font-semibold text-gray-700">
            La nouvelle version repartira des données d'EC Perform : les modifications faites dans l'éditeur
            n'y figureront pas.
          </p>
          <ul v-if="versionsOnlyoffice.length" class="mt-2 list-disc pl-5 text-xs text-gray-500">
            <li v-for="v in versionsOnlyoffice" :key="v.numero">
              v{{ v.numero }} — {{ v.auteur?.nom }}, {{ formatDateTime(v.date) }} (reste téléchargeable)
            </li>
          </ul>
          <div class="mt-5 flex justify-end gap-2">
            <button type="button" class="rounded-lg px-4 py-2 text-sm font-semibold text-gray-600 hover:bg-gray-100" @click="confirmation = null">Annuler</button>
            <button type="button" class="rounded-lg bg-[#c9862c] px-4 py-2 text-sm font-semibold text-white hover:bg-[#b37624]" @click="generer(true)">
              Régénérer quand même
            </button>
          </div>
        </template>
        <template v-else>
          <h2 class="text-lg font-bold text-[#0d3b56]">Émettre le rapport final ?</h2>
          <p class="mt-3 text-sm text-gray-700">
            La version v{{ rapport.derniereVersion }} sera figée comme rapport final de la mission. Cette action est
            <strong>irréversible</strong> : le rapport passera en lecture seule pour tous, et ne pourra plus être
            régénéré ni modifié.
          </p>
          <div class="mt-5 flex justify-end gap-2">
            <button type="button" class="rounded-lg px-4 py-2 text-sm font-semibold text-gray-600 hover:bg-gray-100" @click="confirmation = null">Annuler</button>
            <button type="button" class="rounded-lg bg-[#7cb342] px-4 py-2 text-sm font-semibold text-white hover:bg-[#6ca038]" @click="emettre">
              Émettre la version v{{ rapport.derniereVersion }}
            </button>
          </div>
        </template>
      </div>
    </div>

    <EditeurOnlyoffice v-if="editeurOuvert" :mission-id="mission.id" @fermer="fermerEditeur" />
  </div>
</template>
