<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import logo from '../assets/logo2.y3.png'

const router = useRouter()
const route = useRoute()

const employee = JSON.parse(localStorage.getItem('employee') ?? '{}')

const initials = computed(() => {
  const first = (employee.prenoms ?? '').trim().charAt(0)
  const last = (employee.nom ?? '').trim().charAt(0)
  return `${first}${last}`.toUpperCase()
})

function logout() {
  localStorage.clear()
  router.push('/login')
}

const navItems = [
  { label: 'Tableau de bord', path: '/', icon: 'dashboard' },
  { label: 'Missions comptable', path: '/missions', icon: 'missions' },
  { label: 'Clients', path: '/clients', icon: 'clients' },
]
</script>

<template>
  <div class="flex h-screen bg-[#eef2f6]">
    <aside class="flex w-52 shrink-0 flex-col justify-between overflow-y-auto bg-[#0d3b56] px-4 py-6">
      <div>
        <RouterLink to="/" class="-mt-4 mb-6 flex justify-start">
          <img :src="logo" alt="Y3 Audit & Conseils" class="h-auto w-2/5" />
        </RouterLink>

        <nav class="space-y-2">
          <RouterLink
            v-for="item in navItems"
            :key="item.label"
            :to="item.path ?? route.path"
            class="flex w-full items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-3 text-left text-sm font-semibold transition"
            :class="
              item.path === route.path
                ? 'bg-white text-[#0d3b56]'
                : 'text-white hover:bg-white/10'
            "
          >
            <svg
              v-if="item.icon === 'dashboard'"
              viewBox="0 0 24 24"
              class="h-4 w-4 shrink-0"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <rect x="3" y="3" width="7" height="7" rx="1" />
              <rect x="14" y="3" width="7" height="7" rx="1" />
              <rect x="3" y="14" width="7" height="7" rx="1" />
              <rect x="14" y="14" width="7" height="7" rx="1" />
            </svg>
            <svg
              v-else-if="item.icon === 'missions'"
              viewBox="0 0 24 24"
              class="h-4 w-4 shrink-0"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <rect x="2" y="7" width="20" height="14" rx="2" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
              <path stroke-linecap="round" d="M2 13h20" />
            </svg>
            <svg
              v-else-if="item.icon === 'clients'"
              viewBox="0 0 24 24"
              class="h-4 w-4 shrink-0"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M23 21v-2a4 4 0 0 0-3-3.87" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
            {{ item.label }}
          </RouterLink>
        </nav>
      </div>

      <button
        type="button"
        class="flex items-center gap-2 rounded-lg px-4 py-3 text-left text-sm font-semibold text-white transition hover:bg-white/10"
        @click="logout"
      >
        <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
          <path stroke-linecap="round" stroke-linejoin="round" d="M16 17l5-5-5-5" />
          <path stroke-linecap="round" stroke-linejoin="round" d="M21 12H9" />
        </svg>
        Se déconnecter
      </button>
    </aside>

    <div class="flex min-h-0 min-w-0 flex-1 flex-col">
      <header class="flex shrink-0 items-center justify-end border-b border-gray-200 bg-white px-8 py-4">
        <RouterLink to="/profil" class="flex items-center gap-3">
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
        </RouterLink>
      </header>

      <main class="flex-1 overflow-y-auto p-6">
        <RouterView />
      </main>
    </div>
  </div>
</template>
