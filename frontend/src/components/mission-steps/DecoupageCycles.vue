<script setup>
const cycles = [
  { code: 'A', libelle: 'Trésorerie et financement', plage: '52 à 57', nbComptes: 14, soldeN: '98 400 000', soldeNMoins1: '93 600 000' },
  { code: 'B', libelle: 'Ventes et clients', plage: '70', nbComptes: 29, soldeN: '-742 100 000', soldeNMoins1: '-542 100 000' },
  { code: 'C', libelle: 'Achats et fournisseurs', plage: '60', nbComptes: 34, soldeN: '318 700 000', soldeNMoins1: '302 700 000' },
  { code: 'D', libelle: 'Stocks', plage: '31 à 39', nbComptes: 22, soldeN: '187 300 000', soldeNMoins1: '200 000 000' },
  { code: 'E', libelle: 'Immobilisations', plage: '21 à 28', nbComptes: 38, soldeN: '412 500 000', soldeNMoins1: '398 500 000' },
  { code: 'F', libelle: 'Personnel et charges sociales', plage: '42 à 43', nbComptes: 21, soldeN: '-64 800 000', soldeNMoins1: '-34 800 000' },
  { code: 'G', libelle: 'Fiscalité', plage: '52 à 57', nbComptes: 14, soldeN: '98 400 000', soldeNMoins1: '93 600 000' },
  { code: 'H', libelle: 'Capitaux propres', plage: '10 à 13', nbComptes: 14, soldeN: '-520 000 000', soldeNMoins1: '-536 000 000' },
]
</script>

<template>
  <div>
    <h1 class="mt-4 text-lg font-extrabold text-[#0d3b56]">Planification des travaux</h1>
    <p class="mt-1 text-sm text-gray-500">
      Génération automatique des cycles à partir de la balance importée en Phase 1.
    </p>

    <div class="mt-6 overflow-x-auto rounded-lg shadow-sm">
      <table class="w-full text-left text-sm">
        <thead>
          <tr class="bg-[#7cb342] text-sm font-bold text-white">
            <th class="px-4 py-3">Code</th>
            <th class="px-4 py-3">Cycle</th>
            <th class="px-4 py-3 text-center">Plage</th>
            <th class="px-4 py-3 text-center">NB de comptes</th>
            <th class="px-4 py-3 text-right">Solde N</th>
            <th class="px-4 py-3 text-right">Solde N-1</th>
          </tr>
        </thead>
        <tbody class="bg-white">
          <tr v-for="cycle in cycles" :key="cycle.code" class="border-t border-gray-100">
            <td class="px-4 py-3">
              <span
                class="flex h-7 w-7 items-center justify-center rounded-lg bg-[#0d3b56] text-xs font-bold text-white"
              >
                {{ cycle.code }}
              </span>
            </td>
            <td class="px-4 py-3 font-medium text-[#0d3b56]">{{ cycle.libelle }}</td>
            <td class="px-4 py-3 text-center text-gray-500">{{ cycle.plage }}</td>
            <td class="px-4 py-3 text-center text-gray-500">{{ cycle.nbComptes }}</td>
            <td class="px-4 py-3 text-right text-gray-500">{{ cycle.soldeN }}</td>
            <td class="px-4 py-3 text-right text-gray-500">{{ cycle.soldeNMoins1 }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
