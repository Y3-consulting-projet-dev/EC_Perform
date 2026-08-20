<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  lead: { type: Object, default: null },
  mission: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue'])

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function authHeaders() {
  return { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
}

function close() {
  emit('update:modelValue', false)
}

function formatNumber(n) {
  const rounded = Math.round(n)
  const sign = rounded < 0 ? '-' : ''
  return sign + Math.abs(rounded).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
}

function formatVariation(lead) {
  if (!lead || lead.variationPct === null) return '—'
  const sign = lead.variationPct > 0 ? '+' : ''
  return `${sign}${lead.variationPct.toFixed(1).replace('.', ',')} %`
}

const sensStyles = {
  hausse: 'text-green-600',
  baisse: 'text-red-600',
  stable: 'text-gray-500',
}

const comptes = ref([])
const loading = ref(false)
const error = ref('')

async function fetchComptes() {
  if (!props.lead?.code || !props.mission?.id) {
    comptes.value = []
    return
  }
  loading.value = true
  error.value = ''
  try {
    const response = await fetch(`${apiUrl}/missions/${props.mission.id}/cycles/${props.lead.code}`, {
      headers: authHeaders(),
    })
    const data = await response.json()
    if (!response.ok) {
      error.value = data.detail ?? 'Une erreur est survenue.'
      comptes.value = []
      return
    }
    comptes.value = data.comptes.map((row) => {
      const ecart = row.soldeN - row.soldeNMoins1
      // Division par la valeur absolue : un solde N-1 négatif (compte créditeur) ne doit
      // pas inverser le signe du pourcentage par rapport au sens hausse/baisse.
      const pct = row.soldeNMoins1 ? (ecart / Math.abs(row.soldeNMoins1)) * 100 : 0
      return {
        ...row,
        ecart,
        pct,
        sens: ecart > 0 ? 'hausse' : ecart < 0 ? 'baisse' : 'stable',
      }
    })
  } catch {
    error.value = 'Impossible de contacter le serveur.'
    comptes.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.modelValue, props.lead?.code],
  ([open]) => {
    if (open) fetchComptes()
  },
)
</script>

<template>
  <div
    v-if="modelValue && lead"
    class="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 p-6"
    @click.self="close"
  >
    <div class="max-h-[90vh] w-full max-w-3xl overflow-hidden rounded-2xl bg-white shadow-xl">
      <div class="flex items-center justify-between border-b border-gray-100 px-8 py-5">
        <h2 class="text-lg font-bold text-[#0d3b56]">Feuille maîtresse — Cycle {{ lead.code }} · {{ lead.libelle }}</h2>
        <button type="button" class="text-gray-400 hover:text-gray-600" aria-label="Fermer" @click="close">✕</button>
      </div>

      <div class="scrollbar-hide max-h-[calc(90vh-73px)] overflow-y-auto p-8">
        <div class="grid grid-cols-3 gap-4">
          <div class="rounded-lg bg-gray-100 p-4">
            <p class="text-xs text-gray-500">Solde N</p>
            <p class="mt-1 text-sm font-bold text-[#0d3b56]">{{ lead.soldeN }}</p>
          </div>
          <div class="rounded-lg bg-gray-100 p-4">
            <p class="text-xs text-gray-500">Solde N-1</p>
            <p class="mt-1 text-sm font-bold text-[#0d3b56]">{{ lead.soldeNMoins1 }}</p>
          </div>
          <div class="rounded-lg bg-gray-100 p-4">
            <p class="text-xs text-gray-500">Variation</p>
            <p class="mt-1 text-sm font-bold" :class="sensStyles[lead.sens]">{{ formatVariation(lead) }}</p>
          </div>
        </div>

        <h3 class="mt-6 text-sm font-bold text-[#0d3b56]">Comptes rattachés au cycle</h3>

        <p v-if="loading" class="mt-3 text-sm text-gray-400">Chargement des comptes...</p>
        <p v-else-if="error" class="mt-3 text-sm text-red-600">{{ error }}</p>

        <div v-else-if="comptes.length" class="mt-3 overflow-x-auto rounded-lg shadow-sm">
          <table class="w-full text-left text-sm">
            <thead>
              <tr class="bg-[#7cb342] text-sm font-bold text-white">
                <th class="px-4 py-3">Compte</th>
                <th class="px-4 py-3">Libellé</th>
                <th class="px-4 py-3 text-right">Solde N</th>
                <th class="px-4 py-3 text-right">Solde N-1</th>
                <th class="px-4 py-3 text-right">Variation</th>
              </tr>
            </thead>
            <tbody class="bg-white">
              <tr v-for="compte in comptes" :key="compte.numero" class="border-t border-gray-100">
                <td class="px-4 py-3 font-medium text-[#0d3b56]">{{ compte.numero }}</td>
                <td class="px-4 py-3 text-[#0d3b56]">{{ compte.libelle }}</td>
                <td class="px-4 py-3 text-right text-gray-500">{{ formatNumber(compte.soldeN) }}</td>
                <td class="px-4 py-3 text-right text-gray-500">{{ formatNumber(compte.soldeNMoins1) }}</td>
                <td class="px-4 py-3 text-right">
                  <template v-if="compte.sens === 'stable'">
                    <p class="text-gray-500">0</p>
                    <p class="text-gray-500">0,0 %</p>
                  </template>
                  <template v-else>
                    <p class="font-semibold" :class="sensStyles[compte.sens]">
                      {{ compte.sens === 'hausse' ? '+' : '' }}{{ formatNumber(compte.ecart) }}
                    </p>
                    <p class="font-semibold" :class="sensStyles[compte.sens]">
                      {{ compte.sens === 'hausse' ? '+' : '' }}{{ compte.pct.toFixed(1).replace('.', ',') }} %
                    </p>
                  </template>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="mt-3 text-sm text-gray-500">Aucun compte rattaché à ce cycle sur les balances importées.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.scrollbar-hide {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
</style>
