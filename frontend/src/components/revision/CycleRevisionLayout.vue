<script setup>
import { computed, inject } from 'vue'
import { ETAPES, NIVEAUX, formatDateTime } from '../../composables/useCycleRevision'
import CycleSelector from './CycleSelector.vue'
import PointRevueCard from './PointRevueCard.vue'
import ValidationStepper from './ValidationStepper.vue'

// Gabarit commun des écrans d'un cycle : sélecteur de cycle, chaîne de validation, onglets
// 4a-4f | Revue, bandeaux de verrouillage / retour, et points de revue épinglés sur l'étape.
const props = defineProps({
  entry: { type: Object, default: null },
  summary: { type: Object, required: true },
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  etape: { type: String, default: null },
  niveau: { type: String, default: null },
})

const nav = inject('revisionNav')
const revision = computed(() => props.entry?.revision ?? null)

const NIVEAU_LABELS = Object.fromEntries(NIVEAUX.map((n) => [n.code, n.label]))

const niveauEtat = computed(() =>
  Object.fromEntries((revision.value?.chaine ?? []).map((step) => [step.niveau, step.etat])),
)

const pointsEpingles = computed(() =>
  (props.entry?.points ?? []).filter((p) => p.statut === 'ouvert' && p.cible.etape === props.etape),
)
const autresPointsOuverts = computed(() =>
  (props.entry?.points ?? []).filter((p) => p.statut === 'ouvert' && p.cible.etape !== props.etape),
)

const saveLabel = computed(() => {
  if (!props.entry) return ''
  if (props.entry.saving) return 'Enregistrement…'
  if (props.entry.lastSavedAt) return `Enregistré le ${formatDateTime(props.entry.lastSavedAt)}`
  if (revision.value?.updatedAt) {
    return `Dernière modification le ${formatDateTime(revision.value.updatedAt)} par ${revision.value.updatedBy?.nom ?? '—'}`
  }
  return ''
})

const soumission = computed(() => revision.value?.chaine?.[0])
</script>

<template>
  <div class="mt-4 space-y-4">
    <div class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-lg font-extrabold text-[#0d3b56]">
          {{ title }}
          <span v-if="revision" class="ml-2 rounded-full bg-[#eaf1f7] px-2.5 py-0.5 align-middle text-[11px] font-bold text-[#2c6e8f]">
            Cycle {{ revision.code }} · {{ revision.libelle }}
          </span>
        </h1>
        <p v-if="subtitle" class="text-[13px] text-gray-500">{{ subtitle }}</p>
        <p v-if="revision?.collaborateur" class="text-xs text-gray-400">Préparé par {{ revision.collaborateur.nom }}</p>
      </div>
      <p v-if="saveLabel" class="text-xs text-gray-400">{{ saveLabel }}</p>
    </div>

    <CycleSelector
      v-if="summary.loaded"
      :cycles="summary.cycles"
      :selected="nav.selectedCycle.value"
      @select="(code) => (nav.selectedCycle.value = code)"
    />
    <p v-else-if="summary.error" class="text-sm text-red-600">{{ summary.error }}</p>

    <p v-if="!entry || (entry.loading && !revision)" class="text-sm text-gray-400">Chargement du cycle...</p>
    <p v-else-if="entry.error && !revision" class="text-sm text-red-600">{{ entry.error }}</p>

    <template v-if="revision">
      <ValidationStepper :chaine="revision.chaine" />

      <nav class="flex flex-wrap gap-1 border-b border-gray-200">
        <button
          v-for="e in ETAPES"
          :key="e.code"
          type="button"
          class="-mb-px whitespace-nowrap border-b-2 px-2 py-2 text-[11.5px] font-semibold transition"
          :class="etape === e.code ? 'border-[#2c6e8f] text-[#0d3b56]' : 'border-transparent text-gray-500 hover:text-[#0d3b56]'"
          @click="nav.goToStep(e.stepId)"
        >
          {{ e.code }} · {{ e.label }}
        </button>
        <span class="mx-1 my-1.5 w-px bg-gray-200"></span>
        <span class="self-center pl-1 text-[11px] font-bold uppercase tracking-wide text-gray-400">Revue</span>
        <button
          v-for="n in NIVEAUX"
          :key="n.code"
          type="button"
          class="-mb-px whitespace-nowrap border-b-2 px-2 py-2 text-[11.5px] font-semibold transition"
          :class="niveau === n.code ? 'border-[#2c6e8f] text-[#0d3b56]' : 'border-transparent text-gray-500 hover:text-[#0d3b56]'"
          @click="nav.goToStep(n.stepId)"
        >
          {{ n.label }}<span v-if="niveauEtat[n.code] === 'en_attente'"> 🔒</span>
          <span v-if="revision.pointsOuverts[n.code]" class="ml-1 rounded-full bg-[#fbeee0] px-1.5 text-[10px] text-[#c9862c]">
            {{ revision.pointsOuverts[n.code] }}
          </span>
        </button>
      </nav>

      <div
        v-if="entry.error"
        class="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700"
      >
        <span>{{ entry.error }}</span>
        <button
          v-if="entry.conflict"
          type="button"
          class="rounded-md bg-white px-3 py-1 text-xs font-semibold text-red-700 shadow-sm"
          @click="entry.load()"
        >
          Recharger la dernière version
        </button>
      </div>

      <template v-if="etape">
        <p
          v-if="revision.verrouille"
          class="rounded-lg border border-dashed border-gray-300 bg-[#f4f6f8] px-4 py-2.5 text-xs text-gray-500"
        >
          🔒
          <template v-if="revision.statut === 'cloture'">Cycle clôturé : les travaux sont archivés en lecture seule.</template>
          <template v-else>
            Cycle soumis le {{ formatDateTime(soumission?.le) }}, en revue {{ NIVEAU_LABELS[revision.niveauActif] }} : les
            travaux sont en lecture seule jusqu'à un éventuel retour pour modification.
          </template>
        </p>
        <p
          v-else-if="!revision.droits.editer"
          class="rounded-lg border border-dashed border-gray-300 bg-[#f4f6f8] px-4 py-2.5 text-xs text-gray-500"
        >
          Ce cycle est affecté à un autre collaborateur : consultation seule.
        </p>
        <p v-else-if="revision.retourDe" class="rounded-lg bg-[#fbeee0] px-4 py-2.5 text-xs font-semibold text-[#9a6420]">
          ↩ Cycle renvoyé par la revue {{ NIVEAU_LABELS[revision.retourDe] }}. Traitez les points ouverts, répondez-y, puis
          resoumettez depuis 4f : le cycle reviendra directement en revue {{ NIVEAU_LABELS[revision.retourDe] }}.
        </p>

        <div v-if="pointsEpingles.length" class="space-y-2">
          <p class="text-xs font-bold uppercase tracking-wide text-[#c9862c]">
            📌 Points de revue ouverts sur cette étape ({{ pointsEpingles.length }})
          </p>
          <PointRevueCard
            v-for="point in pointsEpingles"
            :key="point.id"
            :point="point"
            :entry="entry"
            :can-respond="revision.droits.repondre"
            :show-go-to="false"
          />
        </div>
        <p v-if="autresPointsOuverts.length" class="text-xs text-gray-500">
          {{ autresPointsOuverts.length }} autre(s) point(s) ouvert(s) sur :
          <button
            v-for="code in [...new Set(autresPointsOuverts.map((p) => p.cible.etape))]"
            :key="code"
            type="button"
            class="ml-1 font-semibold text-[#2c6e8f] hover:underline"
            @click="nav.goToStep(ETAPES.find((e) => e.code === code).stepId)"
          >
            {{ code }}
          </button>
        </p>
      </template>

      <slot :revision="revision" />
    </template>
  </div>
</template>
