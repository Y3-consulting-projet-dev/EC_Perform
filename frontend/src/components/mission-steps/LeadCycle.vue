<script setup>
import { computed, ref, watch } from 'vue'
import CycleRevisionLayout from '../revision/CycleRevisionLayout.vue'
import PapierTravailBloc from '../revision/PapierTravailBloc.vue'
import { apiFetch, formatNumber } from '../../composables/useCycleRevision'
import { useRevisionStep } from '../../composables/useRevisionStep'

const props = defineProps({
  mission: { type: Object, required: true },
})

const { nav, summary, entry, canEdit } = useRevisionStep(props)

const sensStyles = { hausse: 'text-green-600', baisse: 'text-red-600', stable: 'text-gray-500' }

// Soldes calculés depuis les balances N / N-1 de la mission (Phase 3), jamais saisis.
const lead = ref(null)
const comptes = ref([])
const loading = ref(false)
const error = ref('')

async function fetchLead(code) {
  if (!code) return
  loading.value = true
  error.value = ''
  try {
    const [cycles, detail] = await Promise.all([
      apiFetch(`/missions/${props.mission.id}/cycles`),
      apiFetch(`/missions/${props.mission.id}/cycles/${code}`),
    ])
    lead.value = cycles.cycles.find((c) => c.code === code) ?? null
    comptes.value = detail.comptes.map((row) => {
      const ecart = row.soldeN - row.soldeNMoins1
      const pct = row.soldeNMoins1 ? (ecart / Math.abs(row.soldeNMoins1)) * 100 : null
      return { ...row, ecart, pct, sens: ecart > 0 ? 'hausse' : ecart < 0 ? 'baisse' : 'stable' }
    })
  } catch (e) {
    lead.value = null
    comptes.value = []
    error.value =
      e.status === 404
        ? 'Les balances N et N-1 sont nécessaires pour calculer le lead : déposez-les en Phase 1.'
        : e.message
  } finally {
    loading.value = false
  }
}

watch(() => nav.selectedCycle.value, fetchLead, { immediate: true })

const variationLabel = computed(() => {
  if (!lead.value || lead.value.variationPct === null) return '—'
  const sign = lead.value.variationPct > 0 ? '+' : ''
  return `${sign}${lead.value.variationPct.toFixed(1).replace('.', ',')} %`
})

function commentaire(revision, numero) {
  return revision.lead.commentaires[numero] ?? ''
}

function setCommentaire(revision, numero, value) {
  revision.lead.commentaires = { ...revision.lead.commentaires, [numero]: value }
  entry.value.scheduleSave('lead')
}
</script>

<template>
  <CycleRevisionLayout
    :entry="entry"
    :summary="summary"
    etape="4b"
    title="Lead du cycle"
    subtitle="Rapprochement des soldes N / N-1 compte par compte."
  >
    <template #default="{ revision }">
      <p v-if="loading" class="text-sm text-gray-400">Calcul du lead...</p>
      <p v-else-if="error" class="rounded-lg bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-700">{{ error }}</p>

      <template v-else-if="lead">
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div class="rounded-lg bg-white p-4 shadow-sm">
            <p class="text-xs text-gray-500">Solde N</p>
            <p class="mt-1 text-[15px] font-bold text-[#0d3b56]">{{ lead.soldeN }}</p>
          </div>
          <div class="rounded-lg bg-white p-4 shadow-sm">
            <p class="text-xs text-gray-500">Solde N-1</p>
            <p class="mt-1 text-[15px] font-bold text-[#0d3b56]">{{ lead.soldeNMoins1 }}</p>
          </div>
          <div class="rounded-lg bg-white p-4 shadow-sm">
            <p class="text-xs text-gray-500">Variation</p>
            <p class="mt-1 text-[15px] font-bold" :class="sensStyles[lead.sens]">{{ variationLabel }}</p>
          </div>
        </div>

        <div class="overflow-x-auto rounded-xl bg-white shadow-sm">
          <table class="w-full text-left text-[12.5px]">
            <thead>
              <tr class="bg-[#eef1f4] text-[11px] uppercase tracking-wide text-gray-500">
                <th class="px-3 py-2.5">Compte</th>
                <th class="px-3 py-2.5">Libellé</th>
                <th class="px-3 py-2.5 text-right">Solde N</th>
                <th class="px-3 py-2.5 text-right">Solde N-1</th>
                <th class="px-3 py-2.5 text-right">Variation</th>
                <th class="w-1/4 px-3 py-2.5">Commentaire</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="compte in comptes" :key="compte.numero" class="border-t border-gray-100">
                <td class="px-3 py-2 font-medium text-[#0d3b56]">{{ compte.numero }}</td>
                <td class="px-3 py-2 text-gray-500">{{ compte.libelle }}</td>
                <td class="px-3 py-2 text-gray-500 text-right">{{ formatNumber(compte.soldeN) }}</td>
                <td class="px-3 py-2 text-right text-gray-500">{{ formatNumber(compte.soldeNMoins1) }}</td>
                <td class="px-3 py-2 text-right font-semibold" :class="sensStyles[compte.sens]">
                  {{ compte.ecart > 0 ? '+' : '' }}{{ formatNumber(compte.ecart) }}
                  <span v-if="compte.pct !== null" class="block text-[11px]">
                    {{ compte.pct > 0 ? '+' : '' }}{{ compte.pct.toFixed(1).replace('.', ',') }} %
                  </span>
                </td>
                <td class="px-3 py-1.5">
                  <input
                    :value="commentaire(revision, compte.numero)"
                    :disabled="!canEdit"
                    type="text"
                    :placeholder="compte.sens !== 'stable' ? 'Variation à expliquer' : ''"
                    class="w-full rounded-md border border-gray-200 px-2 py-1 text-xs text-[#1a2634] outline-none focus:ring-2 focus:ring-[#7cb342] disabled:border-transparent disabled:bg-transparent"
                    @input="setCommentaire(revision, compte.numero, $event.target.value)"
                  />
                </td>
              </tr>
              <tr v-if="!comptes.length">
                <td colspan="6" class="px-3 py-4 text-center text-gray-400">Aucun compte rattaché à ce cycle sur les balances importées.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <PapierTravailBloc :mission-id="mission.id" :code="revision.code" etape="4b" :can-edit="canEdit" />

      <div class="flex items-center justify-between">
        <p class="text-xs text-gray-500">Rapprochement N / N-1 pré-rempli depuis les balances, affiné dans le PT.</p>
        <button
          type="button"
          class="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-semibold text-[#0d3b56] hover:bg-gray-50"
          @click="nav.goToStep('justification-solde')"
        >
          Passer à la justification →
        </button>
      </div>
    </template>
  </CycleRevisionLayout>
</template>
