<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const showPassword = ref(false)

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function handleSubmit() {
  error.value = ''
  loading.value = true
  try {
    const response = await fetch(`${apiUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.value, password: password.value }),
    })
    const data = await response.json()
    if (!response.ok) {
      error.value = data.detail ?? 'Une erreur est survenue.'
      return
    }
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('employee', JSON.stringify(data.employee))
    localStorage.setItem('must_change_password', data.must_change_password ? '1' : '')
    router.push('/')
  } catch {
    error.value = 'Impossible de contacter le serveur.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-screen flex-col md:flex-row">
    <div class="relative flex w-full flex-col items-center overflow-hidden bg-[#0d3b56] px-8 pt-16 pb-12 md:w-1/2">
      <h1 class="relative z-10 text-center text-lg font-medium text-white">
        Bienvenue sur l'outil EC PERFORM
      </h1>

      <div class="relative z-10 mt-16 w-full max-w-xs">
        <svg viewBox="0 0 200 200" class="w-full drop-shadow-xl">
          <rect x="10" y="10" width="180" height="180" rx="20" fill="#5ec9c2" />
          <rect x="35" y="95" width="16" height="60" rx="3" fill="#ef5350" />
          <rect x="58" y="75" width="16" height="80" rx="3" fill="#ffca28" />
          <rect x="81" y="55" width="16" height="100" rx="3" fill="#42a5f5" />
          <rect x="30" y="150" width="75" height="6" rx="3" fill="#ffffff" opacity="0.7" />
          <circle cx="145" cy="70" r="26" fill="none" stroke="#0d3b56" stroke-width="6" />
          <line x1="163" y1="88" x2="178" y2="103" stroke="#0d3b56" stroke-width="7" stroke-linecap="round" />
          <rect x="118" y="112" width="55" height="45" rx="6" fill="#ffffff" />
          <rect x="126" y="122" width="12" height="10" rx="2" fill="#0d3b56" />
          <rect x="142" y="122" width="12" height="10" rx="2" fill="#0d3b56" />
          <rect x="158" y="122" width="7" height="10" rx="2" fill="#ef5350" />
          <rect x="126" y="136" width="12" height="10" rx="2" fill="#0d3b56" opacity="0.6" />
          <rect x="142" y="136" width="12" height="10" rx="2" fill="#0d3b56" opacity="0.6" />
          <rect x="158" y="136" width="7" height="10" rx="2" fill="#0d3b56" opacity="0.6" />
        </svg>
      </div>
    </div>

    <div class="flex w-full flex-col items-center justify-center bg-[#efece7] px-8 py-16 md:w-1/2">
      <div class="w-full max-w-sm">
        <h2 class="mb-10 text-center text-2xl font-bold tracking-wide text-[#7cb342]">CONNEXION</h2>

        <form class="space-y-6" @submit.prevent="handleSubmit">
          <div>
            <label for="email" class="mb-1 block text-xs font-bold tracking-wide text-[#0d3b56]"
              >EMAIL</label
            >
            <input
              id="email"
              v-model="email"
              type="email"
              autocomplete="username"
              required
              placeholder="EMAIL"
              class="w-full rounded-xl border border-[#7cb342] bg-[#e7e3dd] px-4 py-2.5 text-sm text-[#0d3b56] placeholder-gray-400 outline-none focus:ring-2 focus:ring-[#7cb342]"
            />
          </div>

          <div>
            <label for="password" class="mb-1 block text-xs font-bold tracking-wide text-[#0d3b56]"
              >MOT DE PASSE</label
            >
            <div class="relative">
              <input
                id="password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                required
                placeholder="MOT DE PASSE"
                class="w-full rounded-xl border border-[#7cb342] bg-[#e7e3dd] px-4 py-2.5 pr-11 text-sm text-[#0d3b56] placeholder-gray-400 outline-none focus:ring-2 focus:ring-[#7cb342]"
              />
              <button
                type="button"
                tabindex="-1"
                class="absolute inset-y-0 right-0 flex items-center px-3 text-[#0d3b56]"
                :aria-label="showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'"
                @click="showPassword = !showPassword"
              >
                <svg v-if="showPassword" viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3 12s3.6-7 9-7 9 7 9 7-3.6 7-9 7-9-7-9-7Z" />
                  <circle cx="12" cy="12" r="3" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
                <svg v-else viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3 3l18 18" />
                  <path stroke-linecap="round" stroke-linejoin="round" d="M10.58 10.58a2 2 0 0 0 2.83 2.83" />
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9.36 5.36A9.77 9.77 0 0 1 12 5c5.4 0 9 7 9 7a13.16 13.16 0 0 1-2.02 2.9M6.6 6.6C4.13 8.2 3 10.99 3 12s3.6 7 9 7a9.77 9.77 0 0 0 3.36-.6" />
                </svg>
              </button>
            </div>
          </div>

          <div class="flex justify-end">
            <a href="#" class="text-xs font-medium text-[#0d3b56] hover:underline"
              >Mot de passe oublié ?</a
            >
          </div>

          <p v-if="error" class="text-center text-sm text-red-600">{{ error }}</p>

          <div class="flex justify-center pt-2">
            <button
              type="submit"
              :disabled="loading"
              class="rounded-full bg-[#7cb342] px-10 py-2.5 text-sm font-semibold text-white transition hover:bg-[#6ca038] disabled:opacity-60"
            >
              {{ loading ? 'Connexion...' : 'Se Connecter' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
