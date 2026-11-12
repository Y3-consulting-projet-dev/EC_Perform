<script setup>
import { computed, ref } from 'vue'
import CycleRevisionLayout from '../revision/CycleRevisionLayout.vue'
import PointRevueCard from '../revision/PointRevueCard.vue'
import { ETAPES, NIVEAUX, formatDateTime } from '../../composables/useCycleRevision'
import { useRevisionStep } from '../../composables/useRevisionStep'

const props = defineProps({
  mission: { type: Object, required: true },
  niveau: { type: String, required: true },
})

const { summary, entry, revision } = useRevisionStep(props, { niveau: props.niveau })

const index = NIVEAUX.findIndex((n) => n.code === props.niveau)
const label = NIVEAUX[index].label
const precedent = index > 0 ? `le ${NIVEAUX[index - 1].label}` : 'le collaborateur'
const suivant = NIVEAUX[index + 1]
const libelleValider = suivant ? `✓ Valider et transmettre au ${suivant.label}` : '✓ Valider — cycle clôturé'

const etape = computed(() => revision.value?.chaine.find((s) => s.niveau === props.niveau))
const actif = computed(() => revision.value?.niveauActif === props.niveau)
const aLeDroit = computed(() => !!revision.value?.droits.revue[props.niveau])
const peutAgir = computed(() => actif.value && aLeDroit.value)

const checklist = computed(() => revision.value?.checklists[props.niveau])
const checklistComplete = computed(() => checklist.value?.items.every((i) => i.coche))

const points = computed(() => (entry.value?.points ?? []).filter((p) => p.niveau === props.niveau))
const pointsOuverts = computed(() => points.value.filter((p) => p.statut === 'ouvert'))

const busy = ref(false)
const error = ref('')

async function run(fn) {
  busy.value = true
  error.value = ''
  try {
    await fn()
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

function cocher(item, event) {
  run(() => entry.value.cocherChecklist(props.niveau, item.cle, event.target.checked))
}

const nouveauPoint = ref({ corps: '', etape: '4c', ref: '' })

function creerPoint() {
  run(async () => {
    const { corps, etape: cibleEtape, ref: feuille } = nouveauPoint.value
    await entry.value.creerPoint(props.niveau, corps, { etape: cibleEtape, onglet: feuille.trim() || null })
    nouveauPoint.value = { corps: '', etape: cibleEtape, ref: '' }
  })
}

const commentaireRetour = ref('')

function valider() {
  run(() => entry.value.valider(props.niveau))
}

function retour() {
  run(async () => {
    await entry.value.retour(props.niveau, commentaireRetour.value)
    commentaireRetour.value = ''
  })
}

const messageBlocage = computed(() => {
  if (pointsOuverts.value.length) {
    const refs = pointsOuverts.value.map((p) => `REF ${p.ref}`).join(', ')
    return `${pointsOuverts.value.length} point(s) encore ouvert(s) (${refs}) : la validation est bloquée tant qu'ils ne sont pas Cleared.`
  }
  if (!checklistComplete.value) return 'La grille de revue doit être entièrement cochée avant validation.'
  return 'Aucun point ouvert : le cycle peut être validé.'
})
</script>

<template>
  <CycleRevisionLayout
    :entry="entry"
    :summary="summary"
    :niveau="niveau"
    :title="`Revue ${label}`"
    :subtitle="checklist ? checklist.objectif : ''"
  >
    <template #default="{ revision: r }">
      <p
        v-if="etape?.etat === 'en_attente'"
        class="rounded-lg border border-dashed border-gray-300 bg-[#f4f6f8] px-4 py-2.5 text-xs text-gray-500"
      >
        🔒 Ce niveau s'active une fois que {{ precedent }} a validé le cycle (tous ses points clôturés). Aperçu pour référence.
      </p>
      <p v-else-if="etape?.etat === 'retour'" class="rounded-lg bg-[#fbeee0] px-4 py-2.5 text-xs font-semibold text-[#9a6420]">
        ↩ Cycle renvoyé au collaborateur pour modification : il reviendra directement à ce niveau après resoumission.
      </p>
      <p v-else-if="etape?.etat === 'fait'" class="rounded-lg bg-[#e6f3ec] px-4 py-2.5 text-xs font-semibold text-[#2f9e6b]">
        ✓ Validé le {{ formatDateTime(etape.le) }} par {{ etape.par }}.
        <span v-if="etape.modifieApresValidation" class="text-[#c9862c]">Les travaux ont été modifiés depuis cette validation.</span>
      </p>
      <p v-else-if="actif && !aLeDroit" class="rounded-lg bg-[#f4f6f8] px-4 py-2.5 text-xs text-gray-500">
        Votre grade ne permet pas d'intervenir au niveau {{ label }} : consultation seule.
      </p>

      <div class="rounded-xl bg-white p-5 shadow-sm">
        <h3 class="text-sm font-bold text-[#0d3b56]">Grille de revue {{ label }}</h3>
        <ul class="mt-2 divide-y divide-gray-100 text-gray-500">
          <li v-for="item in checklist.items" :key="item.cle" class="flex items-center justify-between gap-3 py-2.5">
            <label class="flex items-center gap-2.5 text-[13px]">
              <input
                type="checkbox"
                :checked="item.coche"
                :disabled="!peutAgir || busy"
                class="h-4 w-4 accent-[#2f9e6b]"
                @change="cocher(item, $event)"
              />
              {{ item.libelle }}
            </label>
            <span v-if="item.le" class="shrink-0 text-[11px] text-gray-400">{{ item.par?.nom }} · {{ formatDateTime(item.le) }}</span>
          </li>
        </ul>
      </div>

      <div class="space-y-3 rounded-xl bg-white p-5 shadow-sm">
        <h3 class="text-sm font-bold text-[#0d3b56]">Points de revue {{ label }} — Cycle {{ r.code }} · {{ r.libelle }}</h3>
        <PointRevueCard
          v-for="point in points"
          :key="point.id"
          :point="point"
          :entry="entry"
          :can-respond="r.droits.repondre && !r.verrouille"
          :can-change-status="peutAgir"
        />
        <p v-if="!points.length" class="text-[13px] text-gray-400">Aucun point de revue à ce niveau.</p>

        <form v-if="peutAgir" class="space-y-2 rounded-lg bg-[#f4f6f8] p-3" @submit.prevent="creerPoint">
          <p class="text-xs font-bold text-[#0d3b56]">+ Ajouter un point de revue</p>
          <textarea
            v-model="nouveauPoint.corps"
            rows="3"
            placeholder="Observation à traiter par le collaborateur..."
            class="w-full text-gray-500 rounded-md border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#7cb342]"
          ></textarea>
          <div class="flex flex-wrap items-center gap-2">
            <select v-model="nouveauPoint.etape" class="rounded-md text-gray-500 border border-gray-200 bg-white px-2 py-1.5 text-xs">
              <option v-for="e in ETAPES" :key="e.code" :value="e.code">{{ e.code }} · {{ e.label }}</option>
            </select>
            <input
              v-model="nouveauPoint.ref"
              type="text"
              placeholder="Feuille / onglet / cellule (facultatif)"
              class="min-w-56 text-gray-500 flex-1 rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs outline-none focus:ring-2 focus:ring-[#7cb342]"
            />
            <button
              type="submit"
              :disabled="busy || !nouveauPoint.corps.trim()"
              class="rounded-md bg-[#0d3b56] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#0a2f45] disabled:opacity-50"
            >
              Ajouter le point
            </button>
          </div>
        </form>
      </div>

      <div class="rounded-xl bg-white p-5 shadow-sm">
        <h3 class="text-sm font-bold text-[#0d3b56]">Décision du {{ label }}</h3>
        <p v-if="peutAgir" class="mt-1 text-xs" :class="pointsOuverts.length || !checklistComplete ? 'text-[#c9862c]' : 'text-[#2f9e6b]'">
          {{ messageBlocage }}
        </p>
        <input
          v-if="peutAgir"
          v-model="commentaireRetour"
          type="text"
          placeholder="Commentaire accompagnant un retour (facultatif)"
          class="mt-3 text-gray-500 w-full rounded-md border border-gray-200 px-3 py-1.5 text-xs outline-none focus:ring-2 focus:ring-[#7cb342]"
        />
        <div class="mt-3 flex flex-wrap gap-2.5">
          <button
            type="button"
            :disabled="!peutAgir || busy || pointsOuverts.length > 0 || !checklistComplete"
            class="rounded-lg bg-[#0d3b56] px-4 py-2 text-[13px] font-semibold text-white hover:bg-[#0a2f45] disabled:cursor-not-allowed disabled:opacity-45"
            @click="valider"
          >
            {{ libelleValider }}
          </button>
          <button
            type="button"
            :disabled="!peutAgir || busy || !pointsOuverts.length"
            :title="!pointsOuverts.length ? 'Ajoutez un point de revue ouvert avant de renvoyer le cycle' : ''"
            class="rounded-lg border border-[#f0c9c5] bg-white px-4 py-2 text-[13px] font-semibold text-[#c1483f] hover:bg-[#fdf3f2] disabled:cursor-not-allowed disabled:opacity-45"
            @click="retour"
          >
            ↩ Retour pour modification au collaborateur
          </button>
        </div>
        <p v-if="error" class="mt-2 text-sm text-red-600">{{ error }}</p>
      </div>
    </template>
  </CycleRevisionLayout>
</template>
