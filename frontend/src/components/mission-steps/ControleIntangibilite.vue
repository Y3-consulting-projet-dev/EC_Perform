<script setup>
import { computed, onMounted, ref } from 'vue'

const props = defineProps({
  mission: { type: Object, required: true },
})

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function authHeaders() {
  return { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
}

const balances = ref([])
const selectedN = ref('')
const selectedNMoins1 = ref('')

const controle = ref(null)
const loadingBalances = ref(true)
const loadingControle = ref(false)
const error = ref('')

function balanceLabel(balance) {
  return balance.annee ? `${balance.annee} — ${balance.description}` : balance.description
}

async function fetchBalances() {
  loadingBalances.value = true
  error.value = ''
  try {
    const response = await fetch(`${apiUrl}/missions/${props.mission.id}/balances`, { headers: authHeaders() })
    const data = await response.json()
    if (!response.ok) {
      error.value = data.detail ?? 'Une erreur est survenue.'
      return
    }
    balances.value = data.balances

    if (balances.value.length >= 2) {
      selectedN.value = balances.value[0].documentId
      selectedNMoins1.value = balances.value[1].documentId
      await fetchControle()
    }
  } catch {
    error.value = 'Impossible de contacter le serveur.'
  } finally {
    loadingBalances.value = false
  }
}

async function fetchControle() {
  if (!selectedN.value || !selectedNMoins1.value || selectedN.value === selectedNMoins1.value) {
    controle.value = null
    return
  }
  loadingControle.value = true
  error.value = ''
  try {
    const params = new URLSearchParams({
      documentIdN: selectedN.value,
      documentIdNMoins1: selectedNMoins1.value,
    })
    const response = await fetch(`${apiUrl}/missions/${props.mission.id}/controles/intangibilite?${params}`, {
      headers: authHeaders(),
    })
    const data = await response.json()
    if (!response.ok) {
      error.value = data.detail ?? 'Une erreur est survenue.'
      controle.value = null
      return
    }
    controle.value = data
  } catch {
    error.value = 'Impossible de contacter le serveur.'
    controle.value = null
  } finally {
    loadingControle.value = false
  }
}

onMounted(fetchBalances)

const selectionInvalid = computed(
  () => selectedN.value && selectedNMoins1.value && selectedN.value === selectedNMoins1.value,
)

const compteStatutStyles = {
  Nouveau: 'bg-sky-100 text-sky-700',
  Disparu: 'bg-amber-100 text-amber-700',
  Écart: 'bg-red-100 text-red-700',
  OK: 'bg-emerald-100 text-emerald-700',
}
</script>

<template>
  <div>
    <h1 class="mt-4 text-lg font-extrabold text-[#0d3b56]">Contrôle d'intangibilité</h1>

    <p v-if="loadingBalances" class="mt-6 text-sm text-gray-400">Chargement des balances...</p>

    <template v-else-if="balances.length < 2">
      <p class="mt-4 rounded-lg bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-700">
        Au moins deux balances (exercice N et N-1) sont nécessaires pour lancer ce contrôle. Déposez-les depuis la
        Phase 1 – Ouverture et collecte, dans n'importe quelle catégorie : tout document dont le nom ou la
        description contient « balance » est automatiquement détecté, dès son dépôt, même si les autres documents
        de la checklist ne sont pas encore reçus.
      </p>
    </template>

    <template v-else>
      <div class="mt-4 flex flex-wrap items-center gap-3">
        <label for="balance-n" class="text-sm font-bold text-[#0d3b56]">Exercice N :</label>
        <select
          id="balance-n"
          v-model="selectedN"
          class="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342]"
          @change="fetchControle"
        >
          <option v-for="balance in balances" :key="balance.documentId" :value="balance.documentId">
            {{ balanceLabel(balance) }}
          </option>
        </select>

        <label for="balance-n-1" class="text-sm font-bold text-[#0d3b56]">Exercice N-1 :</label>
        <select
          id="balance-n-1"
          v-model="selectedNMoins1"
          class="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342]"
          @change="fetchControle"
        >
          <option v-for="balance in balances" :key="balance.documentId" :value="balance.documentId">
            {{ balanceLabel(balance) }}
          </option>
        </select>
      </div>

      <p v-if="selectionInvalid" class="mt-3 text-sm text-red-600">
        Les balances N et N-1 doivent être deux fichiers différents.
      </p>
      <p v-if="error" class="mt-3 text-sm text-red-600">{{ error }}</p>
      <p v-if="loadingControle" class="mt-4 text-sm text-gray-400">Calcul du contrôle...</p>

      <template v-if="controle">
        <p class="mt-2 flex items-center gap-2 text-sm font-semibold text-amber-600">
          <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M12 9v4m0 4h.01M10.29 3.86 1.82 18a1 1 0 0 0 .86 1.5h18.64a1 1 0 0 0 .86-1.5L13.71 3.86a1 1 0 0 0-1.72 0Z"
            />
          </svg>
          {{ controle.ecarts }} écart(s) détecté(s) sur {{ controle.totalComptes }} compte(s)
        </p>
        <p class="mt-1 text-sm text-gray-500">
          Périodes analysées : N = {{ controle.periodeN }}, N-1 = {{ controle.periodeNMoins1 }}
        </p>

        <button
          type="button"
          class="mt-4 rounded-lg bg-[#7cb342] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#6ca038]"
        >
          Télécharger (XLSX)
        </button>

        <div class="mt-6 overflow-x-auto rounded-lg shadow-sm">
          <table class="w-full text-left text-sm">
            <thead>
              <tr class="bg-[#0d3b56] text-xs font-semibold uppercase text-white">
                <th class="px-4 py-3">Compte</th>
                <th class="px-4 py-3">Bilan ouverture (N)</th>
                <th class="px-4 py-3">Bilan clôture (N-1)</th>
                <th class="px-4 py-3">Écarts</th>
                <th class="px-4 py-3">Statut</th>
                <th class="px-4 py-3">Explications probables</th>
              </tr>
            </thead>
            <tbody class="bg-white">
              <tr v-for="compte in controle.comptes" :key="compte.compte" class="border-t border-gray-100">
                <td class="px-4 py-3">
                  <span class="font-medium text-[#0d3b56]">{{ compte.compte }}</span>
                </td>
                <td class="px-4 py-3 text-gray-500">{{ compte.bilanOuvertureN }}</td>
                <td class="px-4 py-3 text-gray-500">{{ compte.bilanClotureNMoins1 }}</td>
                <td class="px-4 py-3 font-bold text-red-600">{{ compte.ecart }}</td>
                <td class="px-4 py-3">
                  <span
                    class="rounded-full px-3 py-1 text-xs font-semibold"
                    :class="compteStatutStyles[compte.statut] ?? 'bg-gray-100 text-gray-600'"
                  >
                    {{ compte.statut }}
                  </span>
                </td>
                <td class="max-w-xs px-4 py-3 text-xs text-gray-500">{{ compte.explication }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </template>
  </div>
</template>
