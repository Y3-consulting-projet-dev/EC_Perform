<script setup>
import { computed, onMounted, ref } from 'vue'

const props = defineProps({
  mission: { type: Object, required: true },
})

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function authHeaders() {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${localStorage.getItem('access_token')}`,
  }
}

// Seuls ces grades peuvent créer l'équipe et affecter les cycles (risque, collaborateur,
// délai) ; les autres grades (ex. Assistant) sont en lecture seule sur cette page. Doit
// rester cohérent avec CYCLE_MANAGEMENT_GRADES côté backend (repartition_service.py).
const CYCLE_MANAGEMENT_GRADES = ['senior', 'assistant manager', 'manager', 'senior manager', 'associé', 'associe']

const currentEmployee = JSON.parse(localStorage.getItem('employee') ?? '{}')
const canManage = computed(() => CYCLE_MANAGEMENT_GRADES.includes((currentEmployee.grade ?? '').trim().toLowerCase()))

const risqueOptions = ['Élevé', 'Moyen', 'Faible']
const risqueStyles = {
  Élevé: 'bg-red-100 text-red-600',
  Moyen: 'bg-amber-100 text-amber-700',
  Faible: 'bg-green-100 text-green-700',
}

const employees = ref([])
const cycles = ref([])
const loading = ref(true)
const error = ref('')
const savingCode = ref('')

function initials(employee) {
  const nom = (employee?.nom ?? '').trim()
  const prenoms = (employee?.prenoms ?? '').trim().split(/\s+/).filter(Boolean)
  return `${nom.charAt(0)}${prenoms[0]?.charAt(0) ?? ''}${prenoms[1]?.charAt(0) ?? ''}`.toUpperCase()
}

function employeeLabel(employee) {
  return `${initials(employee)} - ${employee.prenoms} ${employee.nom}`
}

function employeeById(id) {
  return employees.value.find((e) => e.id === id) ?? null
}

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('fr-FR')
}

async function fetchData() {
  loading.value = true
  error.value = ''
  try {
    const [employeesRes, cyclesRes, equipeRes] = await Promise.all([
      fetch(`${apiUrl}/employees`, { headers: authHeaders() }),
      fetch(`${apiUrl}/missions/${props.mission.id}/repartition`, { headers: authHeaders() }),
      fetch(`${apiUrl}/missions/${props.mission.id}/equipe`, { headers: authHeaders() }),
    ])
    const employeesData = await employeesRes.json()
    const cyclesData = await cyclesRes.json()
    const equipeData = await equipeRes.json()
    if (!employeesRes.ok) {
      error.value = employeesData.detail ?? 'Une erreur est survenue.'
      return
    }
    if (!cyclesRes.ok) {
      error.value = cyclesData.detail ?? 'Une erreur est survenue.'
      return
    }
    if (!equipeRes.ok) {
      error.value = equipeData.detail ?? 'Une erreur est survenue.'
      return
    }
    employees.value = employeesData
    cycles.value = cyclesData
    equipe.value = equipeData.equipe ?? []
  } catch {
    error.value = 'Impossible de contacter le serveur.'
  } finally {
    loading.value = false
  }
}

async function saveCycle(cycle) {
  if (!canManage.value) return
  savingCode.value = cycle.code
  error.value = ''
  try {
    const response = await fetch(`${apiUrl}/missions/${props.mission.id}/repartition/${cycle.code}`, {
      method: 'PATCH',
      headers: authHeaders(),
      body: JSON.stringify({ risque: cycle.risque, assigneA: cycle.assigneA, delai: cycle.delai }),
    })
    const data = await response.json()
    if (!response.ok) {
      error.value = data.detail ?? 'Une erreur est survenue.'
      return
    }
    Object.assign(cycle, data)
  } catch {
    error.value = 'Impossible de contacter le serveur.'
  } finally {
    savingCode.value = ''
  }
}

onMounted(fetchData)

const showTeamPanel = ref(false)
const equipeSelectionnee = ref([])
const equipe = ref([])

const equipeMembres = computed(() => employees.value.filter((e) => equipe.value.includes(e.id)))
const assignationOptions = computed(() => (equipe.value.length ? equipeMembres.value : employees.value))

function openTeamPanel() {
  if (!canManage.value) return
  equipeSelectionnee.value = [...equipe.value]
  showTeamPanel.value = !showTeamPanel.value
}

async function creerEquipe() {
  showTeamPanel.value = false
  if (!canManage.value) return
  error.value = ''
  try {
    const response = await fetch(`${apiUrl}/missions/${props.mission.id}/equipe`, {
      method: 'PUT',
      headers: authHeaders(),
      body: JSON.stringify({ employeeIds: equipeSelectionnee.value }),
    })
    const data = await response.json()
    if (!response.ok) {
      error.value = data.detail ?? 'Une erreur est survenue.'
      return
    }
    equipe.value = data.equipe
  } catch {
    error.value = 'Impossible de contacter le serveur.'
    return
  }
  if (!equipe.value.length) return
  for (const cycle of cycles.value) {
    if (!equipe.value.includes(cycle.assigneA)) {
      cycle.assigneA = equipe.value[0]
      await saveCycle(cycle)
    }
  }
}
</script>

<template>
  <div>
    <div class="mt-4 flex items-center justify-between">
      <h1 class="text-lg font-extrabold text-[#0d3b56]">Répartition des cycles</h1>

      <div class="flex items-center gap-4">
        <div v-if="equipeMembres.length" class="flex items-center -space-x-2">
          <span
            v-for="membre in equipeMembres"
            :key="membre.id"
            :title="`${membre.prenoms} ${membre.nom}`"
            class="flex h-8 w-8 items-center justify-center rounded-full border-2 border-white bg-[#2f6fb0] text-xs font-bold text-white"
          >
            {{ initials(membre) }}
          </span>
        </div>

        <div v-if="canManage" class="relative">
          <button
            type="button"
            class="flex items-center gap-2 rounded-lg bg-[#0d3b56] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#0a2f45]"
            @click="openTeamPanel"
          >
            Créer mon équipe
            <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="m6 9 6 6 6-6" />
            </svg>
          </button>

          <div v-if="showTeamPanel" class="fixed inset-0 z-10" @click="showTeamPanel = false"></div>

          <div
            v-if="showTeamPanel"
            class="absolute right-0 z-20 mt-2 w-96 rounded-xl border border-gray-200 bg-white p-4 shadow-lg"
            @click.stop
          >
            <p class="text-xs text-gray-500">Sélectionnez les collaborateurs à affecter à cette mission.</p>

            <div class="mt-3 max-h-64 space-y-1 overflow-y-auto">
              <label
                v-for="employee in employees"
                :key="employee.id"
                class="flex items-center gap-3 rounded-lg px-2 py-2 hover:bg-gray-50"
              >
                <input
                  type="checkbox"
                  :value="employee.id"
                  v-model="equipeSelectionnee"
                  class="h-4 w-4 rounded border-gray-300 text-[#7cb342] focus:ring-[#7cb342]"
                />
                <span
                  class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#0d3b56] text-xs font-bold text-white"
                >
                  {{ initials(employee) }}
                </span>
                <span class="flex-1">
                  <span class="block text-sm font-bold text-[#0d3b56]">{{ employee.prenoms }} {{ employee.nom }}</span>
                  <span v-if="employee.grade" class="block text-xs text-gray-400">{{ employee.grade }}</span>
                </span>
              </label>
            </div>

            <div class="mt-4 flex justify-end">
              <button
                type="button"
                class="rounded-lg bg-[#0d3b56] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#0a2f45]"
                @click="creerEquipe"
              >
                Créer l'équipe
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <p v-if="loading" class="mt-6 text-sm text-gray-400">Chargement...</p>
    <p v-else-if="error" class="mt-4 text-sm text-red-600">{{ error }}</p>

    <div v-else class="mt-6 overflow-x-auto rounded-lg shadow-sm">
      <table class="w-full text-left text-sm">
        <thead>
          <tr class="bg-[#7cb342] text-sm font-bold text-white">
            <th class="px-4 py-3">Cycle</th>
            <th class="px-4 py-3 text-center">Risque</th>
            <th class="px-4 py-3 text-center">Assigné à</th>
            <th class="px-4 py-3 text-right">Délai</th>
          </tr>
        </thead>
        <tbody class="bg-white">
          <tr v-for="cycle in cycles" :key="cycle.code" class="border-t border-gray-100">
            <td class="px-4 py-3">
              <div class="flex items-center gap-2">
                <span
                  class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[#0d3b56] text-xs font-bold text-white"
                >
                  {{ cycle.code }}
                </span>
                <span class="font-medium text-[#0d3b56]">{{ cycle.libelle }}</span>
              </div>
            </td>
            <td class="px-4 py-3">
              <div class="flex justify-center">
                <select
                  v-if="canManage"
                  v-model="cycle.risque"
                  :disabled="savingCode === cycle.code"
                  class="appearance-none rounded-full px-4 py-1.5 text-xs font-semibold outline-none disabled:opacity-60"
                  :class="risqueStyles[cycle.risque]"
                  @change="saveCycle(cycle)"
                >
                  <option v-for="option in risqueOptions" :key="option" :value="option">{{ option }}</option>
                </select>
                <span
                  v-else
                  class="rounded-full px-4 py-1.5 text-xs font-semibold"
                  :class="risqueStyles[cycle.risque]"
                >
                  {{ cycle.risque }}
                </span>
              </div>
            </td>
            <td class="px-4 py-3">
              <div class="flex items-center justify-center gap-2">
                <span
                  v-if="employeeById(cycle.assigneA)"
                  class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#2f6fb0] text-xs font-bold text-white"
                  :title="`${employeeById(cycle.assigneA).prenoms} ${employeeById(cycle.assigneA).nom}`"
                >
                  {{ initials(employeeById(cycle.assigneA)) }}
                </span>
                <select
                  v-if="canManage"
                  v-model="cycle.assigneA"
                  :disabled="savingCode === cycle.code"
                  class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342] disabled:opacity-60"
                  @change="saveCycle(cycle)"
                >
                  <option :value="null">-</option>
                  <option v-for="option in assignationOptions" :key="option.id" :value="option.id">
                    {{ employeeLabel(option) }}
                  </option>
                </select>
                <span v-else class="text-sm text-[#0d3b56]">
                  {{ employeeById(cycle.assigneA) ? `${employeeById(cycle.assigneA).prenoms} ${employeeById(cycle.assigneA).nom}` : '—' }}
                </span>
              </div>
            </td>
            <td class="px-4 py-3 text-right">
              <input
                v-if="canManage"
                type="date"
                v-model="cycle.delai"
                :disabled="savingCode === cycle.code"
                class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342] disabled:opacity-60"
                @change="saveCycle(cycle)"
              />
              <span v-else class="text-gray-500">{{ formatDate(cycle.delai) }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
