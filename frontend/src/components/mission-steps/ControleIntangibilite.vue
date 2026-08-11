<script setup>
const controleIntangibilite = {
  ecarts: 22,
  totalComptes: 63,
  periodeN: '2024',
  periodeNMoins1: '2023',
  comptes: [
    {
      n: 1,
      compte: '12100000',
      bilanOuvertureN: '-30 802 192',
      bilanClotureNMoins1: 'N/A',
      ecart: '-30 802 192',
      statut: 'Nouveau',
      explication:
        "Le compte 12100000 est présent dans l'exercice N avec un solde d'ouverture de -30802192.0, mais n'existait pas dans l'exercice N-1. Cela peut indiquer une création de compte, un reclassement ou une erreur de saisie.",
    },
  ],
}

const compteStatutStyles = {
  Nouveau: 'bg-sky-100 text-sky-700',
}
</script>

<template>
  <div>
    <h1 class="mt-4 text-lg font-extrabold text-[#0d3b56]">Contrôle d'intangibilité</h1>

    <p class="mt-2 flex items-center gap-2 text-sm font-semibold text-amber-600">
      <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2">
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M12 9v4m0 4h.01M10.29 3.86 1.82 18a1 1 0 0 0 .86 1.5h18.64a1 1 0 0 0 .86-1.5L13.71 3.86a1 1 0 0 0-1.72 0Z"
        />
      </svg>
      {{ controleIntangibilite.ecarts }} écart(s) détecté(s) sur {{ controleIntangibilite.totalComptes }} compte(s)
    </p>
    <p class="mt-1 text-sm text-gray-500">
      Périodes analysées : N = {{ controleIntangibilite.periodeN }}, N-1 = {{ controleIntangibilite.periodeNMoins1 }}
    </p>

    <button
      type="button"
      class="mt-4 rounded-lg bg-[#7cb342] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#6ca038]"
    >
      Télécharger (XLSX)
    </button>

    <div class="mt-6 overflow-x-auto rounded-lg shadow-sm">
      <table class="w-full text-left text-sm">
        <thead>
          <tr class="bg-[#0d3b56] text-xs font-semibold uppercase text-white">
            <th class="px-4 py-3">Compte</th>
            <th class="px-4 py-3">Bilan ouverture (N)</th>
            <th class="px-4 py-3">Bilan clôture (N-1)</th>
            <th class="px-4 py-3">Écarts</th>
            <th class="px-4 py-3">Statut</th>
            <th class="px-4 py-3">Explications probables</th>
          </tr>
        </thead>
        <tbody class="bg-white">
          <tr v-for="compte in controleIntangibilite.comptes" :key="compte.n" class="border-t border-gray-100">
            <td class="px-4 py-3">
              <div class="flex items-center gap-2">
                <span
                  class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white"
                >
                  {{ compte.n }}
                </span>
                <span class="font-medium text-[#0d3b56]">{{ compte.compte }}</span>
              </div>
            </td>
            <td class="px-4 py-3 text-gray-500">{{ compte.bilanOuvertureN }}</td>
            <td class="px-4 py-3 text-gray-500">{{ compte.bilanClotureNMoins1 }}</td>
            <td class="px-4 py-3 font-bold text-red-600">{{ compte.ecart }}</td>
            <td class="px-4 py-3">
              <span
                class="rounded-full px-3 py-1 text-xs font-semibold"
                :class="compteStatutStyles[compte.statut] ?? 'bg-gray-100 text-gray-600'"
              >
                {{ compte.statut }}
              </span>
            </td>
            <td class="max-w-xs px-4 py-3 text-xs text-gray-500">{{ compte.explication }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
