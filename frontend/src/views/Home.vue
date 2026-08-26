<script setup>
import { computed, onMounted, ref } from 'vue'
import { API_URL as apiUrl } from '../utils/apiUrl'


function authHeaders() {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${localStorage.getItem('access_token')}`,
  }
}

const clientStats = ref({ total: null, newLastThreeMonths: null })
const missionStats = ref({
  enCours: null,
  deltaVsLastMonth: null,
  terminees: null,
  annee: new Date().getFullYear(),
  pourcentageDansLesDelais: null,
})
const missionPhases = ref([])

async function fetchClientStats() {
  try {
    const response = await fetch(`${apiUrl}/clients/stats`, { headers: authHeaders() })
    if (!response.ok) return
    clientStats.value = await response.json()
  } catch {
    // stat card falls back to a placeholder below
  }
}

async function fetchMissionStats() {
  try {
    const response = await fetch(`${apiUrl}/missions/stats`, { headers: authHeaders() })
    if (!response.ok) return
    missionStats.value = await response.json()
  } catch {
    // stat card falls back to a placeholder below
  }
}

async function fetchMissionPhases() {
  try {
    const response = await fetch(`${apiUrl}/missions/phases`, { headers: authHeaders() })
    if (!response.ok) return
    missionPhases.value = await response.json()
  } catch {
    // section falls back to an empty grid below
  }
}

onMounted(() => {
  fetchClientStats()
  fetchMissionStats()
  fetchMissionPhases()
})

function missionsDelta() {
  const delta = missionStats.value.deltaVsLastMonth
  if (delta === null) return ''
  if (delta < 0) return `▼ ${delta} vs le mois dernier`
  return `▲ +${delta} vs le mois dernier`
}

const stats = computed(() => [
  {
    value: clientStats.value.total === null ? '-' : String(clientStats.value.total),
    label: 'Clients enregistrés',
    delta:
      clientStats.value.newLastThreeMonths === null
        ? ''
        : `▲ +${clientStats.value.newLastThreeMonths} ce trimestre`,
  },
  {
    value: missionStats.value.enCours === null ? '-' : String(missionStats.value.enCours),
    label: 'Missions en cours',
    delta: missionsDelta(),
  },
  {
    value: missionStats.value.terminees === null ? '-' : String(missionStats.value.terminees),
    label: `Missions terminées (${missionStats.value.annee})`,
    delta:
      missionStats.value.pourcentageDansLesDelais === null
        ? ''
        : `▲ ${missionStats.value.pourcentageDansLesDelais}% dans les délais`,
  },
])

const totalMissions = computed(() => missionPhases.value.reduce((sum, p) => sum + p.value, 0))

const riskStyles = {
  Élevé: { dot: 'bg-red-500', text: 'text-red-600' },
  Moyen: { dot: 'bg-amber-500', text: 'text-amber-600' },
  Faible: { dot: 'bg-green-500', text: 'text-green-600' },
}

const missionsAtRisk = [
  { mission: 'SAVEDO SA', phase: '4.Révision cycle C', risque: 'Élevé', avancement: 65, echeance: '28Juil' },
  { mission: 'Groupe Nanan', phase: '5.Revue', risque: 'Moyen', avancement: 55, echeance: '25Juil' },
  { mission: 'Ets Koffi & Fils', phase: '2.Contrôles', risque: 'Moyen', avancement: 30, echeance: '02Août' },
  { mission: 'SA Distribution', phase: '4.Révision cycle B', risque: 'Faible', avancement: 75, echeance: '05Août' },
]

const tagStyles = {
  Urgent: 'bg-red-50 text-red-600',
  'A valider': 'bg-amber-50 text-amber-700',
  'A obtenir': 'bg-slate-100 text-slate-600',
  'A planifier': 'bg-sky-50 text-sky-700',
}

const todos = [
  { tag: 'Urgent', title: '5 Clients à relancer pour documents', subtitle: 'Phase1.échéance dépassée' },
  { tag: 'Urgent', title: '2 Contrôles bloqués à traiter', subtitle: 'Phase2.SA Distribution Ets Koffi' },
  { tag: 'A valider', title: '3 Dossiers attendent ma validation', subtitle: 'Phase5.revue niveau associé' },
  { tag: 'A obtenir', title: "1 lettre d'affirmation à obtenir", subtitle: 'Phase5.SAVEDO SA' },
  { tag: 'A planifier', title: '2 circularisations en attente de réponse >15 j', subtitle: 'Phase6.revue client' },
]
</script>

<template>
  <div class="space-y-6">
    <div class="grid grid-cols-1 gap-6 sm:grid-cols-3">
      <div v-for="stat in stats" :key="stat.label" class="rounded-lg bg-[#0d3b56] p-6 text-white">
        <p class="text-3xl font-extrabold">{{ stat.value }}</p>
        <p class="mt-1 text-sm text-gray-200">{{ stat.label }}</p>
        <p
          class="mt-3 text-xs font-medium"
          :class="stat.delta.startsWith('▼') ? 'text-red-400' : 'text-green-400'"
        >
          {{ stat.delta }}
        </p>
      </div>
    </div>

    <div class="rounded-lg bg-white p-6 shadow-sm">
      <h2 class="mb-4 text-sm font-bold text-[#0d3b56]">Où en sont les {{ totalMissions }} missions ?</h2>
      <div class="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-7">
        <div
          v-for="phase in missionPhases"
          :key="phase.label"
          class="rounded-lg bg-[#e2f0e7] px-3 py-4 text-center"
        >
          <p class="text-2xl font-extrabold text-[#0d3b56]">{{ phase.value }}</p>
          <p class="mt-1 text-[11px] leading-tight text-gray-500">{{ phase.label }}</p>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div class="rounded-lg bg-white p-6 shadow-sm lg:col-span-2">
        <h2 class="mb-4 text-sm font-bold text-[#0d3b56]">Missions à surveiller</h2>
        <div class="overflow-x-auto">
          <table class="w-full min-w-[560px] text-left text-sm">
            <thead>
              <tr class="text-xs text-gray-400">
                <th class="pb-2 font-semibold">MISSION</th>
                <th class="pb-2 font-semibold">PHASE</th>
                <th class="pb-2 font-semibold">RISQUE</th>
                <th class="pb-2 font-semibold">AVANCEMENT</th>
                <th class="pb-2 font-semibold">ECHEANCE</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in missionsAtRisk" :key="row.mission" class="border-t border-gray-100">
                <td class="py-3 font-medium text-[#0d3b56]">{{ row.mission }}</td>
                <td class="py-3 text-gray-500">{{ row.phase }}</td>
                <td class="py-3">
                  <span class="inline-flex items-center gap-1.5" :class="riskStyles[row.risque].text">
                    <span class="h-2 w-2 rounded-full" :class="riskStyles[row.risque].dot"></span>
                    {{ row.risque }}
                  </span>
                </td>
                <td class="py-3">
                  <div class="h-2 w-28 overflow-hidden rounded-full bg-gray-100">
                    <div class="h-full rounded-full bg-[#2f6fb0]" :style="{ width: row.avancement + '%' }"></div>
                  </div>
                </td>
                <td class="py-3 text-gray-500">{{ row.echeance }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="rounded-lg bg-white p-6 shadow-sm">
        <h2 class="mb-4 text-sm font-bold text-[#0d3b56]">A faire</h2>
        <ul class="space-y-4">
          <li v-for="todo in todos" :key="todo.title" class="flex items-start gap-3">
            <span
              class="mt-0.5 shrink-0 rounded px-2 py-0.5 text-[11px] font-semibold"
              :class="tagStyles[todo.tag]"
              >{{ todo.tag }}</span
            >
            <span>
              <span class="block text-sm font-medium text-[#0d3b56]">{{ todo.title }}</span>
              <span class="block text-xs text-gray-400">{{ todo.subtitle }}</span>
            </span>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>
