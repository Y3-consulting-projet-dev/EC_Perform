<script setup>
import { formatDateTime } from '../../composables/useCycleRevision'

defineProps({
  chaine: { type: Array, required: true },
})

const circleStyles = {
  fait: 'bg-[#2f9e6b] text-white',
  en_cours: 'bg-[#2c6e8f] text-white',
  retour: 'bg-[#c9862c] text-white',
  en_attente: 'bg-[#eef1f4] text-gray-500',
}
const statusStyles = {
  fait: 'text-[#2f9e6b]',
  en_cours: 'text-[#2c6e8f]',
  retour: 'text-[#c9862c]',
  en_attente: 'text-gray-400',
}

function statusText(step) {
  const date = step.le ? formatDateTime(step.le) : ''
  if (step.etat === 'fait') {
    const verbe = step.niveau === 'collaborateur' ? 'Soumis' : 'Validé'
    return [`${verbe}${date ? ` le ${date}` : ''}`, step.par].filter(Boolean).join(' — ')
  }
  if (step.etat === 'en_cours') return ['En cours', step.par].filter(Boolean).join(' — ')
  if (step.etat === 'retour') {
    return step.niveau === 'collaborateur' ? ['Retour pour modification', step.par].filter(Boolean).join(' — ') : 'A renvoyé le cycle'
  }
  return step.par ? `En attente — ${step.par}` : 'En attente'
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-y-3 rounded-xl bg-white px-5 py-4 shadow-sm">
    <template v-for="(step, index) in chaine" :key="step.niveau">
      <div v-if="index > 0" class="mx-2 hidden h-0.5 w-10 shrink-0 sm:block" :class="chaine[index - 1].etat === 'fait' ? 'bg-[#2f9e6b]' : 'bg-gray-200'"></div>
      <div class="flex min-w-0 flex-1 items-center gap-2.5">
        <span
          class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold"
          :class="circleStyles[step.etat]"
        >
          <template v-if="step.etat === 'fait'">✓</template>
          <template v-else-if="step.etat === 'retour'">↩</template>
          <template v-else>{{ index + 1 }}</template>
        </span>
        <span class="min-w-0">
          <span class="block text-[13px] font-bold text-[#0d3b56]">{{ step.label }}</span>
          <span class="block truncate text-[11px]" :class="statusStyles[step.etat]">{{ statusText(step) }}</span>
          <span v-if="step.modifieApresValidation" class="block text-[11px] font-semibold text-[#c9862c]">
            Travaux modifiés après validation
          </span>
        </span>
      </div>
    </template>
  </div>
</template>
