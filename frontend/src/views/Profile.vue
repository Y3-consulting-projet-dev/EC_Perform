<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import logo from '../assets/logo.y3.png'

const router = useRouter()
const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const employee = reactive(JSON.parse(localStorage.getItem('employee') ?? '{}'))

const initials = computed(() => {
  const first = (employee.prenoms ?? '').trim().charAt(0)
  const last = (employee.nom ?? '').trim().charAt(0)
  return `${first}${last}`.toUpperCase()
})

function authHeaders() {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${localStorage.getItem('access_token')}`,
  }
}

function logout() {
  localStorage.clear()
  router.push('/login')
}

const activeTab = ref('info')

const form = reactive({ prenoms: employee.prenoms ?? '', nom: employee.nom ?? '' })
const savingProfile = ref(false)
const profileError = ref('')
const profileSuccess = ref('')

function resetForm() {
  form.prenoms = employee.prenoms ?? ''
  form.nom = employee.nom ?? ''
  profileError.value = ''
  profileSuccess.value = ''
}

async function handleSaveProfile() {
  profileError.value = ''
  profileSuccess.value = ''
  savingProfile.value = true
  try {
    const response = await fetch(`${apiUrl}/users/me`, {
      method: 'PATCH',
      headers: authHeaders(),
      body: JSON.stringify({ nom: form.nom, prenoms: form.prenoms }),
    })
    const data = await response.json()
    if (!response.ok) {
      profileError.value = data.detail ?? 'Une erreur est survenue.'
      return
    }
    employee.nom = data.nom
    employee.prenoms = data.prenoms
    localStorage.setItem('employee', JSON.stringify(data))
    profileSuccess.value = 'Profil mis à jour avec succès.'
  } catch {
    profileError.value = 'Impossible de contacter le serveur.'
  } finally {
    savingProfile.value = false
  }
}

const currentPassword = ref('')
const newPassword = ref('')
const changePasswordError = ref('')
const changePasswordSuccess = ref('')
const changingPassword = ref(false)

async function handleChangePassword() {
  changePasswordError.value = ''
  changePasswordSuccess.value = ''
  changingPassword.value = true
  try {
    const response = await fetch(`${apiUrl}/auth/change-password`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        current_password: currentPassword.value,
        new_password: newPassword.value,
      }),
    })
    const data = await response.json()
    if (!response.ok) {
      changePasswordError.value = data.detail ?? 'Une erreur est survenue.'
      return
    }
    changePasswordSuccess.value = 'Mot de passe mis à jour avec succès.'
    localStorage.setItem('must_change_password', '')
    currentPassword.value = ''
    newPassword.value = ''
  } catch {
    changePasswordError.value = 'Impossible de contacter le serveur.'
  } finally {
    changingPassword.value = false
  }
}
</script>

<template>
  <div class="flex h-screen flex-col bg-[#eef2f6]">
    <header class="flex shrink-0 items-center justify-between border-b border-gray-200 bg-white px-8 py-4">
      <RouterLink to="/">
        <img :src="logo" alt="Y3 Audit & Conseils" class="h-16 w-auto" />
      </RouterLink>

      <div class="flex items-center gap-3">
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
      </div>
    </header>

    <main class="flex-1 overflow-y-auto px-10 py-8">
      <h1 class="mb-8 text-3xl font-extrabold text-[#0d3b56]">MON PROFIL</h1>

      <div class="flex items-start gap-8">
        <div class="w-72 shrink-0">
          <div class="flex items-start gap-3">
            <span
              class="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-[#0d3b56] text-lg font-semibold text-white"
            >
              {{ initials }}
            </span>
            <div>
              <p class="font-bold leading-tight text-[#0d3b56]">{{ employee.prenoms }} {{ employee.nom }}</p>
              <p class="mt-1 text-sm text-[#2f6fb0]">{{ employee.email }}</p>
            </div>
          </div>

          <span class="mt-3 inline-block rounded-full bg-[#e2f0e7] px-3 py-1 text-xs font-semibold text-[#4b7a5c]">
            {{ employee.grade }}
          </span>

          <div class="mt-6 space-y-2">
            <button
              type="button"
              class="flex w-full items-center justify-between rounded-lg px-4 py-3 text-left text-sm font-semibold transition"
              :class="activeTab === 'info' ? 'bg-[#7cb342] text-white' : 'bg-white text-[#0d3b56] hover:bg-gray-50'"
              @click="activeTab = 'info'"
            >
              Informations personnelles
              <span
                class="flex h-5 w-5 items-center justify-center rounded-full text-xs"
                :class="activeTab === 'info' ? 'bg-white/25 text-white' : 'bg-gray-100 text-gray-500'"
                >1</span
              >
            </button>
            <button
              type="button"
              class="flex w-full items-center justify-between rounded-lg px-4 py-3 text-left text-sm font-semibold transition"
              :class="activeTab === 'password' ? 'bg-[#7cb342] text-white' : 'bg-white text-[#0d3b56] hover:bg-gray-50'"
              @click="activeTab = 'password'"
            >
              Connexion & mot de passe
              <span
                class="flex h-5 w-5 items-center justify-center rounded-full text-xs"
                :class="activeTab === 'password' ? 'bg-white/25 text-white' : 'bg-gray-100 text-gray-500'"
                >2</span
              >
            </button>
          </div>

          <button
            type="button"
            class="mt-6 flex w-full items-center justify-between rounded-lg bg-[#0d3b56] px-4 py-3 text-left text-sm font-semibold text-white transition hover:bg-[#0a2f45]"
            @click="logout"
          >
            Déconnexion
            <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M16 17l5-5-5-5" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 12H9" />
            </svg>
          </button>
        </div>

        <div class="flex-1 rounded-xl bg-white p-8 shadow-sm">
          <template v-if="activeTab === 'info'">
            <h2 class="text-2xl font-bold text-[#0d3b56]">Informations personnelles</h2>
            <p class="mt-1 text-sm text-gray-500">Profil de votre compte sur l'outil d'évaluation.</p>

            <form class="mt-8 grid grid-cols-2 gap-6" @submit.prevent="handleSaveProfile">
              <div>
                <label for="prenoms" class="mb-1 block text-sm text-gray-700">Prénoms</label>
                <input
                  id="prenoms"
                  v-model="form.prenoms"
                  type="text"
                  required
                  class="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342]"
                />
              </div>
              <div>
                <label for="nom" class="mb-1 block text-sm text-gray-700">Nom</label>
                <input
                  id="nom"
                  v-model="form.nom"
                  type="text"
                  required
                  class="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342]"
                />
              </div>

              <div class="col-span-2">
                <label for="email" class="mb-1 block text-sm text-gray-700">Email</label>
                <div class="relative">
                  <input
                    id="email"
                    :value="employee.email"
                    type="email"
                    readonly
                    class="w-full cursor-not-allowed rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 pr-32 text-sm text-[#0d3b56]"
                  />
                  <span
                    class="absolute right-3 top-1/2 flex -translate-y-1/2 items-center gap-1 rounded-full bg-[#e2f0e7] px-3 py-1 text-xs font-semibold text-[#4b7a5c]"
                  >
                    <span class="h-1.5 w-1.5 rounded-full bg-[#4b7a5c]"></span>
                    Renseigné
                  </span>
                </div>
              </div>

              <div>
                <label for="grade" class="mb-1 block text-sm text-gray-700">Grade</label>
                <select
                  id="grade"
                  disabled
                  class="w-full cursor-not-allowed appearance-none rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-400"
                >
                  <option>{{ employee.grade }}</option>
                </select>
              </div>
              <div>
                <label for="departement" class="mb-1 block text-sm text-gray-700">Département</label>
                <select
                  id="departement"
                  disabled
                  class="w-full cursor-not-allowed appearance-none rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-400"
                >
                  <option>{{ employee.departement }}</option>
                </select>
              </div>

              <div class="col-span-2">
                <p v-if="profileError" class="mb-2 text-sm text-red-600">{{ profileError }}</p>
                <p v-if="profileSuccess" class="mb-2 text-sm text-green-600">{{ profileSuccess }}</p>
              </div>

              <div class="col-span-2 flex justify-end gap-3">
                <button
                  type="button"
                  class="rounded-full border border-gray-300 px-6 py-2.5 text-sm font-semibold text-gray-600 transition hover:bg-gray-50"
                  @click="resetForm"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  :disabled="savingProfile"
                  class="rounded-full bg-[#7cb342] px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-[#6ca038] disabled:opacity-60"
                >
                  {{ savingProfile ? 'Enregistrement...' : 'Enregistrer' }}
                </button>
              </div>
            </form>
          </template>

          <template v-else>
            <h2 class="text-2xl font-bold text-[#0d3b56]">Connexion & mot de passe</h2>
            <p class="mt-1 text-sm text-gray-500">Modifiez le mot de passe de votre compte.</p>

            <form class="mt-8 max-w-sm space-y-4" @submit.prevent="handleChangePassword">
              <div>
                <label for="current" class="mb-1 block text-sm text-gray-700">Mot de passe actuel</label>
                <input
                  id="current"
                  v-model="currentPassword"
                  type="password"
                  required
                  class="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342]"
                />
              </div>
              <div>
                <label for="new" class="mb-1 block text-sm text-gray-700">Nouveau mot de passe</label>
                <input
                  id="new"
                  v-model="newPassword"
                  type="password"
                  required
                  minlength="8"
                  class="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342]"
                />
              </div>

              <p v-if="changePasswordError" class="text-sm text-red-600">{{ changePasswordError }}</p>
              <p v-if="changePasswordSuccess" class="text-sm text-green-600">{{ changePasswordSuccess }}</p>

              <button
                type="submit"
                :disabled="changingPassword"
                class="rounded-full bg-[#7cb342] px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-[#6ca038] disabled:opacity-60"
              >
                {{ changingPassword ? 'Envoi...' : 'Valider' }}
              </button>
            </form>
          </template>
        </div>
      </div>
    </main>
  </div>
</template>
