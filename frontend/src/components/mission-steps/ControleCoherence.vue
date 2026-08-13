<script setup>
import { onMounted, ref } from 'vue'

const props = defineProps({
  mission: { type: Object, required: true },
})

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function authHeaders() {
  return { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
}

const tabs = [
  { id: 'arithmetique', label: 'Contrôle Arithmétique' },
  { id: 'vraisemblance', label: 'Contrôle de Vraisemblance' },
]
const activeTab = ref('arithmetique')

const balances = ref([])
const selectedDocumentId = ref('')
const controleActif = ref(null)

const loadingBalances = ref(true)
const loadingControle = ref(false)
const error = ref('')

function balanceLabel(balance) {
  return balance.annee ? `${balance.annee} — ${balance.description}` : balance.description
}

async function fetchBalances() {
  loadingBalances.value = true
  error.value = ''
  try {
    const response = await fetch(`${apiUrl}/missions/${props.mission.id}/balances`, { headers: authHeaders() })
    const data = await response.json()
    if (!response.ok) {
      error.value = data.detail ?? 'Une erreur est survenue.'
      return
    }
    balances.value = data.balances
    if (balances.value.length) {
      selectedDocumentId.value = balances.value[0].documentId
      await fetchControle()
    }
  } catch {
    error.value = 'Impossible de contacter le serveur.'
  } finally {
    loadingBalances.value = false
  }
}

async function fetchControle() {
  if (!selectedDocumentId.value) {
    controleActif.value = null
    return
  }
  loadingControle.value = true
  error.value = ''
  try {
    const params = new URLSearchParams({ documentId: selectedDocumentId.value })
    const response = await fetch(`${apiUrl}/missions/${props.mission.id}/controles/coherence?${params}`, {
      headers: authHeaders(),
    })
    const data = await response.json()
    if (!response.ok) {
      error.value = data.detail ?? 'Une erreur est survenue.'
      controleActif.value = null
      return
    }
    controleActif.value = data
  } catch {
    error.value = 'Impossible de contacter le serveur.'
    controleActif.value = null
  } finally {
    loadingControle.value = false
  }
}

onMounted(fetchBalances)
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
      <p v-if="loadingBalances" class="mt-6 text-sm text-gray-400">Chargement des balances...</p>

      <p v-else-if="balances.length === 0" class="mt-4 rounded-lg bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-700">
        Aucune balance disponible pour cette mission. Déposez-la depuis la Phase 1 – Ouverture et collecte, dans
        n'importe quelle catégorie : tout document dont le nom ou la description contient « balance » est
        automatiquement détecté, dès son dépôt, même si les autres documents de la checklist ne sont pas encore
        reçus.
      </p>

      <template v-else>
        <div class="mt-6 flex items-center gap-3">
          <label for="balance" class="text-sm font-bold text-[#0d3b56]">Sélectionner la balance :</label>
          <select
            id="balance"
            v-model="selectedDocumentId"
            class="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342]"
            @change="fetchControle"
          >
            <option v-for="balance in balances" :key="balance.documentId" :value="balance.documentId">
              {{ balanceLabel(balance) }}
            </option>
          </select>
          <button
            type="button"
            class="rounded-lg bg-[#7cb342] px-5 py-2 text-sm font-semibold text-white transition hover:bg-[#6ca038]"
          >
            Télécharger (XLSX)
          </button>
        </div>

        <p v-if="error" class="mt-3 text-sm text-red-600">{{ error }}</p>
        <p v-if="loadingControle" class="mt-4 text-sm text-gray-400">Calcul du contrôle...</p>

        <template v-if="controleActif">
          <div class="mt-6 flex items-center gap-4 rounded-xl bg-white p-5 shadow-sm">
            <span
              class="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-[#0d3b56] text-sm font-bold text-white"
            >
              {{ controleActif.annee }}
            </span>
            <div>
              <p class="font-bold text-[#0d3b56]">Contrôles Arithmétiques - Exercice {{ controleActif.annee }}</p>
              <p class="mt-1 flex items-center gap-4 text-xs text-gray-500">
                <span class="flex items-center gap-1.5">
                  <span
                    class="h-2 w-2 rounded-full"
                    :class="controleActif.equilibreOk ? 'bg-[#7cb342]' : 'bg-red-500'"
                  ></span>
                  Équilibre : {{ controleActif.equilibreOk ? 'OK' : 'Erreur' }}
                </span>
                <span class="flex items-center gap-1.5">
                  <span class="h-2 w-2 rounded-full bg-amber-500"></span>
                  {{ controleActif.erreurs }} erreur(s) détectée(s)
                </span>
              </p>
            </div>
          </div>

          <div class="mt-6 space-y-6">
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
                <span class="font-bold">Comment vérifier manuellement :</span>
                {{ controleActif.equilibre.commentVerifier }}
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
                  Formule respectée :
                  <span class="font-bold text-[#7cb342]">{{ controleActif.formule.formuleRespectee }}</span>
                </div>
                <div class="rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-center text-sm text-[#0d3b56]">
                  Formule non respectée :
                  <span class="font-bold text-red-600">{{ controleActif.formule.formuleNonRespectee }}</span>
                </div>
              </div>

              <div v-if="controleActif.formule.comptesEnErreur.length" class="mt-4 overflow-x-auto rounded-lg shadow-sm">
                <table class="w-full text-left text-sm">
                  <thead>
                    <tr class="bg-amber-600 text-xs font-semibold uppercase text-white">
                      <th class="px-4 py-3">Compte</th>
                      <th class="px-4 py-3">Libellé</th>
                      <th class="px-4 py-3">Solde ouverture</th>
                      <th class="px-4 py-3">Mouvements</th>
                      <th class="px-4 py-3">Clôture attendue</th>
                      <th class="px-4 py-3">Clôture balance</th>
                      <th class="px-4 py-3">Écart</th>
                    </tr>
                  </thead>
                  <tbody class="bg-white">
                    <tr
                      v-for="compte in controleActif.formule.comptesEnErreur"
                      :key="compte.compte"
                      class="border-t border-gray-100"
                    >
                      <td class="px-4 py-3 font-medium text-[#0d3b56]">{{ compte.compte }}</td>
                      <td class="px-4 py-3 text-gray-500">{{ compte.libelle }}</td>
                      <td class="px-4 py-3 text-gray-500">{{ compte.soldeOuverture }}</td>
                      <td class="px-4 py-3 text-gray-500">{{ compte.mouvements }}</td>
                      <td class="px-4 py-3 text-gray-500">{{ compte.soldeClotureAttendu }}</td>
                      <td class="px-4 py-3 text-gray-500">{{ compte.soldeClotureBalance }}</td>
                      <td class="px-4 py-3 font-bold text-red-600">{{ compte.ecart }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </template>
      </template>
    </template>

    <p v-else class="mt-6 text-sm text-gray-500">Contenu à venir pour le contrôle de vraisemblance.</p>
  </div>
</template>
