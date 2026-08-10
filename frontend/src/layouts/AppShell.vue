<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import logo from '../assets/logo.y3.png'

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
  { label: 'Tableau de board', path: '/' },
  { label: 'Clients', path: '/clients' },
  { label: 'Missions comptable', path: null },
]
</script>

<template>
  <div class="flex h-screen flex-col bg-[#eef2f6]">
    <header class="flex shrink-0 items-center justify-between border-b border-gray-200 bg-white px-8 py-4">
      <img :src="logo" alt="Y3 Audit & Conseils" class="h-16 w-auto" />

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

    <div class="flex min-h-0 flex-1">
      <aside class="flex w-60 shrink-0 flex-col justify-between overflow-y-auto bg-[#0d3b56] px-4 py-6">
        <nav class="space-y-2">
          <RouterLink
            v-for="item in navItems"
            :key="item.label"
            :to="item.path ?? route.path"
            class="block w-full rounded-lg px-4 py-3 text-left text-sm font-semibold transition"
            :class="
              item.path === route.path
                ? 'bg-white text-[#0d3b56]'
                : 'text-white hover:bg-white/10'
            "
          >
            {{ item.label }}
          </RouterLink>
        </nav>

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

      <main class="flex-1 overflow-y-auto p-6">
        <RouterView />
      </main>
    </div>
  </div>
</template>
