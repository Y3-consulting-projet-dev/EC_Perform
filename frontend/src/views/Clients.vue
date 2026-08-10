<script setup>
import { computed, ref } from 'vue'
import ClientDetailModal from '../components/ClientDetailModal.vue'
import NewClientModal from '../components/NewClientModal.vue'
import { addClient, clients } from '../stores/clients'

const secteurs = computed(() => ['Tous secteurs', ...new Set(clients.map((c) => c.secteurActivite))])

const search = ref('')
const secteurFilter = ref('Tous secteurs')
const showNewClientModal = ref(false)

function handleClientCreated(form) {
  addClient(form)
}

const filteredClients = computed(() =>
  clients.filter((c) => {
    const matchesSearch = c.raisonSociale.toLowerCase().includes(search.value.trim().toLowerCase())
    const matchesSecteur = secteurFilter.value === 'Tous secteurs' || c.secteurActivite === secteurFilter.value
    return matchesSearch && matchesSecteur
  }),
)

const selectedClient = ref(null)
const showClientDetail = ref(false)

function openClientDetail(client) {
  selectedClient.value = client
  showClientDetail.value = true
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
          <tr v-for="client in filteredClients" :key="client.raisonSociale" class="border-t border-gray-100">
            <td class="py-4 font-medium text-[#0d3b56]">{{ client.raisonSociale }}</td>
            <td class="py-4 text-gray-500">{{ client.secteurActivite }}</td>
            <td class="py-4 text-gray-500">{{ client.ville }}</td>
            <td class="py-4 text-gray-500">{{ client.rccm }}</td>
            <td class="py-4">
              <button
                type="button"
                class="rounded-full bg-[#7cb342] px-5 py-1.5 text-xs font-semibold text-white transition hover:bg-[#6ca038]"
                @click="openClientDetail(client)"
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
    <ClientDetailModal v-model="showClientDetail" :client="selectedClient" />
  </div>
</template>
