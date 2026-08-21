<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  client: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'created'])

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function authHeaders() {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${localStorage.getItem('access_token')}`,
  }
}

const employees = ref([])

async function fetchEmployees() {
  try {
    const response = await fetch(`${apiUrl}/employees`, { headers: authHeaders() })
    if (!response.ok) return
    employees.value = await response.json()
  } catch {
    // selects simply stay empty if the request fails
  }
}

onMounted(fetchEmployees)

function fullName(e) {
  return `${e.prenoms} ${e.nom}`.trim()
}

const MANAGER_GRADES = ['manager']
const SENIOR_GRADES = ['senior']

const EXPERTISE_COMPTABLE_DEPARTEMENTS = ['expertise comptable', 'audit & expertise comptable']

function isExpertiseComptable(e) {
  return EXPERTISE_COMPTABLE_DEPARTEMENTS.includes((e.departement ?? '').trim().toLowerCase())
}

const managers = computed(() =>
  employees.value
    .filter((e) => isExpertiseComptable(e) && MANAGER_GRADES.includes((e.grade ?? '').trim().toLowerCase()))
    .map(fullName),
)

const seniors = computed(() =>
  employees.value
    .filter((e) => isExpertiseComptable(e) && SENIOR_GRADES.includes((e.grade ?? '').trim().toLowerCase()))
    .map(fullName),
)

function emptyForm() {
  return {
    dateDebut: '',
    echeance: '',
    manager: '',
    senior: '',
  }
}

const form = reactive(emptyForm())
const saving = ref(false)
const error = ref('')

const currentYear = new Date().getFullYear()

const balanceNFile = ref(null)
const balanceNMoins1File = ref(null)

function handleBalanceNChange(event) {
  balanceNFile.value = event.target.files[0] ?? null
}

function handleBalanceNMoins1Change(event) {
  balanceNMoins1File.value = event.target.files[0] ?? null
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      Object.assign(form, emptyForm())
      balanceNFile.value = null
      balanceNMoins1File.value = null
      error.value = ''
    }
  },
)

function close() {
  error.value = ''
  emit('update:modelValue', false)
}

async function uploadBalanceDocument(missionId, file, description) {
  const formData = new FormData()
  formData.append('categorie', 'BALANCES')
  formData.append('description', description)
  formData.append('version', 'Electronique')
  formData.append('dateDemande', '')
  formData.append('statut', 'Reçu')
  formData.append('fichier', file)

  const response = await fetch(`${apiUrl}/missions/${missionId}/documents`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
    body: formData,
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail ?? 'Une erreur est survenue.')
  }
}

async function handleSubmit() {
  error.value = ''
  saving.value = true
  try {
    const response = await fetch(`${apiUrl}/missions`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        clientId: props.client?.id,
        exercice: String(currentYear),
        dateDebut: form.dateDebut,
        echeance: form.echeance,
        manager: form.manager,
        senior: form.senior,
      }),
    })
    const data = await response.json()
    if (!response.ok) {
      error.value = data.detail ?? 'Une erreur est survenue.'
      return
    }

    if (balanceNFile.value || balanceNMoins1File.value) {
      try {
        if (balanceNFile.value) {
          await uploadBalanceDocument(data.id, balanceNFile.value, `Balance N ${currentYear}`)
        }
        if (balanceNMoins1File.value) {
          await uploadBalanceDocument(data.id, balanceNMoins1File.value, `Balance N-1 ${currentYear - 1}`)
        }
      } catch (uploadError) {
        error.value = `Mission créée, mais l'import d'une balance a échoué : ${uploadError.message}`
        emit('created', data)
        return
      }
    }

    emit('created', data)
    close()
  } catch {
    error.value = 'Impossible de contacter le serveur.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div
    v-if="modelValue"
    class="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-6"
    @click.self="close"
  >
    <div class="flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl bg-white shadow-xl">
      <div class="scrollbar-hide overflow-y-auto p-8">
        <h2 class="text-lg font-bold text-[#7cb342]">Nouvelle mission</h2>
        <button
          type="button"
          class="mt-4 rounded-full border border-[#7cb342] px-5 py-1.5 text-sm font-semibold text-[#0d3b56] transition hover:bg-gray-50"
          @click="close"
        >
          Retour
        </button>

        <form class="mt-8 grid grid-cols-1 gap-x-10 gap-y-6 sm:grid-cols-2" @submit.prevent="handleSubmit">
          <div>
            <label for="mission-client" class="mb-1 block text-sm font-bold text-[#0d3b56]">Client</label>
            <input
              id="mission-client"
              :value="client?.raisonSociale"
              type="text"
              readonly
              class="w-full cursor-not-allowed rounded-xl border border-gray-200 bg-gray-100 px-4 py-2.5 text-sm text-[#0d3b56]"
            />
          </div>
          <div>
            <label for="mission-exercice" class="mb-1 block text-sm font-bold text-[#0d3b56]">Exercice</label>
            <input
              id="mission-exercice"
              :value="currentYear"
              type="text"
              readonly
              class="w-full cursor-not-allowed rounded-xl border border-gray-200 bg-gray-100 px-4 py-2.5 text-sm text-[#0d3b56]"
            />
          </div>

          <div>
            <label for="mission-manager" class="mb-1 block text-sm font-bold text-[#0d3b56]">Manager</label>
            <select
              id="mission-manager"
              v-model="form.manager"
              class="w-full rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342]"
            >
              <option value="" disabled>Choisir</option>
              <option v-for="name in managers" :key="name" :value="name">{{ name }}</option>
            </select>
          </div>
          <div>
            <label for="mission-date-debut" class="mb-1 block text-sm font-bold text-[#0d3b56]">Date de début</label>
            <input
              id="mission-date-debut"
              v-model="form.dateDebut"
              type="date"
              class="w-full rounded-xl border border-[#7cb342] bg-[#eef1ec] px-4 py-2.5 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342]"
            />
          </div>

          <div>
            <label for="mission-senior" class="mb-1 block text-sm font-bold text-[#0d3b56]">Senior</label>
            <select
              id="mission-senior"
              v-model="form.senior"
              class="w-full rounded-xl border border-[#7cb342] bg-white px-4 py-2.5 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342]"
            >
              <option value="" disabled>Choisir</option>
              <option v-for="name in seniors" :key="name" :value="name">{{ name }}</option>
            </select>
          </div>
          <div>
            <label for="mission-echeance" class="mb-1 block text-sm font-bold text-[#0d3b56]">Échéance</label>
            <input
              id="mission-echeance"
              v-model="form.echeance"
              type="date"
              class="w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342]"
            />
          </div>

          <div class="col-span-2">
            <h3 class="mb-3 text-sm font-bold text-[#0d3b56]">Balances (facultatif)</h3>
            <div class="grid grid-cols-1 gap-x-10 gap-y-6 sm:grid-cols-2">
              <div>
                <label for="mission-balance-n" class="mb-1 block text-sm font-bold text-[#0d3b56]">Balance N</label>
                <input
                  id="mission-balance-n"
                  type="file"
                  accept=".xlsx,.xls"
                  class="w-full rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm text-[#0d3b56] outline-none file:mr-3 file:rounded-full file:border-0 file:bg-[#7cb342] file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-white"
                  @change="handleBalanceNChange"
                />
                <p v-if="balanceNFile" class="mt-1 text-xs text-gray-500">{{ balanceNFile.name }}</p>
              </div>
              <div>
                <label for="mission-balance-n-1" class="mb-1 block text-sm font-bold text-[#0d3b56]"
                  >Balance N-1</label
                >
                <input
                  id="mission-balance-n-1"
                  type="file"
                  accept=".xlsx,.xls"
                  class="w-full rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm text-[#0d3b56] outline-none file:mr-3 file:rounded-full file:border-0 file:bg-[#7cb342] file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-white"
                  @change="handleBalanceNMoins1Change"
                />
                <p v-if="balanceNMoins1File" class="mt-1 text-xs text-gray-500">{{ balanceNMoins1File.name }}</p>
              </div>
            </div>
          </div>

          <p v-if="error" class="col-span-2 text-sm text-red-600">{{ error }}</p>

          <div class="col-span-2 flex justify-end pt-2">
            <button
              type="submit"
              :disabled="saving"
              class="rounded-xl bg-[#0d3b56] px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-[#0a2f45] disabled:opacity-60"
            >
              {{ saving ? 'Enregistrement...' : 'Créer la mission' }}
            </button>
          </div>
        </form>
      </div>
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
