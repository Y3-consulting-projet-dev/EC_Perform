<script setup>
import { onMounted, ref } from 'vue'
import { API_URL as apiUrl } from '../../utils/apiUrl'

const props = defineProps({
  mission: { type: Object, required: true },
})


function authHeaders() {
  return { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
}

const cycles = ref([])
const loading = ref(true)
const error = ref('')
const balancesInsuffisantes = ref(false)

async function fetchCycles() {
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
    cycles.value = data.cycles
  } catch {
    error.value = 'Impossible de contacter le serveur.'
  } finally {
    loading.value = false
  }
}

onMounted(fetchCycles)
</script>

<template>
  <div>
    <h1 class="mt-4 text-lg font-extrabold text-[#0d3b56]">Planification des travaux</h1>
    <p class="mt-1 text-sm text-gray-500">
      Génération automatique des cycles à partir de la balance importée en Phase 1.
    </p>

    <p v-if="loading" class="mt-6 text-sm text-gray-400">Chargement des cycles...</p>

    <p
      v-else-if="balancesInsuffisantes"
      class="mt-4 rounded-lg bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-700"
    >
      Au moins deux balances (exercice N et N-1) sont nécessaires pour générer les cycles. Déposez-les
      depuis la Phase 1 – Ouverture et collecte, dans n'importe quelle catégorie : tout document dont le
      nom ou la description contient « balance » est automatiquement détecté.
    </p>

    <p v-else-if="error" class="mt-4 text-sm text-red-600">{{ error }}</p>

    <div v-else class="mt-6 overflow-x-auto rounded-lg shadow-sm">
      <table class="w-full text-left text-sm">
        <thead>
          <tr class="bg-[#7cb342] text-sm font-bold text-white">
            <th class="px-4 py-3">Code</th>
            <th class="px-4 py-3">Cycle</th>
            <th class="px-4 py-3 text-center">Plage</th>
            <th class="px-4 py-3 text-center">NB de comptes</th>
            <th class="px-4 py-3 text-right">Solde N</th>
            <th class="px-4 py-3 text-right">Solde N-1</th>
          </tr>
        </thead>
        <tbody class="bg-white">
          <tr v-for="cycle in cycles" :key="cycle.code" class="border-t border-gray-100">
            <td class="px-4 py-3">
              <span
                class="flex h-7 w-7 items-center justify-center rounded-lg bg-[#0d3b56] text-xs font-bold text-white"
              >
                {{ cycle.code }}
              </span>
            </td>
            <td class="px-4 py-3 font-medium text-[#0d3b56]">{{ cycle.libelle }}</td>
            <td class="px-4 py-3 text-center text-gray-500">{{ cycle.plage }}</td>
            <td class="px-4 py-3 text-center text-gray-500">{{ cycle.nbComptes }}</td>
            <td class="px-4 py-3 text-right text-gray-500">{{ cycle.soldeN }}</td>
            <td class="px-4 py-3 text-right text-gray-500">{{ cycle.soldeNMoins1 }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
