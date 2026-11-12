<script setup>
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { apiFetch, fileUrl, formatDateTime } from '../../composables/useCycleRevision'

// Chargé à la demande : le moteur de tableur pèse ~500 Ko et n'est utile qu'en mode intégré.
const TableurIntegre = defineAsyncComponent(() => import('./TableurIntegre.vue'))

// Bloc « Papier de travail » réutilisable : mode Lien Excel (fichier externe + copie relue en
// lecture) ou Éditeur intégré (classeur multi-onglets). Enregistrement automatique horodaté.
const props = defineProps({
  missionId: { type: String, required: true },
  code: { type: String, required: true },
  etape: { type: String, required: true },
  canEdit: { type: Boolean, default: false },
})
const emit = defineEmits(['loaded'])

const AUTOSAVE_DELAY_MS = 1000
const PROVIDERS = {
  onedrive: 'OneDrive',
  sharepoint: 'SharePoint',
  google: 'Google Sheets',
  autre: 'Autre',
}

const papier = ref(null)
const loading = ref(false)
const error = ref('')
const conflict = ref(false)
const saving = ref(false)
const editorKey = ref(0)
const journal = ref(null)
const showJournal = ref(false)
const ongletLien = ref(0)
const lastExport = ref(null)

const base = computed(() => `/missions/${props.missionId}/cycles/${props.code}/papiers/${props.etape}`)
const editable = computed(() => !!(props.canEdit && papier.value && !papier.value.verrouille))

// Les modifications s'accumulent pendant le délai puis partent en une seule écriture versionnée.
let timer = null
let pending = {}
let chain = Promise.resolve()

async function load() {
  loading.value = true
  error.value = ''
  conflict.value = false
  clearTimeout(timer)
  pending = {}
  try {
    papier.value = await apiFetch(base.value)
    editorKey.value += 1
    showJournal.value = false
    emit('loaded', papier.value)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

watch(base, load, { immediate: true })
// Soumission / retour de revue : le cycle change de verrou, on recharge pour refléter l'état serveur.
watch(
  () => props.canEdit,
  () => {
    if (papier.value) load()
  },
)

function schedule(changes, delay = AUTOSAVE_DELAY_MS) {
  Object.assign(pending, changes)
  clearTimeout(timer)
  timer = setTimeout(() => {
    const body = pending
    pending = {}
    chain = chain.then(() => save(body))
  }, delay)
}

async function save(body) {
  if (conflict.value) return
  saving.value = true
  try {
    const updated = await apiFetch(base.value, { method: 'PATCH', body: { ...body, version: papier.value.version } })
    // Les données du classeur restent celles de l'éditeur (pas de remontage pendant la saisie).
    Object.assign(papier.value, {
      version: updated.version,
      updatedAt: updated.updatedAt,
      updatedBy: updated.updatedBy,
      mode: updated.mode,
      lien: { ...updated.lien, ...(body.lien ? papier.value.lien : {}) },
    })
    error.value = ''
    emit('loaded', papier.value)
  } catch (e) {
    error.value = e.message
    if (e.status === 409) conflict.value = true
  } finally {
    saving.value = false
  }
}

function setMode(mode) {
  if (!editable.value || papier.value.mode === mode) return
  papier.value.mode = mode
  schedule({ mode }, 0)
}

function onEditorChange(feuilles) {
  papier.value.feuilles = feuilles
  schedule({ feuilles })
}

function onLienChange() {
  const { provider, webUrl, chemin } = papier.value.lien
  schedule({ lien: { provider, webUrl, chemin } })
}

const desktopUrl = computed(() => {
  const lien = papier.value?.lien
  if (!lien?.webUrl || !['onedrive', 'sharepoint'].includes(lien.provider)) return null
  return `ms-excel:ofe|u|${lien.webUrl}`
})

const uploading = ref(false)
async function onFichier(event) {
  const fichier = event.target.files[0]
  event.target.value = ''
  if (!fichier) return
  await chain
  uploading.value = true
  error.value = ''
  try {
    const form = new FormData()
    form.append('version', papier.value.version)
    form.append('fichier', fichier)
    papier.value = await apiFetch(`${base.value}/fichier`, { method: 'POST', form })
    ongletLien.value = 0
    emit('loaded', papier.value)
  } catch (e) {
    error.value = e.message
    if (e.status === 409) conflict.value = true
  } finally {
    uploading.value = false
  }
}

async function toggleJournal() {
  showJournal.value = !showJournal.value
  if (showJournal.value) {
    try {
      journal.value = await apiFetch(`${base.value}/versions`)
    } catch (e) {
      error.value = e.message
    }
  }
}

const exporting = ref(false)
async function exporter() {
  await chain
  exporting.value = true
  try {
    lastExport.value = await apiFetch(`${base.value}/export`, { method: 'POST' })
    return lastExport.value
  } catch (e) {
    error.value = e.message
    return null
  } finally {
    exporting.value = false
  }
}

defineExpose({ exporter, papier })
</script>

<template>
  <div class="rounded-xl border border-[#d7e6d2] bg-[#f3f7f1] p-4">
    <p v-if="loading && !papier" class="text-sm text-gray-400">Chargement du papier de travail...</p>
    <p v-else-if="!papier && error" class="text-sm text-red-600">{{ error }}</p>

    <template v-if="papier">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div class="flex items-center gap-2.5">
          <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#1d6a3a] text-sm font-extrabold text-white">X</span>
          <div>
            <p class="text-[13.5px] font-bold text-[#1a2634]">{{ papier.titre }}</p>
            <p class="text-[11.5px] text-gray-500">
              <template v-if="saving">Enregistrement…</template>
              <template v-else-if="papier.updatedAt">
                Dernière modification : {{ formatDateTime(papier.updatedAt) }} par {{ papier.updatedBy?.nom ?? '—' }} · v{{ papier.version }}
              </template>
              <template v-else>Pas encore modifié</template>
              · enregistrement auto
            </p>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <div class="flex rounded-full border border-[#d7e6d2] bg-white p-0.5">
            <button
              v-for="[mode, label] in [['lien', 'Lien Excel'], ['integre', 'Éditeur intégré']]"
              :key="mode"
              type="button"
              :disabled="!editable"
              class="rounded-full px-3 py-1 text-[11px] font-bold transition disabled:cursor-default"
              :class="papier.mode === mode ? 'bg-[#1d6a3a] text-white' : 'text-gray-500'"
              @click="setMode(mode)"
            >
              {{ label }}
            </button>
          </div>
          <button
            type="button"
            class="rounded-md border border-[#c3dcbc] bg-white px-3 py-1.5 text-[11px] font-semibold text-[#1d6a3a] hover:bg-[#eef3ec]"
            @click="toggleJournal"
          >
            Journal
          </button>
          <button
            v-if="papier.mode === 'integre'"
            type="button"
            :disabled="exporting"
            class="rounded-md border border-[#c3dcbc] bg-white px-3 py-1.5 text-[11px] font-semibold text-[#1d6a3a] hover:bg-[#eef3ec] disabled:opacity-50"
            @click="exporter"
          >
            {{ exporting ? 'Export…' : 'Exporter .xlsx' }}
          </button>
        </div>
      </div>

      <div v-if="error" class="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-md bg-red-50 px-3 py-2 text-xs text-red-700">
        <span>{{ error }}</span>
        <button v-if="conflict" type="button" class="font-semibold underline" @click="load">Recharger</button>
      </div>

      <p v-if="lastExport" class="mt-2 text-xs text-[#1d6a3a]">
        Export du {{ formatDateTime(lastExport.exporteLe) }} (v{{ lastExport.version }}) :
        <a :href="fileUrl(lastExport.fileUrl)" class="font-semibold underline">{{ lastExport.fileName }}</a>
      </p>

      <div v-if="showJournal && journal" class="mt-3 max-h-48 overflow-y-auto rounded-md border border-[#d7e6d2] bg-white">
        <table class="w-full text-left text-xs">
          <thead class="bg-[#f7faf6] text-gray-500">
            <tr>
              <th class="px-3 py-1.5">Version</th>
              <th class="px-3 py-1.5">Date</th>
              <th class="px-3 py-1.5">Auteur</th>
              <th class="px-3 py-1.5">Mode</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="v in journal" :key="v.version" class="border-t border-[#eef3ec] text-gray-500">
              <td class="px-3 py-1.5 font-semibold">v{{ v.version }}<span v-if="v.courante" class="text-[#1d6a3a]"> (actuelle)</span></td>
              <td class="px-3 py-1.5">{{ formatDateTime(v.updatedAt) }}</td>
              <td class="px-3 py-1.5">{{ v.updatedBy?.nom ?? 'Création' }}</td>
              <td class="px-3 py-1.5">{{ v.mode === 'lien' ? 'Lien Excel' : 'Éditeur intégré' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Mode Lien Excel -->
      <div v-if="papier.mode === 'lien'" class="mt-3 space-y-2">
        <div class="space-y-2 rounded-lg border border-dashed border-[#c3dcbc] bg-white p-3">
          <div class="grid grid-cols-1 gap-2 sm:grid-cols-[140px_1fr]">
            <select
              v-model="papier.lien.provider"
              :disabled="!editable"
              class="rounded-md border border-gray-200 text-[#1a2634] px-2 py-1.5 text-xs"
              @change="onLienChange"
            >
              <option v-for="(label, key) in PROVIDERS" :key="key" :value="key">{{ label }}</option>
            </select>
            <input
              v-model="papier.lien.webUrl"
              :disabled="!editable"
              type="url"
              placeholder="URL de partage du fichier (https://...)"
              class="rounded-md border text-[#1a2634] border-gray-200 px-3 py-1.5 text-xs outline-none focus:ring-2 focus:ring-[#7cb342]"
              @input="onLienChange"
            />
          </div>
          <input
            v-model="papier.lien.chemin"
            :disabled="!editable"
            type="text"
            placeholder="Chemin lisible, ex. OneDrive / Missions / SAVEDO SA / Cycle C — Lead.xlsx"
            class="w-full rounded-md border text-[#1a2634] border-gray-200 px-3 py-1.5 text-xs outline-none focus:ring-2 focus:ring-[#7cb342]"
            @input="onLienChange"
          />
          <div class="flex flex-wrap items-center justify-between gap-2">
            <span class="text-xs font-semibold text-[#1d6a3a]">📄 {{ papier.lien.chemin || papier.lien.webUrl || 'Aucun fichier lié' }}</span>
            <div class="flex flex-wrap gap-2">
              <a
                v-if="papier.lien.webUrl"
                :href="papier.lien.webUrl"
                target="_blank"
                rel="noopener"
                class="rounded-md border border-[#c3dcbc] bg-white px-3 py-1.5 text-xs font-semibold text-[#1d6a3a] hover:bg-[#eef3ec]"
              >
                Ouvrir dans {{ papier.lien.provider === 'google' ? 'Google Sheets' : 'Excel Online' }}
              </a>
              <a
                v-if="desktopUrl"
                :href="desktopUrl"
                class="rounded-md bg-[#1d6a3a] px-3 py-1.5 text-xs font-semibold text-white hover:opacity-90"
              >
                Ouvrir dans Excel (bureau)
              </a>
            </div>
          </div>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-2 text-[11px] text-[#1d6a3a]">
          <span class="flex items-center gap-1.5">
            <span class="h-1.5 w-1.5 rounded-full" :class="papier.lien.derniereSync ? 'bg-[#1d6a3a]' : 'bg-gray-300'"></span>
            <template v-if="papier.lien.derniereSync">
              Synchronisé le {{ formatDateTime(papier.lien.derniereSync) }} depuis
              <a :href="fileUrl(papier.lien.fichier?.fileUrl)" class="font-semibold underline">{{ papier.lien.fichier?.fileName }}</a>
              — valeurs en lecture seule
            </template>
            <template v-else>Déposez une copie .xlsx du fichier pour afficher ses valeurs ici.</template>
          </span>
          <label
            v-if="editable"
            class="cursor-pointer rounded-md border border-[#c3dcbc] bg-white px-3 py-1.5 font-semibold hover:bg-[#eef3ec]"
          >
            {{ uploading ? 'Import…' : papier.lien.derniereSync ? 'Resynchroniser (.xlsx)' : 'Déposer la copie (.xlsx)' }}
            <input type="file" accept=".xlsx,.xlsm" class="hidden" :disabled="uploading" @change="onFichier" />
          </label>
        </div>

        <div v-if="papier.lien.feuilles?.length" class="overflow-hidden rounded-lg border border-[#d7e6d2] bg-white">
          <div class="flex flex-wrap gap-1 border-b border-[#d7e6d2] bg-[#eef3ec] px-2 pt-1.5">
            <button
              v-for="(feuille, index) in papier.lien.feuilles"
              :key="feuille.nom"
              type="button"
              class="rounded-t-md px-3 py-1 text-[11px] font-semibold"
              :class="ongletLien === index ? 'bg-white text-[#1d6a3a]' : 'text-gray-500'"
              @click="ongletLien = index"
            >
              {{ feuille.nom }}
            </button>
          </div>
          <div class="max-h-80 overflow-auto">
            <table class="w-full text-left text-[11.5px]">
              <thead class="sticky top-0 bg-[#f7faf6] text-gray-500">
                <tr>
                  <th v-for="(col, i) in papier.lien.feuilles[ongletLien].colonnes" :key="i" class="whitespace-nowrap px-2 py-1.5">{{ col }}</th>
                </tr>
              </thead>
              <tbody class="text-gray-700">
                <tr v-for="(row, r) in papier.lien.feuilles[ongletLien].data" :key="r" class="border-t border-[#eef3ec]">
                  <td v-for="(cell, c) in row" :key="c" class="whitespace-nowrap px-2 py-1">{{ cell ?? '' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Mode Éditeur intégré -->
      <div v-else class="mt-3 overflow-hidden rounded-lg border border-[#d7e6d2] bg-white">
        <div class="flex justify-between border-b border-[#d7e6d2] bg-[#eef3ec] px-3 py-1.5 text-[11px] text-gray-500">
          <span>{{ editable ? 'Éditeur intégré — modifications enregistrées automatiquement' : 'Éditeur intégré — lecture seule' }}</span>
          <span v-if="papier.updatedAt">Horodatage : {{ formatDateTime(papier.updatedAt) }}</span>
        </div>
        <TableurIntegre :key="editorKey" :feuilles="papier.feuilles" :read-only="!editable" @change="onEditorChange" />
      </div>
    </template>
  </div>
</template>
