<script setup>
import { computed, reactive, ref } from 'vue'

const props = defineProps({
  checklist: { type: Object, required: true },
})

const progressPercent = computed(() =>
  props.checklist.total ? Math.round((props.checklist.recus / props.checklist.total) * 100) : 0,
)

const statutStyles = {
  'En attente de livraison': 'bg-gray-100 text-gray-600',
  'Partiellement reçu': 'bg-amber-100 text-amber-700',
  Reçu: 'bg-[#7cb342] text-white',
}

const statutOptions = ['En attente de livraison', 'Partiellement reçu', 'Reçu']
const NEW_CATEGORY = '__new__'

function updateDocStatut(doc, newStatut) {
  if (doc.statut === 'Reçu' && newStatut !== 'Reçu') props.checklist.recus -= 1
  if (doc.statut !== 'Reçu' && newStatut === 'Reçu') props.checklist.recus += 1
  doc.statut = newStatut
}

const showInsertDocument = ref(false)
const insertForm = reactive({
  categorie: '',
  nouvelleCategorie: '',
  description: '',
  version: 'Electronique',
  dateDemande: '',
  dateReception: '',
  statut: 'En attente de livraison',
})
const selectedFile = ref(null)

function handleFileChange(event) {
  selectedFile.value = event.target.files[0] ?? null
}

function openInsertDocument() {
  insertForm.categorie = props.checklist.categories[0]?.title ?? NEW_CATEGORY
  insertForm.nouvelleCategorie = ''
  insertForm.description = ''
  insertForm.version = 'Electronique'
  insertForm.dateDemande = ''
  insertForm.dateReception = ''
  insertForm.statut = 'En attente de livraison'
  selectedFile.value = null
  showInsertDocument.value = true
}

function closeInsertDocument() {
  showInsertDocument.value = false
}

function handleInsertDocument() {
  const categoryTitle =
    insertForm.categorie === NEW_CATEGORY ? insertForm.nouvelleCategorie.trim().toUpperCase() : insertForm.categorie
  if (!categoryTitle || !insertForm.description.trim()) return

  let category = props.checklist.categories.find((c) => c.title === categoryTitle)
  if (!category) {
    category = { title: categoryTitle, documents: [] }
    props.checklist.categories.push(category)
  }

  const totalDocs = props.checklist.categories.reduce((sum, c) => sum + c.documents.length, 0)
  category.documents.push({
    n: totalDocs + 1,
    description: insertForm.description.trim(),
    version: insertForm.version.trim() || 'Electronique',
    dateDemande: insertForm.dateDemande.trim() || '—',
    dateReception: insertForm.dateReception.trim() || '—',
    statut: insertForm.statut,
    fileName: selectedFile.value?.name ?? null,
    fileUrl: selectedFile.value ? URL.createObjectURL(selectedFile.value) : null,
  })

  props.checklist.total += 1
  if (insertForm.statut === 'Reçu') props.checklist.recus += 1

  closeInsertDocument()
}
</script>

<template>
  <div>
    <div class="mt-4 flex items-start justify-between gap-6">
      <div class="flex-1">
        <h1 class="text-lg font-extrabold text-[#0d3b56]">{{ checklist.recus }}/{{ checklist.total }} documents reçus</h1>
        <div class="mt-3 flex max-w-md items-center gap-3">
          <div class="h-2.5 flex-1 overflow-hidden rounded-full bg-gray-200">
            <div class="h-full rounded-full bg-[#7cb342]" :style="{ width: progressPercent + '%' }"></div>
          </div>
          <span class="text-sm font-bold text-[#7cb342]">{{ progressPercent }}%</span>
        </div>
      </div>

      <button
        type="button"
        class="flex shrink-0 items-center gap-2 rounded-lg bg-[#0d3b56] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#0a2f45]"
      >
        <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="5" width="18" height="14" rx="2" />
          <path stroke-linecap="round" stroke-linejoin="round" d="m4 6 8 7 8-7" />
        </svg>
        Relancer le client
      </button>
    </div>

    <button
      type="button"
      class="mt-6 flex items-center gap-2 rounded-lg border border-[#7cb342] bg-white px-5 py-2.5 text-sm font-semibold text-[#0d3b56] transition hover:bg-gray-50"
      @click="openInsertDocument"
    >
      <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 5v14M5 12h14" />
      </svg>
      Insérer des documents
    </button>

    <div class="mt-6 overflow-x-auto rounded-lg shadow-sm">
      <table class="w-full text-left text-sm">
        <thead>
          <tr class="bg-[#7cb342] text-xs font-semibold text-white">
            <th class="px-4 py-3">N°</th>
            <th class="px-4 py-3">Description des documents</th>
            <th class="px-4 py-3">Version</th>
            <th class="px-4 py-3">Date de demande</th>
            <th class="px-4 py-3">Date de réception</th>
            <th class="px-4 py-3">Statut</th>
          </tr>
        </thead>
        <tbody class="bg-white">
          <template v-for="category in checklist.categories" :key="category.title">
            <tr class="bg-[#0d3b56]">
              <td colspan="6" class="px-4 py-2 text-xs font-bold text-white">{{ category.title }}</td>
            </tr>
            <tr v-for="doc in category.documents" :key="doc.n" class="border-t border-gray-100">
              <td class="px-4 py-3 text-gray-500">{{ doc.n }}</td>
              <td class="px-4 py-3 font-medium text-[#0d3b56]">
                <a
                  v-if="doc.fileUrl"
                  :href="doc.fileUrl"
                  :download="doc.fileName"
                  class="flex items-center gap-1.5 text-[#2f6fb0] hover:underline"
                  target="_blank"
                >
                  <svg viewBox="0 0 24 24" class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M21.44 11.05 12.25 20.24a5.5 5.5 0 0 1-7.78-7.78l9.19-9.19a3.5 3.5 0 0 1 4.95 4.95l-9.2 9.19a1.5 1.5 0 0 1-2.12-2.12l8.49-8.48" />
                  </svg>
                  {{ doc.description }}
                </a>
                <span v-else>{{ doc.description }}</span>
              </td>
              <td class="px-4 py-3 text-gray-500">{{ doc.version }}</td>
              <td class="px-4 py-3 text-gray-500">{{ doc.dateDemande }}</td>
              <td class="px-4 py-3 text-gray-500">{{ doc.dateReception }}</td>
              <td class="px-4 py-3">
                <select
                  :value="doc.statut"
                  class="appearance-none rounded-full px-3 py-1 text-xs font-semibold outline-none"
                  :class="statutStyles[doc.statut] ?? 'bg-gray-100 text-gray-600'"
                  @change="updateDocStatut(doc, $event.target.value)"
                >
                  <option v-for="option in statutOptions" :key="option" :value="option">{{ option }}</option>
                </select>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <div
      v-if="showInsertDocument"
      class="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-6"
      @click.self="closeInsertDocument"
    >
      <div class="w-full max-w-lg rounded-2xl bg-white p-8 shadow-xl">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-bold text-[#0d3b56]">Insérer un document</h2>
          <button type="button" class="text-gray-400 hover:text-gray-600" aria-label="Fermer" @click="closeInsertDocument">
            ✕
          </button>
        </div>

        <form class="mt-6 space-y-4" @submit.prevent="handleInsertDocument">
          <div>
            <label for="doc-categorie" class="mb-1 block text-sm font-bold text-[#0d3b56]">Catégorie</label>
            <select
              id="doc-categorie"
              v-model="insertForm.categorie"
              class="w-full rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342]"
            >
              <option v-for="category in checklist.categories" :key="category.title" :value="category.title">
                {{ category.title }}
              </option>
              <option :value="NEW_CATEGORY">+ Nouvelle catégorie</option>
            </select>
          </div>

          <div v-if="insertForm.categorie === NEW_CATEGORY">
            <label for="doc-nouvelle-categorie" class="mb-1 block text-sm font-bold text-[#0d3b56]"
              >Nom de la catégorie</label
            >
            <input
              id="doc-nouvelle-categorie"
              v-model="insertForm.nouvelleCategorie"
              type="text"
              required
              placeholder="Ex. : IMMOBILISATIONS"
              class="w-full rounded-xl border border-[#7cb342] bg-[#eef1ec] px-4 py-2.5 text-sm text-[#0d3b56] placeholder-gray-400 outline-none focus:ring-2 focus:ring-[#7cb342]"
            />
          </div>

          <div>
            <label for="doc-description" class="mb-1 block text-sm font-bold text-[#0d3b56]"
              >Description du document</label
            >
            <input
              id="doc-description"
              v-model="insertForm.description"
              type="text"
              required
              placeholder="Ex. : Relevé bancaire 2024"
              class="w-full rounded-xl border border-[#7cb342] bg-[#eef1ec] px-4 py-2.5 text-sm text-[#0d3b56] placeholder-gray-400 outline-none focus:ring-2 focus:ring-[#7cb342]"
            />
          </div>

          <div>
            <label for="doc-fichier" class="mb-1 block text-sm font-bold text-[#0d3b56]">Fichier</label>
            <input
              id="doc-fichier"
              type="file"
              class="w-full rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm text-[#0d3b56] outline-none file:mr-3 file:rounded-full file:border-0 file:bg-[#7cb342] file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-white"
              @change="handleFileChange"
            />
            <p v-if="selectedFile" class="mt-1 text-xs text-gray-500">{{ selectedFile.name }}</p>
          </div>

          <div class="grid grid-cols-3 gap-4">
            <div>
              <label for="doc-version" class="mb-1 block text-sm font-bold text-[#0d3b56]">Version</label>
              <input
                id="doc-version"
                v-model="insertForm.version"
                type="text"
                class="w-full rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342]"
              />
            </div>
            <div>
              <label for="doc-date-demande" class="mb-1 block text-sm font-bold text-[#0d3b56]">Date de demande</label>
              <input
                id="doc-date-demande"
                v-model="insertForm.dateDemande"
                type="date"
                class="w-full rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342]"
              />
            </div>
            <div>
              <label for="doc-date-reception" class="mb-1 block text-sm font-bold text-[#0d3b56]">Date de réception</label>
              <input
                id="doc-date-reception"
                v-model="insertForm.dateReception"
                type="date"
                class="w-full rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342]"
              />
            </div>
          </div>

          <div>
            <label for="doc-statut" class="mb-1 block text-sm font-bold text-[#0d3b56]">Statut</label>
            <select
              id="doc-statut"
              v-model="insertForm.statut"
              class="w-full rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342]"
            >
              <option v-for="statut in statutOptions" :key="statut" :value="statut">{{ statut }}</option>
            </select>
          </div>

          <div class="flex justify-end gap-3 pt-2">
            <button
              type="button"
              class="rounded-full border border-gray-300 px-6 py-2.5 text-sm font-semibold text-gray-600 transition hover:bg-gray-50"
              @click="closeInsertDocument"
            >
              Annuler
            </button>
            <button
              type="submit"
              class="rounded-full bg-[#7cb342] px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-[#6ca038]"
            >
              Insérer
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
