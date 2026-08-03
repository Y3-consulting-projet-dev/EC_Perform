<script setup>
import { computed, ref } from 'vue'
import NewClientModal from '../components/NewClientModal.vue'

const clients = ref([
  { entreprise: 'Microsoft', secteur: 'Technologie', ville: 'New York', rccm: 'SDRE123' },
  { entreprise: 'TEACH', secteur: 'Technologie', ville: 'ABidjan', rccm: 'CI-12' },
  { entreprise: 'BibiTech', secteur: 'Technique', ville: '18000', rccm: 'CI-12' },
  { entreprise: 'LEAN DISTRIBUTION', secteur: 'Télécommunications et TIC', ville: 'DIVO', rccm: 'CI-ABJ-2019-B-21427' },
])

const secteurs = computed(() => ['Tous secteurs', ...new Set(clients.value.map((c) => c.secteur))])

const search = ref('')
const secteurFilter = ref('Tous secteurs')
const showNewClientModal = ref(false)

const filteredClients = computed(() =>
  clients.value.filter((c) => {
    const matchesSearch = c.entreprise.toLowerCase().includes(search.value.trim().toLowerCase())
    const matchesSecteur = secteurFilter.value === 'Tous secteurs' || c.secteur === secteurFilter.value
    return matchesSearch && matchesSecteur
  }),
)

function handleClientCreated(form) {
  clients.value.push({
    entreprise: form.raisonSociale,
    secteur: form.secteurActivite,
    ville: form.ville,
    rccm: form.rccm,
  })
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-start justify-between">
      <div>
        <h1 class="text-lg font-bold text-[#0d3b56]">Liste des clients</h1>
        <p class="text-xs text-gray-400">Clients en base de données</p>
      </div>

      <div class="flex items-center gap-3">
        <button
          type="button"
          class="rounded-lg bg-[#0d3b56] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#0a2f45]"
          @click="showNewClientModal = true"
        >
          Nouveau client
        </button>
        <input
          v-model="search"
          type="text"
          placeholder="Rechercher par entreprise..."
          class="rounded-xl border border-[#7cb342] bg-white px-4 py-2.5 text-sm text-[#0d3b56] outline-none placeholder-gray-400 focus:ring-2 focus:ring-[#7cb342]"
        />
        <select
          v-model="secteurFilter"
          class="rounded-xl border border-[#7cb342] bg-white px-4 py-2.5 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342]"
        >
          <option v-for="secteur in secteurs" :key="secteur">{{ secteur }}</option>
        </select>
      </div>
    </div>

    <div class="rounded-lg bg-white p-6 shadow-sm">
      <table class="w-full text-left text-sm">
        <thead>
          <tr class="text-sm text-[#0d3b56]">
            <th class="pb-3 font-bold">Entreprise</th>
            <th class="pb-3 font-bold">Secteur</th>
            <th class="pb-3 font-bold">Ville</th>
            <th class="pb-3 font-bold">RCCM</th>
            <th class="pb-3 font-bold">Action</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="client in filteredClients" :key="client.entreprise" class="border-t border-gray-100">
            <td class="py-4 font-medium text-[#0d3b56]">{{ client.entreprise }}</td>
            <td class="py-4 text-gray-500">{{ client.secteur }}</td>
            <td class="py-4 text-gray-500">{{ client.ville }}</td>
            <td class="py-4 text-gray-500">{{ client.rccm }}</td>
            <td class="py-4">
              <button
                type="button"
                class="rounded-full bg-[#7cb342] px-5 py-1.5 text-xs font-semibold text-white transition hover:bg-[#6ca038]"
              >
                Voir
              </button>
            </td>
          </tr>
          <tr v-if="filteredClients.length === 0">
            <td colspan="5" class="py-6 text-center text-sm text-gray-400">Aucun client ne correspond à la recherche.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <NewClientModal v-model="showNewClientModal" @created="handleClientCreated" />
  </div>
</template>
