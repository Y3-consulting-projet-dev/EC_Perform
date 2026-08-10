<script setup>
import { computed, ref } from 'vue'

const tabs = [
  { id: 'arithmetique', label: 'Contrôle Arithmétique' },
  { id: 'vraisemblance', label: 'Contrôle de Vraisemblance' },
]
const activeTab = ref('arithmetique')

const annees = ['2024', '2023']
const selectedAnnee = ref('2024')

const controlesArithmetiques = {
  '2024': {
    equilibreOk: true,
    erreurs: 5,
    equilibre: {
      totalDebits: '3 918 813 969',
      totalCredits: '3 918 813 969',
      nombreComptes: 128,
      explication:
        "Le système a vérifié que le total des débits (3,918,813,969 FCFA) est strictement égal au total des crédits (3,918,813,969 FCFA) en additionnant les colonnes 'Débit fin' et 'Crédit fin' de tous les comptes.",
      commentVerifier:
        "Additionnez toutes les valeurs de la colonne 'Débit fin' de tous les comptes, puis additionnez toutes les valeurs de la colonne 'Crédit fin'. Les deux totaux doivent être identiques.",
    },
    formule: {
      libelle: "Solde de clôture = Solde d'ouverture + Mouvements de période",
      description:
        "Le système a vérifié la formule 'Solde de clôture = Solde d'ouverture + Mouvements de période' pour 128 comptes. 123 comptes respectent la formule, mais 5 comptes présentent des ERREURS. Les comptes en erreur sont listés ci-dessous avec les détails de l'écart détecté.",
      comptesVerifies: 128,
      formuleRespectee: 123,
      formuleNonRespectee: 5,
    },
  },
}

const controleActif = computed(() => controlesArithmetiques[selectedAnnee.value])
</script>

<template>
  <div>
    <h1 class="mt-4 text-lg font-extrabold text-[#0d3b56]">Contrôle de cohérence</h1>

    <div class="mt-4 flex gap-3">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        class="flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition"
        :class="
          activeTab === tab.id
            ? 'bg-[#0d3b56] text-white'
            : 'border border-gray-200 bg-white text-gray-500 hover:bg-gray-50'
        "
        @click="activeTab = tab.id"
      >
        <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="4" y="3" width="16" height="18" rx="2" />
          <path stroke-linecap="round" d="M8 8h8M8 12h8M8 16h5" />
        </svg>
        {{ tab.label }}
      </button>
    </div>

    <template v-if="activeTab === 'arithmetique'">
      <div class="mt-6 flex items-center gap-3">
        <label for="annee" class="text-sm font-bold text-[#0d3b56]">Sélectionner l'année :</label>
        <select
          id="annee"
          v-model="selectedAnnee"
          class="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342]"
        >
          <option v-for="annee in annees" :key="annee" :value="annee">{{ annee }}</option>
        </select>
        <button
          type="button"
          class="rounded-lg bg-[#7cb342] px-5 py-2 text-sm font-semibold text-white transition hover:bg-[#6ca038]"
        >
          Télécharger (XLSX)
        </button>
      </div>

      <div v-if="controleActif" class="mt-6 flex items-center gap-4 rounded-xl bg-white p-5 shadow-sm">
        <span class="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-[#0d3b56] text-sm font-bold text-white">
          {{ selectedAnnee }}
        </span>
        <div>
          <p class="font-bold text-[#0d3b56]">Contrôles Arithmétiques - Année {{ selectedAnnee }}</p>
          <p class="mt-1 flex items-center gap-4 text-xs text-gray-500">
            <span class="flex items-center gap-1.5">
              <span class="h-2 w-2 rounded-full bg-[#7cb342]"></span>
              Équilibre : {{ controleActif.equilibreOk ? 'OK' : 'Erreur' }}
            </span>
            <span class="flex items-center gap-1.5">
              <span class="h-2 w-2 rounded-full bg-amber-500"></span>
              {{ controleActif.erreurs }} erreur(s) détectée(s)
            </span>
          </p>
        </div>
      </div>

      <div v-if="controleActif" class="mt-6 space-y-6">
        <div class="rounded-xl border-l-4 border-[#7cb342] bg-[#f2f8ee] p-5">
          <p class="flex items-center gap-2 text-sm font-bold text-[#4b7a5c]">
            <span class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#7cb342] text-white">
              <svg viewBox="0 0 24 24" class="h-3 w-3" fill="none" stroke="currentColor" stroke-width="3">
                <path stroke-linecap="round" stroke-linejoin="round" d="m5 13 4 4L19 7" />
              </svg>
            </span>
            Premier Contrôle Arithmétique : Vérification de l'Équilibre
          </p>

          <p class="mt-3 text-xs font-semibold text-gray-500">Résultats exacts de la vérification :</p>
          <div class="mt-2 grid grid-cols-2 gap-4">
            <div class="rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm text-[#0d3b56]">
              Total des débits : <span class="font-bold">{{ controleActif.equilibre.totalDebits }} FCFA</span>
            </div>
            <div class="rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm text-[#0d3b56]">
              Total des crédits : <span class="font-bold">{{ controleActif.equilibre.totalCredits }} FCFA</span>
            </div>
          </div>
          <p class="mt-3 text-xs text-gray-500">
            Nombre de comptes analysés : {{ controleActif.equilibre.nombreComptes }}
          </p>

          <div class="mt-3 rounded-lg bg-[#e2f0e7] p-3 text-xs text-[#3f6650]">
            <span class="font-bold">Explication :</span> {{ controleActif.equilibre.explication }}
          </div>
          <div class="mt-2 rounded-lg bg-[#e2f0e7] p-3 text-xs text-[#3f6650]">
            <span class="font-bold">Comment vérifier manuellement :</span> {{ controleActif.equilibre.commentVerifier }}
          </div>
        </div>

        <div class="rounded-xl border-l-4 border-amber-500 bg-amber-50 p-5">
          <p class="flex items-center gap-2 text-sm font-bold text-amber-700">
            <svg viewBox="0 0 24 24" class="h-5 w-5 shrink-0" fill="none" stroke="currentColor" stroke-width="2">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M12 9v4m0 4h.01M10.29 3.86 1.82 18a1 1 0 0 0 .86 1.5h18.64a1 1 0 0 0 .86-1.5L13.71 3.86a1 1 0 0 0-1.72 0Z"
              />
            </svg>
            Second Contrôle Arithmétique : Vérification de la Formule
          </p>

          <p class="mt-3 text-sm font-bold text-amber-700">Formule vérifiée : {{ controleActif.formule.libelle }}</p>
          <p class="mt-2 text-xs text-amber-800">{{ controleActif.formule.description }}</p>

          <div class="mt-3 grid grid-cols-3 gap-4">
            <div class="rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-center text-sm text-[#0d3b56]">
              Comptes vérifiés : <span class="font-bold">{{ controleActif.formule.comptesVerifies }}</span>
            </div>
            <div class="rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-center text-sm text-[#0d3b56]">
              Formule respectée : <span class="font-bold text-[#7cb342]">{{ controleActif.formule.formuleRespectee }}</span>
            </div>
            <div class="rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-center text-sm text-[#0d3b56]">
              Formule non respectée :
              <span class="font-bold text-red-600">{{ controleActif.formule.formuleNonRespectee }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <p v-else class="mt-6 text-sm text-gray-500">Contenu à venir pour le contrôle de vraisemblance.</p>
  </div>
</template>
