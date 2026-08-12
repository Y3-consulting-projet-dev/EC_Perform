<script setup>
import { computed, ref } from 'vue'
import MissionWorkspaceModal from '../components/MissionWorkspaceModal.vue'

const missions = [
  {
    client: 'Microsoft',
    mandat: '2026 -> 2026',
    responsable: 'Stéphanie Axelle Kotie AMANI',
    role: 'Auditeur - Senior Manager',
    statut: '-',
    progression: 0,
  },
  {
    client: 'Microsoft',
    mandat: '2026 -> 2026',
    responsable: "Verane N'Gouan",
    role: 'Auditeur - Directeur',
    statut: '-',
    progression: 0,
  },
  {
    client: 'Microsoft',
    mandat: '2026 -> 2026',
    responsable: "Verane N'Gouan",
    role: 'Auditeur - Directeur',
    statut: '-',
    progression: 0,
  },
]

const search = ref('')

const filteredMissions = computed(() =>
  missions.filter((m) => m.client.toLowerCase().includes(search.value.trim().toLowerCase())),
)

const showExportMenu = ref(false)

function exportExcel() {
  const headers = ['Client', 'Mandat', 'Responsable', 'Fonction', 'Statut', 'Progression']
  const rows = filteredMissions.value.map((m) => [
    m.client,
    m.mandat,
    m.responsable,
    m.role,
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

const showWorkspace = ref(false)
const selectedClient = ref(null)
const selectedMission = ref(null)

function openMissionProcess(mission) {
  selectedClient.value = { raisonSociale: mission.client }
  selectedMission.value = { exercice: mission.mandat.split('->').pop().trim() }
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
      <table class="w-full text-left text-sm">
        <thead>
          <tr class="bg-gray-50 text-sm font-bold text-[#0d3b56]">
            <th class="px-6 py-4">Client</th>
            <th class="px-6 py-4">Mandat</th>
            <th class="px-6 py-4">Responsable</th>
            <th class="px-6 py-4">Statut</th>
            <th class="px-6 py-4">Progression</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(mission, index) in filteredMissions"
            :key="index"
            class="cursor-pointer border-t border-gray-100 transition hover:bg-gray-50"
            @click="openMissionProcess(mission)"
          >
            <td class="px-6 py-4 text-[#0d3b56]">{{ mission.client }}</td>
            <td class="px-6 py-4 text-gray-500">{{ mission.mandat }}</td>
            <td class="px-6 py-4">
              <p class="font-bold text-[#0d3b56]">{{ mission.responsable }}</p>
              <p class="text-xs text-gray-400">{{ mission.role }}</p>
            </td>
            <td class="px-6 py-4 text-gray-400">{{ mission.statut }}</td>
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
        </tbody>
      </table>

      <div class="flex items-center justify-between border-t border-gray-100 px-6 py-4 print:hidden">
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
