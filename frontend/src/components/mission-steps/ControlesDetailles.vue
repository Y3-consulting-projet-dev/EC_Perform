<script setup>
import CycleRevisionLayout from '../revision/CycleRevisionLayout.vue'
import PapierTravailBloc from '../revision/PapierTravailBloc.vue'
import { formatDateTime } from '../../composables/useCycleRevision'
import { useRevisionStep } from '../../composables/useRevisionStep'

const props = defineProps({
  mission: { type: Object, required: true },
})

const { nav, summary, entry, canEdit } = useRevisionStep(props)

// Les assertions restent stockées dans la section « justification » du cycle.
function saveAssertions() {
  entry.value.scheduleSave('justification')
}

const sousSections = [
  ['Balance âgée', 'Tranches 0-30 / 31-60 / 61-90 / > 90 jours, avec la part de chaque tranche dans le solde.'],
  ['Cut-off', 'Dernières factures avant et premières après la clôture : date de livraison et rattachement.'],
  ['Circularisation', 'Clients circularisés, solde comptable, montant confirmé, écart et statut de la réponse.'],
]
</script>

<template>
  <CycleRevisionLayout
    :entry="entry"
    :summary="summary"
    etape="4d"
    title="Contrôles détaillés"
    subtitle="Tests substantifs : balance âgée, cut-off et circularisation."
  >
    <template #default="{ revision }">
      <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div v-for="[titre, description] in sousSections" :key="titre" class="rounded-lg bg-white p-4 shadow-sm">
          <p class="text-[13px] font-bold text-[#0d3b56]">{{ titre }}</p>
          <p class="mt-1 text-xs text-gray-500">{{ description }}</p>
        </div>
      </div>
      <p class="text-xs text-gray-500">
        Le classeur ci-dessous contient un onglet par contrôle. En mode « Lien Excel », les onglets du fichier déposé sont
        affichés en lecture.
      </p>

      <PapierTravailBloc :mission-id="mission.id" :code="revision.code" etape="4d" :can-edit="canEdit" />

      <div class="rounded-xl bg-white p-5 shadow-sm">
        <h3 class="text-sm font-bold text-[#0d3b56]">Assertions d'audit couvertes par le papier de travail</h3>
        <ul class="mt-2 divide-y divide-gray-100">
          <li v-for="assertion in revision.justification.assertions" :key="assertion.cle" class="flex items-center justify-between gap-3 py-2.5">
            <label class="flex items-center text-[#1a2634] gap-2.5 text-[13px]">
              <input
                v-model="assertion.coche"
                type="checkbox"
                :disabled="!canEdit"
                class="h-4 w-4 accent-[#2f9e6b]"
                @change="saveAssertions"
              />
              {{ assertion.libelle }}
            </label>
            <span v-if="assertion.le" class="text-[11px] text-gray-400">
              {{ assertion.coche ? 'Couverte' : 'Décochée' }} le {{ formatDateTime(assertion.le) }} par {{ assertion.par?.nom }}
            </span>
          </li>
        </ul>
      </div>

      <div class="flex justify-end">
        <button
          type="button"
          class="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-semibold text-[#0d3b56] hover:bg-gray-50"
          @click="nav.goToStep('constats-risques')"
        >
          Passer aux constats →
        </button>
      </div>
    </template>
  </CycleRevisionLayout>
</template>
