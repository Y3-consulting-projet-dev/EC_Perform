<script setup>
import { onMounted, ref } from 'vue'

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
  return `${initials(employee)} — ${employee.prenoms} ${employee.nom}`
}

function employeeById(id) {
  return employees.value.find((e) => e.id === id) ?? null
}

async function fetchData() {
  loading.value = true
  error.value = ''
  try {
    const [employeesRes, cyclesRes] = await Promise.all([
      fetch(`${apiUrl}/employees`, { headers: authHeaders() }),
      fetch(`${apiUrl}/missions/${props.mission.id}/repartition`, { headers: authHeaders() }),
    ])
    const employeesData = await employeesRes.json()
    const cyclesData = await cyclesRes.json()
    if (!employeesRes.ok) {
      error.value = employeesData.detail ?? 'Une erreur est survenue.'
      return
    }
    if (!cyclesRes.ok) {
      error.value = cyclesData.detail ?? 'Une erreur est survenue.'
      return
    }
    employees.value = employeesData
    cycles.value = cyclesData
  } catch {
    error.value = 'Impossible de contacter le serveur.'
  } finally {
    loading.value = false
  }
}

async function saveCycle(cycle) {
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
</script>

<template>
  <div>
    <h1 class="mt-4 text-lg font-extrabold text-[#0d3b56]">Répartition des cycles</h1>

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
                  v-model="cycle.risque"
                  :disabled="savingCode === cycle.code"
                  class="appearance-none rounded-full px-4 py-1.5 text-xs font-semibold outline-none disabled:opacity-60"
                  :class="risqueStyles[cycle.risque]"
                  @change="saveCycle(cycle)"
                >
                  <option v-for="option in risqueOptions" :key="option" :value="option">{{ option }}</option>
                </select>
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
                  v-model="cycle.assigneA"
                  :disabled="savingCode === cycle.code"
                  class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342] disabled:opacity-60"
                  @change="saveCycle(cycle)"
                >
                  <option :value="null">—</option>
                  <option v-for="option in employees" :key="option.id" :value="option.id">
                    {{ employeeLabel(option) }}
                  </option>
                </select>
              </div>
            </td>
            <td class="px-4 py-3 text-right">
              <input
                type="date"
                v-model="cycle.delai"
                :disabled="savingCode === cycle.code"
                class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342] disabled:opacity-60"
                @change="saveCycle(cycle)"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
