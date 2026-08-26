<script setup>
import { computed, onMounted, ref } from 'vue'
import MissionWorkspaceModal from '../components/MissionWorkspaceModal.vue'
import { API_URL as apiUrl } from '../utils/apiUrl'


function authHeaders() {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${localStorage.getItem('access_token')}`,
  }
}

const missions = ref([])
const loading = ref(false)
const error = ref('')

async function fetchMissions() {
  loading.value = true
  error.value = ''
  try {
    const response = await fetch(`${apiUrl}/missions`, { headers: authHeaders() })
    const data = await response.json()
    if (!response.ok) {
      error.value = data.detail ?? 'Une erreur est survenue.'
      return
    }
    missions.value = data
  } catch {
    error.value = 'Impossible de contacter le serveur.'
  } finally {
    loading.value = false
  }
}

onMounted(fetchMissions)

const search = ref('')

const filteredMissions = computed(() =>
  missions.value.filter((m) => m.client.toLowerCase().includes(search.value.trim().toLowerCase())),
)

const statutStyles = {
  'En cours': 'bg-sky-100 text-sky-700',
  Terminée: 'bg-[#7cb342] text-white',
  'Pas encore commencée': 'bg-gray-100 text-gray-500',
}

const showExportMenu = ref(false)

function exportExcel() {
  const headers = ['Client', 'Durée', 'Responsable', 'Grade', 'Statut', 'Progression']
  const rows = filteredMissions.value.map((m) => [
    m.client,
    dureeLabel(m),
    m.manager,
    m.managerGrade,
    m.statut,
    `${m.progression}%`,
  ])
  const csv = [headers, ...rows]
    .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(';'))
    .join('\r\n')
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'missions-comptable.csv'
  link.click()
  URL.revokeObjectURL(url)
  showExportMenu.value = false
}

function exportPdf() {
  showExportMenu.value = false
  window.print()
}

function dureeLabel(mission) {
  if (mission.dureeSemaines === null || mission.dureeSemaines === undefined) return '-'
  return `${mission.dureeSemaines} semaine${mission.dureeSemaines > 1 ? 's' : ''}`
}

function formatDate(value) {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return date.toLocaleDateString('fr-FR')
}

function dureeTitle(mission) {
  const debut = formatDate(mission.dateDebut)
  const fin = formatDate(mission.echeance)
  if (!debut || !fin) return ''
  return `Du ${debut} au ${fin}`
}

const showWorkspace = ref(false)
const selectedClient = ref(null)
const selectedMission = ref(null)

function openMissionProcess(mission) {
  selectedClient.value = { raisonSociale: mission.client }
  selectedMission.value = mission
  showWorkspace.value = true
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-start justify-between print:hidden">
      <div>
        <h1 class="text-lg font-bold text-[#0d3b56]">Missions comptable</h1>
        <p class="text-xs text-gray-400">Liste complète des missions effectuées</p>
      </div>

      <div class="relative">
        <button
          type="button"
          class="flex items-center gap-2 rounded-lg border border-[#7cb342] bg-white px-5 py-2.5 text-sm font-semibold text-[#0d3b56] transition hover:bg-gray-50"
          @click="showExportMenu = !showExportMenu"
        >
          <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 3v12m0 0-4-4m4 4 4-4M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
          </svg>
          Exporter
          <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="m6 9 6 6 6-6" />
          </svg>
        </button>

        <div v-if="showExportMenu" class="fixed inset-0 z-10" @click="showExportMenu = false"></div>

        <div
          v-if="showExportMenu"
          class="absolute right-0 z-20 mt-2 w-48 overflow-hidden rounded-lg border border-gray-200 bg-white shadow-lg"
          @click.stop
        >
          <button
            type="button"
            class="flex w-full items-center gap-2 px-4 py-3 text-left text-sm font-semibold text-gray-600 transition hover:bg-gray-50"
            @click="exportExcel"
          >
            Excel (CSV)
          </button>
          <button
            type="button"
            class="flex w-full items-center gap-2 border-t border-gray-100 px-4 py-3 text-left text-sm font-semibold text-gray-600 transition hover:bg-gray-50"
            @click="exportPdf"
          >
            PDF
          </button>
        </div>
      </div>
    </div>

    <div class="relative max-w-xl print:hidden">
      <svg
        viewBox="0 0 24 24"
        class="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <circle cx="11" cy="11" r="7" />
        <path stroke-linecap="round" d="m21 21-4.35-4.35" />
      </svg>
      <input
        v-model="search"
        type="text"
        placeholder="Rechercher un client..."
        class="w-full rounded-xl bg-white py-3 pl-12 pr-4 text-sm text-[#0d3b56] shadow-sm outline-none placeholder-gray-400 focus:ring-2 focus:ring-[#7cb342]"
      />
    </div>

    <div class="overflow-hidden rounded-lg bg-white shadow-sm">
      <div class="overflow-x-auto">
      <table class="w-full min-w-[720px] text-left text-sm">
        <thead>
          <tr class="bg-gray-50 text-sm font-bold text-[#0d3b56]">
            <th class="px-6 py-4">Client</th>
            <th class="px-6 py-4">Durée</th>
            <th class="px-6 py-4">Responsable</th>
            <th class="px-6 py-4">Statut</th>
            <th class="px-6 py-4">Progression</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="5" class="px-6 py-6 text-center text-sm text-gray-400">Chargement des missions...</td>
          </tr>
          <tr v-else-if="error">
            <td colspan="5" class="px-6 py-6 text-center text-sm text-red-600">{{ error }}</td>
          </tr>
          <template v-else>
            <tr
              v-for="mission in filteredMissions"
              :key="mission.id"
              class="cursor-pointer border-t border-gray-100 transition hover:bg-gray-50"
              @click="openMissionProcess(mission)"
            >
              <td class="px-6 py-4 text-[#0d3b56]">{{ mission.client }}</td>
              <td class="px-6 py-4 text-gray-500" :title="dureeTitle(mission)">{{ dureeLabel(mission) }}</td>
              <td class="px-6 py-4">
                <p class="font-bold text-[#0d3b56]">{{ mission.manager }}</p>
                <p class="text-xs text-gray-400">{{ mission.managerGrade }}</p>
              </td>
              <td class="px-6 py-4">
                <span class="rounded-full px-3 py-1 text-xs font-semibold" :class="statutStyles[mission.statut]">
                  {{ mission.statut }}
                </span>
              </td>
              <td class="px-6 py-4">
                <div class="flex items-center gap-3">
                  <div class="h-1.5 max-w-[220px] flex-1 overflow-hidden rounded-full bg-gray-200">
                    <div class="h-full rounded-full bg-[#7cb342]" :style="{ width: mission.progression + '%' }"></div>
                  </div>
                  <span class="text-xs text-gray-500">{{ mission.progression }}%</span>
                </div>
              </td>
            </tr>
            <tr v-if="filteredMissions.length === 0">
              <td colspan="5" class="px-6 py-6 text-center text-sm text-gray-400">
                Aucune mission ne correspond à la recherche.
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      </div>

      <div class="flex flex-wrap items-center justify-between gap-3 border-t border-gray-100 px-6 py-4 print:hidden">
        <p class="text-sm text-gray-400">Page 1 / 1 - {{ filteredMissions.length }} missions</p>
        <div class="flex gap-3">
          <button
            type="button"
            class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-500 transition hover:bg-gray-50"
          >
            Précédent
          </button>
          <button
            type="button"
            class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-500 transition hover:bg-gray-50"
          >
            Suivant
          </button>
        </div>
      </div>
    </div>

    <MissionWorkspaceModal v-model="showWorkspace" :client="selectedClient" :mission="selectedMission" />
  </div>
</template>
