<script setup>
import { computed, onMounted, ref } from 'vue'
import { formatDateTime } from '../../composables/useCycleRevision'

// Fiche signalétique de l'entité : commune à la mission (et donc à tous les cycles).
// Elle peut être renseignée dans l'application puis téléchargée en Word, ou importée telle quelle.
const props = defineProps({
  mission: { type: Object, required: true },
})

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function authHeaders() {
  return { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
}

const fiche = ref(null)
const loading = ref(false)
const error = ref('')

// Fenêtre : null (fermée), 'consulter' ou 'modifier'.
const mode = ref(null)
const brouillon = ref({})
const saving = ref(false)
const formError = ref('')

const importing = ref(false)
const fileInput = ref(null)
const downloading = ref(false)

const baseUrl = computed(() => `${apiUrl}/missions/${props.mission.id}/fiche-signaletique`)
const modifiable = computed(() => !!fiche.value?.modifiable)
const titreFiche = computed(() => {
  const v = fiche.value?.valeurs ?? {}
  return `Informations générales ${v.sigle || v.denomination || ''}`.trim()
})

async function lireReponse(response) {
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail ?? 'Une erreur est survenue.')
  return data
}

async function fetchFiche() {
  loading.value = true
  error.value = ''
  try {
    fiche.value = await lireReponse(await fetch(baseUrl.value, { headers: authHeaders() }))
  } catch (e) {
    error.value = e instanceof TypeError ? 'Impossible de contacter le serveur.' : e.message
  } finally {
    loading.value = false
  }
}

onMounted(fetchFiche)

function ouvrir(nouveauMode) {
  brouillon.value = { ...fiche.value.valeurs }
  formError.value = ''
  mode.value = nouveauMode
}

function fermer() {
  mode.value = null
}

async function enregistrer() {
  saving.value = true
  formError.value = ''
  try {
    fiche.value = await lireReponse(
      await fetch(baseUrl.value, {
        method: 'PUT',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ valeurs: brouillon.value }),
      }),
    )
    mode.value = 'consulter'
  } catch (e) {
    formError.value = e instanceof TypeError ? 'Impossible de contacter le serveur.' : e.message
  } finally {
    saving.value = false
  }
}

async function importer(event) {
  const fichier = event.target.files?.[0]
  event.target.value = ''
  if (!fichier) return
  importing.value = true
  error.value = ''
  try {
    const formData = new FormData()
    formData.append('fichier', fichier)
    fiche.value = await lireReponse(
      await fetch(`${baseUrl.value}/fichier`, { method: 'POST', headers: authHeaders(), body: formData }),
    )
  } catch (e) {
    error.value = e instanceof TypeError ? 'Impossible de contacter le serveur.' : e.message
  } finally {
    importing.value = false
  }
}

async function telecharger() {
  downloading.value = true
  error.value = ''
  try {
    const response = await fetch(`${baseUrl.value}/export`, { headers: authHeaders() })
    if (!response.ok) {
      await lireReponse(response)
      return
    }
    const url = URL.createObjectURL(await response.blob())
    const lien = document.createElement('a')
    const v = fiche.value.valeurs
    lien.href = url
    lien.download = `Fiche_signaletique_${(v.sigle || v.denomination || 'entite').replace(/[^\w-]+/g, '_')}.docx`
    lien.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    error.value = e instanceof TypeError ? 'Impossible de contacter le serveur.' : e.message
  } finally {
    downloading.value = false
  }
}
</script>

<template>
  <div class="rounded-xl bg-white p-5 shadow-sm">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h3 class="text-sm font-bold text-[#0d3b56]">Fiche signalétique de l'entité</h3>
        <p class="text-xs text-gray-400">Commune à tous les cycles de la mission.</p>
      </div>
      <span
        v-if="fiche"
        class="rounded-full px-2.5 py-0.5 text-[11px] font-bold"
        :class="fiche.renseignee || fiche.fichier ? 'bg-[#eef6e6] text-[#5a8a2c]' : 'bg-[#fbeee0] text-[#c9862c]'"
      >
        {{ fiche.renseignee || fiche.fichier ? 'Déposée' : 'À déposer' }}
      </span>
    </div>

    <p v-if="loading && !fiche" class="mt-3 text-sm text-gray-400">Chargement de la fiche...</p>

    <template v-if="fiche">
      <ul class="mt-3 space-y-1 text-xs text-gray-500">
        <li v-if="fiche.renseignee">
          Renseignée le {{ formatDateTime(fiche.updatedAt) }} par {{ fiche.updatedBy?.nom ?? '—' }}
        </li>
        <li v-if="fiche.fichier">
          Fichier importé :
          <a :href="`${apiUrl}${fiche.fichier.fileUrl}`" target="_blank" rel="noopener" class="font-semibold text-[#2c6e8f] hover:underline">
            {{ fiche.fichier.fileName }}
          </a>
          <span class="text-gray-400"> · le {{ formatDateTime(fiche.fichier.importeLe) }}</span>
        </li>
        <li v-if="!fiche.renseignee && !fiche.fichier">Aucune fiche signalétique pour le moment.</li>
      </ul>
      <p v-if="!modifiable" class="mt-3 rounded-lg bg-[#fbeee0] px-3 py-2 text-xs text-[#c9862c]">
        Mission clôturée : la fiche signalétique ne peut plus être renseignée ni importée.
      </p>

      <div class="mt-3 flex flex-wrap gap-2">
        <button
          v-if="fiche.renseignee"
          type="button"
          class="rounded-lg bg-[#0d3b56] px-4 py-2 text-sm font-semibold text-white hover:bg-[#0a2f45]"
          @click="ouvrir('consulter')"
        >
          Consulter la fiche
        </button>
        <button
          v-else-if="modifiable"
          type="button"
          class="rounded-lg bg-[#0d3b56] px-4 py-2 text-sm font-semibold text-white hover:bg-[#0a2f45]"
          @click="ouvrir('modifier')"
        >
          Renseigner la fiche
        </button>
        <button
          v-if="modifiable"
          type="button"
          :disabled="importing"
          class="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-semibold text-[#0d3b56] hover:bg-gray-50 disabled:opacity-60"
          @click="fileInput.click()"
        >
          {{ importing ? 'Import en cours...' : fiche.fichier ? 'Remplacer le fichier' : 'Importer un fichier' }}
        </button>
        <button
          type="button"
          :disabled="downloading"
          class="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-semibold text-[#0d3b56] hover:bg-gray-50 disabled:opacity-60"
          @click="telecharger"
        >
          {{ fiche.renseignee ? 'Télécharger (.docx)' : 'Télécharger le modèle (.docx)' }}
        </button>
        <input
          ref="fileInput"
          type="file"
          accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg"
          class="hidden"
          @change="importer"
        />
      </div>
    </template>

    <p v-if="error" class="mt-3 text-sm text-red-600">{{ error }}</p>
  </div>

  <div
    v-if="mode && fiche"
    class="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 p-6"
    @click.self="fermer"
  >
    <div class="max-h-[90vh] w-full max-w-3xl overflow-hidden rounded-2xl bg-white shadow-xl">
      <div class="flex items-center justify-between border-b border-gray-100 px-8 py-5">
        <h2 class="text-lg font-bold text-[#0d3b56]">Fiche signalétique</h2>
        <button type="button" class="text-gray-400 hover:text-gray-600" aria-label="Fermer" @click="fermer">✕</button>
      </div>

      <div class="scrollbar-hide max-h-[calc(90vh-73px)] overflow-y-auto p-8">
        <template v-if="mode === 'consulter'">
          <table class="w-full border border-gray-300 text-left text-sm">
            <thead>
              <tr>
                <th colspan="2" class="bg-[#7030a0] px-4 py-2 text-center text-sm font-bold uppercase text-white">
                  {{ titreFiche }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="champ in fiche.champs" :key="champ.key" class="border-t border-gray-200 align-top">
                <th class="w-2/5 px-4 py-2 font-semibold text-[#1a2634]">{{ champ.label }}</th>
                <td class="whitespace-pre-line px-4 py-2 text-[#1a2634]">{{ fiche.valeurs[champ.key] || '—' }}</td>
              </tr>
            </tbody>
          </table>
          <div class="mt-5 flex justify-end gap-2">
            <button
              type="button"
              class="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-semibold text-[#0d3b56] hover:bg-gray-50"
              @click="telecharger"
            >
              Télécharger (.docx)
            </button>
            <button
              v-if="modifiable"
              type="button"
              class="rounded-lg bg-[#0d3b56] px-4 py-2 text-sm font-semibold text-white hover:bg-[#0a2f45]"
              @click="ouvrir('modifier')"
            >
              Modifier
            </button>
          </div>
        </template>

        <form v-else class="space-y-4" @submit.prevent="enregistrer">
          <p v-if="!fiche.renseignee" class="rounded-lg bg-[#eaf1f7] px-4 py-2 text-xs text-[#2c6e8f]">
            Certaines rubriques sont pré-remplies à partir de la fiche client : vérifiez-les avant d'enregistrer.
          </p>
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <label
              v-for="champ in fiche.champs"
              :key="champ.key"
              class="block text-xs font-semibold text-gray-600"
              :class="champ.multiligne ? 'sm:col-span-2' : ''"
            >
              {{ champ.label }}
              <textarea
                v-if="champ.multiligne"
                v-model="brouillon[champ.key]"
                rows="3"
                :placeholder="champ.key === 'associes' ? 'Un associé par ligne' : ''"
                class="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm font-normal text-[#1a2634] outline-none focus:ring-2 focus:ring-[#7cb342]"
              ></textarea>
              <input
                v-else
                v-model="brouillon[champ.key]"
                type="text"
                class="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm font-normal text-[#1a2634] outline-none focus:ring-2 focus:ring-[#7cb342]"
              />
            </label>
          </div>
          <p v-if="formError" class="text-sm text-red-600">{{ formError }}</p>
          <div class="flex justify-end gap-2">
            <button
              type="button"
              class="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-semibold text-[#0d3b56] hover:bg-gray-50"
              @click="fiche.renseignee ? (mode = 'consulter') : fermer()"
            >
              Annuler
            </button>
            <button
              type="submit"
              :disabled="saving"
              class="rounded-lg bg-[#0d3b56] px-4 py-2 text-sm font-semibold text-white hover:bg-[#0a2f45] disabled:opacity-60"
            >
              {{ saving ? 'Enregistrement...' : 'Enregistrer' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
