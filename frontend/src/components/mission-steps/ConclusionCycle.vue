<script setup>
import { computed, ref } from 'vue'
import CycleRevisionLayout from '../revision/CycleRevisionLayout.vue'
import { NIVEAUX, formatNumber, newId } from '../../composables/useCycleRevision'
import { useRevisionStep } from '../../composables/useRevisionStep'

const props = defineProps({
  mission: { type: Object, required: true },
})

const { nav, summary, entry, revision, canEdit } = useRevisionStep(props)

function save() {
  entry.value.scheduleSave('conclusion')
}

function ajouterAjustement(r) {
  r.conclusion.ajustements.push({ id: newId(), compte: '', libelle: '', sens: 'Débit', montant: 0 })
  save()
}

function supprimerAjustement(r, index) {
  r.conclusion.ajustements.splice(index, 1)
  save()
}

const totaux = computed(() => {
  const ajustements = revision.value?.conclusion.ajustements ?? []
  const somme = (sens) => ajustements.filter((a) => a.sens === sens).reduce((t, a) => t + (Number(a.montant) || 0), 0)
  return { debit: somme('Débit'), credit: somme('Crédit') }
})
const equilibre = computed(() => Math.abs(totaux.value.debit - totaux.value.credit) < 0.5)

const busy = ref(false)
const error = ref('')

// « Compléter la justification » ramène le cycle en 4c, où les constats ouverts de 4e sont listés.
async function choisirDecision(r, decision) {
  if (!canEdit.value) return
  r.conclusion.decision = decision
  save()
  if (decision === 'completer') {
    await entry.value.flush('conclusion')
    nav.goToStep('justification-solde')
  }
}

const peutSoumettre = computed(
  () => canEdit.value && revision.value?.conclusion.decision === 'justifie' && revision.value?.conclusion.synthese.trim(),
)

async function soumettre() {
  busy.value = true
  error.value = ''
  try {
    const updated = await entry.value.soumettre()
    const niveau = NIVEAUX.find((n) => n.code === updated.niveauActif)
    if (niveau) nav.goToStep(niveau.stepId)
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <CycleRevisionLayout
    :entry="entry"
    :summary="summary"
    etape="4f"
    title="Conclusion du cycle"
    subtitle="Synthèse, ajustements proposés et décision avant transmission en revue."
  >
    <template #default="{ revision: r }">
      <div class="rounded-xl bg-white p-5 shadow-sm">
        <h3 class="text-sm font-bold text-[#0d3b56]">Synthèse du cycle</h3>
        <textarea
          v-model="r.conclusion.synthese"
          :disabled="!canEdit"
          rows="5"
          placeholder="Cohérence du solde, points d'attention, ajustements proposés, réserves..."
          class="mt-3 w-full text-[#1a2634] rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#7cb342] disabled:bg-gray-50"
          @input="save"
        ></textarea>
      </div>

      <div class="rounded-xl bg-white shadow-sm">
        <div class="flex items-center justify-between px-5 pt-4">
          <h3 class="text-sm font-bold text-[#0d3b56]">Ajustements proposés</h3>
          <button
            v-if="canEdit"
            type="button"
            class="rounded-md bg-[#0d3b56] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#0a2f45]"
            @click="ajouterAjustement(r)"
          >
            + Ajouter une écriture
          </button>
        </div>
        <div class="mt-3 overflow-x-auto">
          <table class="w-full text-left text-[12.5px]">
            <thead>
              <tr class="bg-[#eef1f4] text-[11px] uppercase tracking-wide text-gray-500">
                <th class="px-3 py-2.5">Compte</th>
                <th class="px-3 py-2.5">Libellé</th>
                <th class="px-3 py-2.5">Sens</th>
                <th class="px-3 py-2.5 text-right">Montant</th>
                <th v-if="canEdit" class="px-3 py-2.5"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(ajustement, index) in r.conclusion.ajustements" :key="ajustement.id" class="border-t border-gray-100">
                <td class="px-3 py-1.5 text-gray-500">
                  <input
                    v-model="ajustement.compte"
                    :disabled="!canEdit"
                    type="text"
                    placeholder="681000"
                    class="w-28 rounded-md border border-gray-200 px-2 py-1 text-xs outline-none focus:ring-2 focus:ring-[#7cb342] disabled:border-transparent disabled:bg-transparent"
                    @input="save"
                  />
                </td>
                <td class="px-3 py-1.5 text-gray-500">
                  <input
                    v-model="ajustement.libelle"
                    :disabled="!canEdit"
                    type="text"
                    class="w-full rounded-md border border-gray-200 px-2 py-1 text-xs outline-none focus:ring-2 focus:ring-[#7cb342] disabled:border-transparent disabled:bg-transparent"
                    @input="save"
                  />
                </td>
                <td class="px-3 py-1.5 text-gray-500">
                  <select
                    v-model="ajustement.sens"
                    :disabled="!canEdit"
                    class="rounded-md border border-gray-200 px-2 py-1 text-xs disabled:border-transparent disabled:bg-transparent"
                    @change="save"
                  >
                    <option>Débit</option>
                    <option>Crédit</option>
                  </select>
                </td>
                <td class="px-3 py-1.5 text-right text-gray-500">
                  <input
                    v-if="canEdit"
                    v-model.number="ajustement.montant"
                    type="number"
                    min="0"
                    class="w-36 rounded-md border border-gray-200 px-2 py-1 text-right text-xs outline-none focus:ring-2 focus:ring-[#7cb342]"
                    @input="save"
                  />
                  <span v-else>{{ formatNumber(ajustement.montant) }}</span>
                </td>
                <td v-if="canEdit" class="px-3 py-1.5 text-right">
                  <button type="button" class="text-gray-400 hover:text-[#c1483f]" aria-label="Supprimer l'écriture" @click="supprimerAjustement(r, index)">
                    ✕
                  </button>
                </td>
              </tr>
              <tr v-if="!r.conclusion.ajustements.length">
                <td colspan="5" class="px-3 py-4 text-center text-gray-400">Aucun ajustement proposé.</td>
              </tr>
              <tr v-else class="border-t border-gray-200 bg-[#fafbfc] text-xs font-semibold">
                <td colspan="3" class="px-3 py-2">
                  Total débit {{ formatNumber(totaux.debit) }} · Total crédit {{ formatNumber(totaux.credit) }}
                </td>
                <td :colspan="canEdit ? 2 : 1" class="px-3 py-2 text-right" :class="equilibre ? 'text-[#2f9e6b]' : 'text-[#c1483f]'">
                  {{ equilibre ? 'Écriture équilibrée' : 'Écriture déséquilibrée' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="rounded-xl bg-white p-5 shadow-sm">
        <h3 class="text-sm font-bold text-[#0d3b56]">Décision</h3>
        <div class="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <button
            v-for="[decision, icon, label] in [['justifie', '✅', 'Cycle justifié'], ['completer', '🔁', 'Compléter la justification']]"
            :key="decision"
            type="button"
            :disabled="!canEdit"
            class="rounded-xl border-2 p-4 text-center transition disabled:cursor-default"
            :class="r.conclusion.decision === decision ? 'border-[#2c6e8f] bg-[#eaf1f7]' : 'border-gray-200 bg-white hover:border-gray-300'"
            @click="choisirDecision(r, decision)"
          >
            <span class="block text-xl">{{ icon }}</span>
            <span class="text-[13px] font-bold text-[#0d3b56]">{{ label }}</span>
          </button>
        </div>
        <p class="mt-2 text-xs text-gray-500">
          « Compléter la justification » renvoie le cycle en 4c avec les constats ouverts de 4e listés en tête d'écran.
        </p>
      </div>

      <div class="flex flex-wrap items-center justify-end gap-3">
        <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
        <p v-else-if="canEdit && !peutSoumettre" class="text-xs text-gray-500">
          La synthèse et la décision « Cycle justifié » sont requises pour soumettre.
        </p>
        <button
          v-if="!r.verrouille"
          type="button"
          :disabled="!peutSoumettre || busy"
          class="rounded-lg bg-[#0d3b56] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#0a2f45] disabled:opacity-45"
          @click="soumettre"
        >
          {{ busy ? 'Soumission…' : r.retourDe ? `Resoumettre en revue ${NIVEAUX.find((n) => n.code === r.retourDe).label} →` : 'Soumettre pour revue (Phase 5) →' }}
        </button>
      </div>
    </template>
  </CycleRevisionLayout>
</template>
