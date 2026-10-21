<script setup>
import CycleRevisionLayout from '../revision/CycleRevisionLayout.vue'
import PapierTravailBloc from '../revision/PapierTravailBloc.vue'
import { useRevisionStep } from '../../composables/useRevisionStep'

const props = defineProps({
  mission: { type: Object, required: true },
})

const { nav, summary, entry, canEdit } = useRevisionStep(props)

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
