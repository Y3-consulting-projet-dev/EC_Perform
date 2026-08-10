<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import logo from '../assets/logo.y3.png'
import ControleCoherence from './mission-steps/ControleCoherence.vue'
import ControleIntangibilite from './mission-steps/ControleIntangibilite.vue'
import DecoupageCycles from './mission-steps/DecoupageCycles.vue'
import EtapeGenerique from './mission-steps/EtapeGenerique.vue'
import GenerationLeads from './mission-steps/GenerationLeads.vue'
import OuvertureCollecte from './mission-steps/OuvertureCollecte.vue'
import RepartitionCycles from './mission-steps/RepartitionCycles.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  client: { type: Object, default: null },
  mission: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue'])

const employee = JSON.parse(localStorage.getItem('employee') ?? '{}')

const initials = computed(() => {
  const first = (employee.prenoms ?? '').trim().charAt(0)
  const last = (employee.nom ?? '').trim().charAt(0)
  return `${first}${last}`.toUpperCase()
})

const phaseGroups = [
  {
    title: 'Phase 1 – Ouverture',
    steps: [{ id: 'ouverture-collecte', label: 'Ouverture et collecte' }],
  },
  {
    title: 'Phase 2 – Contrôle',
    steps: [
      { id: 'controle-intangibilite', label: "Contrôle d'intangibilité" },
      { id: 'controle-coherence', label: 'Contrôle de cohérence' },
    ],
  },
  {
    title: 'Phase 3 – Organisation',
    steps: [
      { id: 'decoupage-cycles', label: 'Découpage en 12 cycles' },
      { id: 'repartition-cycles', label: 'Répartition des cycles' },
      { id: 'generation-leads', label: 'Génération des leads' },
    ],
  },
  {
    title: 'Phase 4 – Révision',
    steps: [
      { id: 'prise-connaissance', label: 'Prise de connaissance' },
      { id: 'lead-cycle', label: 'Lead du cycle' },
      { id: 'justification-solde', label: 'Justification du solde' },
      { id: 'controle-detaille', label: 'Contrôle détaillé' },
    ],
  },
]

const stepComponents = {
  'ouverture-collecte': OuvertureCollecte,
  'controle-intangibilite': ControleIntangibilite,
  'controle-coherence': ControleCoherence,
  'decoupage-cycles': DecoupageCycles,
  'repartition-cycles': RepartitionCycles,
  'generation-leads': GenerationLeads,
}

const activeStepId = ref(phaseGroups[0].steps[0].id)
const activeStepComponent = computed(() => stepComponents[activeStepId.value] ?? EtapeGenerique)

watch(
  () => props.modelValue,
  (open) => {
    if (open) activeStepId.value = phaseGroups[0].steps[0].id
  },
)

const router = useRouter()

function close() {
  emit('update:modelValue', false)
}

function goHome() {
  close()
  router.push('/')
}

function goProfile() {
  close()
  router.push('/profil')
}
</script>

<template>
  <div v-if="modelValue && client && mission" class="fixed inset-0 z-50 flex flex-col bg-[#eef2f6]">
    <header class="flex shrink-0 items-center justify-between border-b border-gray-200 bg-white px-8 py-4">
      <button type="button" @click="goHome">
        <img :src="logo" alt="Y3 Audit & Conseils" class="h-16 w-auto" />
      </button>

      <button type="button" class="flex items-center gap-3" @click="goProfile">
        <span
          class="flex h-10 w-10 items-center justify-center rounded-full bg-[#2f6fb0] text-sm font-semibold text-white"
        >
          {{ initials }}
        </span>
        <span class="text-left">
          <span class="block text-sm font-bold text-[#0d3b56]"
            >{{ employee.prenoms }} {{ employee.nom }}</span
          >
          <span class="block text-xs text-gray-400">{{ employee.grade }}</span>
        </span>
      </button>
    </header>

    <div class="flex min-h-0 flex-1">
      <aside class="flex w-64 shrink-0 flex-col gap-6 overflow-y-auto bg-[#0d3b56] px-4 py-6">
        <button
          type="button"
          class="flex w-fit items-center gap-2 rounded-lg bg-white/90 px-4 py-2 text-sm font-semibold text-[#0d3b56] transition hover:bg-white"
          @click="close"
        >
          <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
          Retour
        </button>

        <div
          v-for="group in phaseGroups"
          :key="group.title"
          class="space-y-2 rounded-xl border border-white/15 p-3"
        >
          <p class="px-1 text-sm font-bold text-white">{{ group.title }}</p>
          <button
            v-for="step in group.steps"
            :key="step.id"
            type="button"
            class="block w-full rounded-lg px-4 py-3 text-left text-sm font-semibold transition"
            :class="
              activeStepId === step.id
                ? 'bg-[#e2f0e7] text-[#0d3b56]'
                : 'bg-[#2f5875] text-white hover:bg-[#396a8a]'
            "
            @click="activeStepId = step.id"
          >
            {{ step.label }}
          </button>
        </div>
      </aside>

      <main class="scrollbar-hide flex-1 overflow-y-auto p-8">
        <p class="text-sm font-semibold text-gray-500">
          Mission {{ client.raisonSociale }} · Exercice {{ mission.exercice }}
        </p>

        <KeepAlive>
          <component :is="activeStepComponent" :key="activeStepId" />
        </KeepAlive>
      </main>
    </div>
  </div>
</template>

<style scoped>
.scrollbar-hide {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
</style>
