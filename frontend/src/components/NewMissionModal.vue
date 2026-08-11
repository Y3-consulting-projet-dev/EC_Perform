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

const managers = computed(() =>
  employees.value
    .filter((e) => ['manager', 'senior manager'].includes((e.grade ?? '').trim().toLowerCase()))
    .map(fullName),
)

const seniors = computed(() =>
  employees.value.filter((e) => (e.grade ?? '').trim().toLowerCase() === 'senior').map(fullName),
)

function emptyForm() {
  return {
    objet: '',
    dateDebut: '',
    echeance: '',
    manager: '',
    senior: '',
    dureeEstimee: '',
  }
}

const form = reactive(emptyForm())

const currentYear = new Date().getFullYear()

watch(
  () => props.modelValue,
  (open) => {
    if (open) Object.assign(form, emptyForm())
  },
)

function close() {
  emit('update:modelValue', false)
}

function handleSubmit() {
  emit('created', {
    exercice: String(currentYear),
    phase: '1/7 · Ouverture et collecte',
    statut: 'En cours',
    rapport: null,
    objet: form.objet,
    dateDebut: form.dateDebut,
    echeance: form.echeance,
    manager: form.manager,
    senior: form.senior,
    dureeEstimee: form.dureeEstimee,
  })
  close()
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

        <form class="mt-8 grid grid-cols-2 gap-x-10 gap-y-6" @submit.prevent="handleSubmit">
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
            <label for="mission-objet" class="mb-1 block text-sm font-bold text-[#0d3b56]">Collaborateur</label>
            <input
              id="mission-objet"
              v-model="form.objet"
              type="text"
              placeholder="Conformité BCRG, ..."
              class="w-full rounded-xl border border-[#7cb342] bg-[#eef1ec] px-4 py-2.5 text-sm text-[#0d3b56] placeholder-gray-400 outline-none focus:ring-2 focus:ring-[#7cb342]"
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
          <div>
            <label for="mission-duree" class="mb-1 block text-sm font-bold text-[#0d3b56]"
              >Durée estimée de la mission</label
            >
            <input
              id="mission-duree"
              v-model="form.dureeEstimee"
              type="text"
              placeholder="6 semaines"
              class="w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm text-[#0d3b56] placeholder-gray-400 outline-none focus:ring-2 focus:ring-[#7cb342]"
            />
          </div>

          <div class="col-span-2 flex justify-end pt-2">
            <button
              type="submit"
              class="rounded-xl bg-[#0d3b56] px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-[#0a2f45]"
            >
              Créer la mission
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
