<script setup>
import { reactive, ref } from 'vue'

const risqueOptions = ['Élevé', 'Moyen', 'Faible']
const collaborateurs = ['KAK', 'SCL', 'KKA', 'HBA']

const risqueStyles = {
  Élevé: 'bg-red-100 text-red-600',
  Moyen: 'bg-amber-100 text-amber-700',
  Faible: 'bg-green-100 text-green-700',
}

const cabinetCollaborateurs = [
  { initials: 'KAK', nom: 'K.A. Koné', role: 'Collaborateur confirmé', disponible: true },
  { initials: 'HBA', nom: 'H. Ba', role: 'Collaborateur confirmé', disponible: true },
  { initials: 'OPK', nom: 'O.P. Koné', role: '', disponible: true },
  { initials: 'AK', nom: 'A. Kouadio', role: 'Assistant', disponible: true },
  { initials: 'LTO', nom: 'L. Touré', role: 'Assistant', disponible: true },
  { initials: 'MDK', nom: 'M.D. Koffi', role: 'Assistant', disponible: false },
]

const showTeamPanel = ref(false)
const equipeSelectionnee = ref([])

const cycles = reactive([
  { code: 'A', libelle: 'Trésorerie et financement', risque: 'Élevé', assigneA: 'KAK', delai: 3 },
  { code: 'B', libelle: 'Ventes et clients', risque: 'Élevé', assigneA: 'KAK', delai: 3 },
  { code: 'C', libelle: 'Achats et fournisseurs', risque: 'Moyen', assigneA: 'SCL', delai: 2 },
  { code: 'D', libelle: 'Stocks', risque: 'Moyen', assigneA: 'SCL', delai: 2 },
  { code: 'E', libelle: 'Immobilisations', risque: 'Faible', assigneA: 'KKA', delai: 1 },
  { code: 'F', libelle: 'Personnel et charges sociales', risque: 'Faible', assigneA: 'KKA', delai: 1 },
  { code: 'G', libelle: 'Fiscalité', risque: 'Élevé', assigneA: 'HBA', delai: 3 },
  { code: 'H', libelle: 'Capitaux propres', risque: 'Élevé', assigneA: 'HBA', delai: 3 },
])
</script>

<template>
  <div>
    <div class="mt-4 flex items-center justify-between">
      <h1 class="text-lg font-extrabold text-[#0d3b56]">Repartition des cycles</h1>

      <div class="relative">
        <button
          type="button"
          class="flex items-center gap-2 rounded-lg bg-[#0d3b56] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#0a2f45]"
          @click="showTeamPanel = !showTeamPanel"
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
          <p class="text-xs text-gray-500">
            Collaborateurs du cabinet — leur charge actuelle sur les autres missions est indiquée.
          </p>

          <div class="mt-3 space-y-1">
            <label
              v-for="collaborateur in cabinetCollaborateurs"
              :key="collaborateur.initials"
              class="flex items-center gap-3 rounded-lg px-2 py-2"
              :class="collaborateur.disponible ? 'hover:bg-gray-50' : 'opacity-60'"
            >
              <input
                type="checkbox"
                :value="collaborateur.initials"
                v-model="equipeSelectionnee"
                :disabled="!collaborateur.disponible"
                class="h-4 w-4 rounded border-gray-300 text-[#7cb342] focus:ring-[#7cb342]"
              />
              <span
                class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#0d3b56] text-xs font-bold text-white"
              >
                {{ collaborateur.initials }}
              </span>
              <span class="flex-1">
                <span class="block text-sm font-bold text-[#0d3b56]">
                  <span v-if="!collaborateur.disponible" class="mr-1 text-xs font-semibold text-red-500"
                    >Indisponible —</span
                  >
                  {{ collaborateur.nom }}
                </span>
                <span v-if="collaborateur.role" class="block text-xs text-gray-400">{{ collaborateur.role }}</span>
              </span>
            </label>
          </div>

          <div class="mt-4 flex justify-end">
            <button
              type="button"
              class="rounded-lg bg-[#0d3b56] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#0a2f45]"
              @click="showTeamPanel = false"
            >
              Créer l'équipe
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="mt-6 overflow-x-auto rounded-lg shadow-sm">
      <table class="w-full text-left text-sm">
        <thead>
          <tr class="bg-[#7cb342] text-sm font-bold text-white">
            <th class="px-4 py-3">Cycle</th>
            <th class="px-4 py-3 text-center">Risque</th>
            <th class="px-4 py-3 text-center">Assigné à</th>
            <th class="px-4 py-3 text-right">Délais</th>
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
                  class="appearance-none rounded-full px-4 py-1.5 text-xs font-semibold outline-none"
                  :class="risqueStyles[cycle.risque]"
                >
                  <option v-for="option in risqueOptions" :key="option" :value="option">{{ option }}</option>
                </select>
              </div>
            </td>
            <td class="px-4 py-3">
              <div class="flex justify-center">
                <select
                  v-model="cycle.assigneA"
                  class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342]"
                >
                  <option v-for="option in collaborateurs" :key="option" :value="option">{{ option }}</option>
                </select>
              </div>
            </td>
            <td class="px-4 py-3 text-right text-gray-500">{{ cycle.delai }} jour(s)</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
