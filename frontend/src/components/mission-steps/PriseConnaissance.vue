<script setup>
import { ref } from 'vue'
import CycleRevisionLayout from '../revision/CycleRevisionLayout.vue'
import FicheSignaletique from './FicheSignaletique.vue'
import { useRevisionStep } from '../../composables/useRevisionStep'

const props = defineProps({
  mission: { type: Object, required: true },
})

const { nav, summary, entry, canEdit } = useRevisionStep(props)

const nouveauRisque = ref('')

function save() {
  entry.value.scheduleSave('priseConnaissance')
}

function ajouterRisque(revision) {
  const risque = nouveauRisque.value.trim()
  if (risque && !revision.priseConnaissance.risques.includes(risque)) {
    revision.priseConnaissance.risques.push(risque)
    save()
  }
  nouveauRisque.value = ''
}

function supprimerRisque(revision, index) {
  revision.priseConnaissance.risques.splice(index, 1)
  save()
}
</script>

<template>
  <CycleRevisionLayout
    :entry="entry"
    :summary="summary"
    etape="4a"
    title="Prise de connaissance"
    subtitle="Comprendre le processus métier et les risques spécifiques du cycle avant de démarrer les travaux."
  >
    <template #default="{ revision }">
      <FicheSignaletique :mission="mission" />

      <div class="rounded-xl bg-white p-5 shadow-sm">
        <h3 class="text-sm font-bold text-[#0d3b56]">Description du processus métier</h3>
        <textarea
          v-model="revision.priseConnaissance.processus"
          :disabled="!canEdit"
          rows="5"
          placeholder="Flux, acteurs, outils (ERP...), contrôles internes clés du cycle..."
          class="mt-3 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-[#1a2634] outline-none focus:ring-2 focus:ring-[#7cb342] disabled:bg-gray-50"
          @input="save"
        ></textarea>
      </div>

      <div class="rounded-xl bg-white p-5 shadow-sm">
        <h3 class="text-sm font-bold text-[#0d3b56]">Risques spécifiques identifiés</h3>
        <div class="mt-3 flex flex-wrap gap-2">
          <span
            v-for="(risque, index) in revision.priseConnaissance.risques"
            :key="risque"
            class="flex items-center gap-1.5 rounded-full bg-[#eef1f4] px-3 py-1 text-xs font-semibold text-[#1a2634]"
          >
            {{ risque }}
            <button
              v-if="canEdit"
              type="button"
              class="text-gray-400 hover:text-[#c1483f]"
              :aria-label="`Supprimer ${risque}`"
              @click="supprimerRisque(revision, index)"
            >
              ✕
            </button>
          </span>
          <span v-if="!revision.priseConnaissance.risques.length" class="text-xs text-gray-400">Aucun risque identifié.</span>
        </div>
        <form v-if="canEdit" class="mt-3 flex gap-2" @submit.prevent="ajouterRisque(revision)">
          <input
            v-model="nouveauRisque"
            type="text"
            placeholder="Ex. Cut-off ventes, créances douteuses sous-provisionnées..."
            class="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm text-[#1a2634] outline-none focus:ring-2 focus:ring-[#7cb342]"
          />
          <button type="submit" class="rounded-lg bg-[#0d3b56] px-4 py-2 text-sm font-semibold text-white hover:bg-[#0a2f45]">
            Ajouter
          </button>
        </form>
      </div>

      <div class="rounded-xl bg-white p-5 shadow-sm">
        <h3 class="text-sm font-bold text-[#0d3b56]">Référentiel applicable</h3>
        <textarea
          v-model="revision.priseConnaissance.referentiel"
          :disabled="!canEdit"
          rows="2"
          placeholder="SYSCOHADA révisé — comptes concernés, normes internes du cabinet, seuils..."
          class="mt-3 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-[#1a2634] outline-none focus:ring-2 focus:ring-[#7cb342] disabled:bg-gray-50"
          @input="save"
        ></textarea>
      </div>

      <div class="flex justify-end">
        <button
          type="button"
          class="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-semibold text-[#0d3b56] hover:bg-gray-50"
          @click="nav.goToStep('lead-cycle')"
        >
          Passer au lead du cycle →
        </button>
      </div>
    </template>
  </CycleRevisionLayout>
</template>
