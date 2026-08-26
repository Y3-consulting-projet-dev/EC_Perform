<script setup>
import { computed, onMounted, ref } from 'vue'
import FeuilleMaitresseModal from './FeuilleMaitresseModal.vue'
import { API_URL as apiUrl } from '../../utils/apiUrl'

const props = defineProps({
  mission: { type: Object, required: true },
})


function authHeaders() {
  return { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
}

const sensStyles = {
  hausse: 'text-green-600',
  baisse: 'text-red-600',
  stable: 'text-gray-500',
}
const sensIcon = { hausse: '▲', baisse: '▼', stable: '-' }

function formatVariation(lead) {
  if (lead.variationPct === null) return '-'
  const sign = lead.variationPct > 0 ? '+' : ''
  return `${sign}${lead.variationPct.toFixed(1).replace('.', ',')} %`
}

const leads = ref([])
const loading = ref(true)
const error = ref('')
const balancesInsuffisantes = ref(false)
const search = ref('')

const ACCENTS_REGEX = new RegExp('[' + String.fromCharCode(0x0300) + '-' + String.fromCharCode(0x036f) + ']', 'g')

function normalize(text) {
  return (text ?? '')
    .normalize('NFD')
    .replace(ACCENTS_REGEX, '')
    .toLowerCase()
}

const filteredLeads = computed(() => {
  const query = normalize(search.value).trim()
  if (!query) return leads.value
  return leads.value.filter(
    (lead) => normalize(lead.code).includes(query) || normalize(lead.libelle).includes(query),
  )
})

async function fetchLeads() {
  loading.value = true
  error.value = ''
  balancesInsuffisantes.value = false
  try {
    const response = await fetch(`${apiUrl}/missions/${props.mission.id}/cycles`, { headers: authHeaders() })
    const data = await response.json()
    if (!response.ok) {
      if (response.status === 404) {
        balancesInsuffisantes.value = true
      } else {
        error.value = data.detail ?? 'Une erreur est survenue.'
      }
      return
    }
    leads.value = data.cycles
  } catch {
    error.value = 'Impossible de contacter le serveur.'
  } finally {
    loading.value = false
  }
}

onMounted(fetchLeads)

const showFeuilleMaitresse = ref(false)
const selectedLead = ref(null)

function openFeuilleMaitresse(lead) {
  selectedLead.value = lead
  showFeuilleMaitresse.value = true
}
</script>

<template>
  <div>
    <div class="mt-4 flex flex-wrap items-center justify-between gap-4">
      <h1 class="text-lg font-extrabold text-[#0d3b56]">Génération des leads</h1>

      <div class="relative w-full sm:w-72">
        <svg
          viewBox="0 0 24 24"
          class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <circle cx="11" cy="11" r="7" />
          <path stroke-linecap="round" d="m20 20-3.5-3.5" />
        </svg>
        <input
          v-model="search"
          type="text"
          placeholder="Rechercher un cycle (code ou libellé)..."
          class="w-full rounded-lg border border-gray-200 bg-white py-2 pl-9 pr-3 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342]"
        />
      </div>
    </div>

    <p v-if="loading" class="mt-6 text-sm text-gray-400">Chargement des leads...</p>

    <p
      v-else-if="balancesInsuffisantes"
      class="mt-4 rounded-lg bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-700"
    >
      Au moins deux balances (exercice N et N-1) sont nécessaires pour générer les leads. Déposez-les
      depuis la Phase 1 – Ouverture et collecte, dans n'importe quelle catégorie : tout document dont le
      nom ou la description contient « balance » est automatiquement détecté.
    </p>

    <p v-else-if="error" class="mt-4 text-sm text-red-600">{{ error }}</p>

    <template v-else>
      <p v-if="filteredLeads.length === 0" class="mt-6 text-sm text-gray-400">
        Aucun cycle ne correspond à « {{ search }} ».
      </p>

      <div v-else class="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2">
        <div v-for="lead in filteredLeads" :key="lead.code" class="rounded-xl bg-white p-5 shadow-sm">
          <div class="flex items-center gap-2">
            <span
              class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[#0d3b56] text-xs font-bold text-white"
            >
              {{ lead.code }}
            </span>
            <span class="font-bold text-[#0d3b56]">{{ lead.libelle }}</span>
          </div>

          <div class="mt-4 space-y-1 text-sm">
            <div class="flex justify-between">
              <span class="text-gray-500">Solde N</span>
              <span class="font-medium text-[#0d3b56]">{{ lead.soldeN }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-500">Solde N-1</span>
              <span class="font-medium text-[#0d3b56]">{{ lead.soldeNMoins1 }}</span>
            </div>
          </div>

          <p class="mt-3 text-sm font-bold" :class="sensStyles[lead.sens]">
            {{ sensIcon[lead.sens] }} {{ formatVariation(lead) }}
            <span v-if="lead.sens !== 'stable'">à expliquer</span>
          </p>

          <button
            type="button"
            class="mx-auto mt-3 block rounded-lg bg-[#0d3b56] px-6 py-2 text-sm font-semibold text-white transition hover:bg-[#0a2f45]"
            @click="openFeuilleMaitresse(lead)"
          >
            Ouvrir
          </button>
        </div>
      </div>
    </template>

    <FeuilleMaitresseModal v-model="showFeuilleMaitresse" :lead="selectedLead" :mission="mission" />
  </div>
</template>
