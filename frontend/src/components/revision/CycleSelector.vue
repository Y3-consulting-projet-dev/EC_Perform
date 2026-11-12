<script setup>
const props = defineProps({
  cycles: { type: Array, required: true },
  selected: { type: String, default: null },
})
const emit = defineEmits(['select'])

const ETAPES = ['4a', '4b', '4c', '4d', '4e', '4f']
const NIVEAU_LABELS = { senior: 'Senior', manager: 'Manager', associe: 'Associé' }

function etat(cycle) {
  if (cycle.statut === 'non_commence') return 'non_commence'
  if (cycle.statut === 'cloture') return 'cloture'
  if (ETAPES.includes(cycle.statut)) return cycle.retourDe ? 'retour' : 'revision'
  return 'revue'
}

const styles = {
  non_commence: 'bg-gray-100 text-gray-500',
  revision: 'bg-[#eaf1f7] text-[#2c6e8f]',
  retour: 'bg-[#fbeee0] text-[#c9862c]',
  revue: 'bg-[#2c6e8f] text-white',
  cloture: 'bg-[#2f9e6b] text-white',
}

function tooltip(cycle) {
  const labels = {
    non_commence: 'Non commencé',
    revision: `En révision (${cycle.statut})`,
    retour: `Retour de revue ${NIVEAU_LABELS[cycle.retourDe] ?? ''}`,
    revue: `En revue ${NIVEAU_LABELS[cycle.niveauActif] ?? ''}`,
    cloture: 'Clôturé',
  }
  let text = `${cycle.code} · ${cycle.libelle} — ${labels[etat(cycle)]}`
  if (cycle.pointsOuverts) text += ` · ${cycle.pointsOuverts} point(s) ouvert(s)`
  if (cycle.alertes) text += ` · ${cycle.alertes} point(s) à traiter en séance de travail`
  return text
}

const legende = [
  ['revision', 'En révision'],
  ['retour', 'Retour de revue'],
  ['revue', 'En revue'],
  ['cloture', 'Clôturé'],
]
</script>

<template>
  <div class="rounded-xl bg-white px-4 py-3 shadow-sm">
    <div class="flex flex-wrap items-center gap-2">
      <span class="mr-1 text-xs font-bold uppercase tracking-wide text-gray-400">Cycle</span>
      <button
        v-for="cycle in props.cycles"
        :key="cycle.code"
        type="button"
        :title="tooltip(cycle)"
        class="relative flex h-8 w-8 items-center justify-center rounded-lg text-xs font-bold transition"
        :class="[styles[etat(cycle)], cycle.code === selected ? 'ring-2 ring-[#0d3b56] ring-offset-1' : 'hover:opacity-80']"
        @click="emit('select', cycle.code)"
      >
        {{ cycle.code }}
        <span
          v-if="cycle.alertes"
          class="absolute -right-1.5 -top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-[#c1483f] px-1 text-[10px] text-white"
          >!</span
        >
        <span
          v-else-if="cycle.pointsOuverts"
          class="absolute -right-1.5 -top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-[#c9862c] px-1 text-[10px] text-white"
          >{{ cycle.pointsOuverts }}</span
        >
      </button>
    </div>
    <div class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-gray-500">
      <span v-for="[key, label] in legende" :key="key" class="flex items-center gap-1.5">
        <span class="h-2.5 w-2.5 rounded-sm" :class="styles[key]"></span>{{ label }}
      </span>
      <span class="flex items-center gap-1.5">
        <span class="h-2.5 w-2.5 rounded-full bg-[#c1483f]"></span>À traiter en séance de travail
      </span>
    </div>
  </div>
</template>
