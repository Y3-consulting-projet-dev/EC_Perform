<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '../../composables/useRapport'

// Éditeur ONLYOFFICE Docs, en plein écran au-dessus de l'espace mission. La config (signée en JWT
// par le backend : clé du document, mode edit/view, utilisateur) et l'URL du Document Server sont
// fournies par GET /missions/{id}/rapport/editeur.
const props = defineProps({
  missionId: { type: String, required: true },
})
const emit = defineEmits(['fermer'])

const conteneurId = `oo-editeur-${Math.random().toString(16).slice(2)}`
const chargement = ref(true)
const erreur = ref('')
const mode = ref(null)
const titre = ref('')
let editeur = null

// api.js n'est chargé qu'une fois : une fois DocsAPI disponible, les ouvertures suivantes le
// réutilisent ; un échec retire la balise pour permettre une nouvelle tentative.
function chargerApi(baseUrl) {
  if (window.DocsAPI) return Promise.resolve()
  const src = `${baseUrl}/web-apps/apps/api/documents/api.js`
  return new Promise((resolve, reject) => {
    document.querySelector(`script[src="${src}"]`)?.remove()
    const script = Object.assign(document.createElement('script'), { src, async: true })
    script.onload = () => (window.DocsAPI ? resolve() : reject(new Error('DocsAPI absent')))
    script.onerror = () => {
      script.remove()
      reject(new Error('api.js introuvable'))
    }
    document.head.appendChild(script)
  })
}

onMounted(async () => {
  try {
    const data = await api(`/missions/${props.missionId}/rapport/editeur`)
    mode.value = data.mode
    titre.value = data.config.document.title
    try {
      await chargerApi(data.documentServerUrl)
    } catch {
      throw new Error(
        `Le serveur d'édition ONLYOFFICE (${data.documentServerUrl}) est injoignable. Vérifiez qu'il est démarré.`,
      )
    }
    editeur = new window.DocsAPI.DocEditor(conteneurId, {
      ...data.config,
      width: '100%',
      height: '100%',
      events: {
        onAppReady: () => (chargement.value = false),
        onError: (event) => {
          erreur.value = `Erreur de l'éditeur ONLYOFFICE (code ${event?.data?.errorCode ?? '?'}) : ${event?.data?.errorDescription ?? ''}`
          chargement.value = false
        },
        onRequestClose: () => fermer(),
      },
    })
  } catch (e) {
    erreur.value = e.message
    chargement.value = false
  }
})

function fermer() {
  emit('fermer', { mode: mode.value })
}

onBeforeUnmount(() => {
  try {
    editeur?.destroyEditor()
  } catch {
    // éditeur déjà détruit
  }
  editeur = null
})
</script>

<template>
  <div class="fixed inset-0 z-[80] flex flex-col bg-[#eef2f6]">
    <header class="flex shrink-0 items-center justify-between gap-4 bg-[#0d3b56] px-6 py-3 text-white">
      <div class="min-w-0">
        <p class="truncate text-sm font-bold">{{ titre || 'Rapport final' }}</p>
        <p class="text-xs text-white/70">
          {{ mode === 'edit' ? 'Édition partagée — les modifications sont enregistrées comme nouvelle version.' : 'Lecture seule' }}
        </p>
      </div>
      <button
        type="button"
        class="rounded-lg bg-white/90 px-4 py-2 text-sm font-semibold text-[#0d3b56] hover:bg-white"
        @click="fermer"
      >
        Fermer l'éditeur
      </button>
    </header>

    <div class="relative min-h-0 flex-1">
      <div :id="conteneurId" class="h-full w-full" />
      <div v-if="chargement && !erreur" class="absolute inset-0 flex items-center justify-center bg-[#eef2f6]">
        <p class="text-sm font-semibold text-gray-500">Ouverture de l'éditeur...</p>
      </div>
      <div v-if="erreur" class="absolute inset-0 flex items-center justify-center bg-[#eef2f6] p-6">
        <div class="max-w-lg rounded-xl bg-white p-6 text-center shadow-sm">
          <p class="text-sm font-bold text-red-600">L'éditeur n'a pas pu s'ouvrir</p>
          <p class="mt-2 text-sm text-gray-600">{{ erreur }}</p>
          <button
            type="button"
            class="mt-4 rounded-lg bg-[#0d3b56] px-4 py-2 text-sm font-semibold text-white hover:bg-[#0a2f45]"
            @click="fermer"
          >
            Retour
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
