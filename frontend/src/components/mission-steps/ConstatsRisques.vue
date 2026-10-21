<script setup>
import CycleRevisionLayout from '../revision/CycleRevisionLayout.vue'
import { newId } from '../../composables/useCycleRevision'
import { useRevisionStep } from '../../composables/useRevisionStep'

const props = defineProps({
  mission: { type: Object, required: true },
})

const { nav, summary, entry, canEdit } = useRevisionStep(props)

const FAMILLES = ['Comptabilisation', 'Évaluation', 'Présentation', 'Gouvernance', "Système d'information"]
const SEVERITES = ['Faible', 'Moyen', 'Élevé']
const STATUTS = ['Ouvert', 'Noté', 'Clôturé']

const severiteStyles = {
  Élevé: 'bg-[#fbe6e4] text-[#c1483f]',
  Moyen: 'bg-[#fbeee0] text-[#c9862c]',
  Faible: 'bg-[#e6f3ec] text-[#2f9e6b]',
}
const statutStyles = {
  Ouvert: 'bg-[#fbeee0] text-[#c9862c]',
  Noté: 'bg-[#e6f3ec] text-[#2f9e6b]',
  Clôturé: 'bg-[#eef1f4] text-gray-500',
}

function save() {
  entry.value.scheduleSave('constats')
}

function ajouter(r) {
  r.constats.push({ id: newId(), famille: 'Évaluation', constat: '', severite: 'Moyen', recommandation: '', statut: 'Ouvert' })
  save()
}

function supprimer(r, index) {
  r.constats.splice(index, 1)
  save()
}
</script>

<template>
  <CycleRevisionLayout
    :entry="entry"
    :summary="summary"
    etape="4e"
    title="Constats / Risques"
    subtitle="Recensement des anomalies détectées, classées par famille de risque."
  >
    <template #default="{ revision: r }">
      <div class="overflow-x-auto rounded-xl bg-white shadow-sm">
        <table class="w-full text-left text-[12.5px]">
          <thead>
            <tr class="bg-[#eef1f4] text-[11px] uppercase tracking-wide text-gray-500">
              <th class="px-3 py-2.5">Famille</th>
              <th class="px-3 py-2.5">Constat</th>
              <th class="px-3 py-2.5">Sévérité</th>
              <th class="px-3 py-2.5">Recommandation</th>
              <th class="px-3 py-2.5">Statut</th>
              <th v-if="canEdit" class="px-3 py-2.5"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(constat, index) in r.constats" :key="constat.id" class="border-t border-gray-100 align-top">
              <td class="px-3 py-2 text-gray-500">
                <select
                  v-model="constat.famille"
                  :disabled="!canEdit"
                  class="rounded-md border border-gray-200 px-2 py-1 text-xs disabled:border-transparent disabled:bg-transparent"
                  @change="save"
                >
                  <option v-for="f in FAMILLES" :key="f" :value="f">{{ f }}</option>
                </select>
              </td>
              <td class="w-1/3 px-3 py-2 text-gray-500">
                <textarea
                  v-model="constat.constat"
                  :disabled="!canEdit"
                  rows="2"
                  placeholder="Anomalie constatée..."
                  class="w-full rounded-md border border-gray-200 px-2 py-1 text-xs outline-none focus:ring-2 focus:ring-[#7cb342] disabled:border-transparent disabled:bg-transparent"
                  @input="save"
                ></textarea>
              </td>
              <td class="px-3 py-2">
                <select
                  v-model="constat.severite"
                  :disabled="!canEdit"
                  class="rounded-full border-0 px-2.5 py-1 text-[11px] font-bold outline-none"
                  :class="severiteStyles[constat.severite]"
                  @change="save"
                >
                  <option v-for="s in SEVERITES" :key="s" :value="s">{{ s }}</option>
                </select>
              </td>
              <td class="w-1/4 px-3 py-2 text-gray-500">
                <textarea
                  v-model="constat.recommandation"
                  :disabled="!canEdit"
                  rows="2"
                  class="w-full rounded-md border border-gray-200 px-2 py-1 text-xs outline-none focus:ring-2 focus:ring-[#7cb342] disabled:border-transparent disabled:bg-transparent"
                  @input="save"
                ></textarea>
              </td>
              <td class="px-3 py-2">
                <select
                  v-model="constat.statut"
                  :disabled="!canEdit"
                  class="rounded-full border-0 px-2.5 py-1 text-[11px] font-bold outline-none"
                  :class="statutStyles[constat.statut]"
                  @change="save"
                >
                  <option v-for="s in STATUTS" :key="s" :value="s">{{ s }}</option>
                </select>
              </td>
              <td v-if="canEdit" class="px-3 py-2 text-right">
                <button type="button" class="text-gray-400 hover:text-[#c1483f]" aria-label="Supprimer le constat" @click="supprimer(r, index)">
                  ✕
                </button>
              </td>
            </tr>
            <tr v-if="!r.constats.length">
              <td colspan="6" class="px-3 py-4 text-center text-gray-400">Aucun constat.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="flex items-center justify-between">
        <button
          v-if="canEdit"
          type="button"
          class="rounded-lg bg-[#0d3b56] px-4 py-2 text-sm font-semibold text-white hover:bg-[#0a2f45]"
          @click="ajouter(r)"
        >
          + Ajouter un constat
        </button>
        <span v-else></span>
        <button
          type="button"
          class="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-semibold text-[#0d3b56] hover:bg-gray-50"
          @click="nav.goToStep('conclusion-cycle')"
        >
          Passer à la conclusion →
        </button>
      </div>
    </template>
  </CycleRevisionLayout>
</template>
