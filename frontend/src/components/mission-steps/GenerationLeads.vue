<script setup>
import { ref } from 'vue'
import FeuilleMaitresseModal from './FeuilleMaitresseModal.vue'

const leads = [
  {
    code: 'A',
    libelle: 'Trésorerie et financement',
    soldeN: '98 400 000',
    soldeNMoins1: '93 600 000',
    variance: '+3,6 %',
    hausse: true,
  },
  {
    code: 'B',
    libelle: 'Ventes et clients',
    soldeN: '-742 100 000',
    soldeNMoins1: '-542 100 000',
    variance: '+20,1 %',
    hausse: true,
  },
  {
    code: 'C',
    libelle: 'Achats et fournisseurs',
    soldeN: '318 700 000',
    soldeNMoins1: '302 700 000',
    variance: '+9,1 %',
    hausse: true,
  },
  {
    code: 'D',
    libelle: 'Stocks',
    soldeN: '187 300 000',
    soldeNMoins1: '200 000 000',
    variance: '-8,6 %',
    hausse: false,
  },
]

const showFeuilleMaitresse = ref(false)
const selectedLead = ref(null)

function openFeuilleMaitresse(lead) {
  selectedLead.value = lead
  showFeuilleMaitresse.value = true
}
</script>

<template>
  <div>
    <h1 class="mt-4 text-lg font-extrabold text-[#0d3b56]">Génération des leads</h1>

    <div class="mt-6 grid grid-cols-2 gap-6">
      <div v-for="lead in leads" :key="lead.code" class="rounded-xl bg-white p-5 shadow-sm">
        <div class="flex items-center gap-2">
          <span
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[#0d3b56] text-xs font-bold text-white"
          >
            {{ lead.code }}
          </span>
          <span class="font-bold text-[#0d3b56]">{{ lead.libelle }}</span>
        </div>

        <div class="mt-4 space-y-1 text-sm">
          <div class="flex justify-between">
            <span class="text-gray-500">Solde N</span>
            <span class="font-medium text-[#0d3b56]">{{ lead.soldeN }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">Solde N-1</span>
            <span class="font-medium text-[#0d3b56]">{{ lead.soldeNMoins1 }}</span>
          </div>
        </div>

        <p class="mt-3 text-sm font-bold" :class="lead.hausse ? 'text-red-600' : 'text-green-600'">
          {{ lead.hausse ? '▲' : '▼' }} {{ lead.variance }} à expliquer
        </p>

        <button
          type="button"
          class="mx-auto mt-3 block rounded-lg bg-[#0d3b56] px-6 py-2 text-sm font-semibold text-white transition hover:bg-[#0a2f45]"
          @click="openFeuilleMaitresse(lead)"
        >
          Ouvrir
        </button>
      </div>
    </div>

    <FeuilleMaitresseModal v-model="showFeuilleMaitresse" :lead="selectedLead" />
  </div>
</template>
