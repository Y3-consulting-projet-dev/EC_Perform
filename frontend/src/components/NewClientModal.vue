<script setup>
import { reactive } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'created'])

const formesJuridiques = ['SARL', 'SA', 'SAS']

function emptyForm() {
  return {
    raisonSociale: '',
    secteurActivite: '',
    formeJuridique: 'SARL',
    rccm: '',
    compteContribuable: '',
    regimeFiscal: '',
    adresse: '',
    exerciceComptable: '',
    ville: '',
    contactPrincipal: '',
    email: '',
    telephone: '',
  }
}

const form = reactive(emptyForm())

function close() {
  emit('update:modelValue', false)
}

function handleSubmit() {
  emit('created', { ...form })
  Object.assign(form, emptyForm())
  close()
}
</script>

<template>
  <div
    v-if="modelValue"
    class="fixed inset-0 z-30 flex items-center justify-center bg-black/40 p-6"
    @click.self="close"
  >
    <div class="max-h-[90vh] w-full max-w-3xl overflow-hidden rounded-2xl bg-white shadow-xl">
    <div class="scrollbar-hide max-h-[90vh] overflow-y-auto p-8">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-bold text-[#0d3b56]">Nouveau client</h2>
        <div class="flex items-center gap-5">
          <button
            type="button"
            class="rounded-full bg-[#0d3b56] px-6 py-2 text-sm font-semibold text-white transition hover:bg-[#0a2f45]"
          >
            Nouvelle Mission
          </button>
          <button type="button" class="text-gray-400 hover:text-gray-600" aria-label="Fermer" @click="close">
            ✕
          </button>
        </div>
      </div>

      <form class="mt-4 space-y-5" @submit.prevent="handleSubmit">
        <div>
          <h3 class="text-sm font-bold tracking-wide text-[#0d3b56]">IDENTITE</h3>
          <div class="mt-3 grid grid-cols-2 gap-6">
            <div>
              <label for="raisonSociale" class="mb-1 block text-xs font-semibold text-[#0d3b56]">Raison sociale</label>
              <input
                id="raisonSociale"
                v-model="form.raisonSociale"
                type="text"
                required
                placeholder="EX. : SARL KOUASSI"
                class="w-full rounded-xl border border-[#7cb342] bg-[#eef1ec] px-4 py-2.5 text-sm text-[#0d3b56] placeholder-gray-400 outline-none focus:ring-2 focus:ring-[#7cb342]"
              />
            </div>
            <div>
              <label for="secteurActivite" class="mb-1 block text-xs font-semibold text-[#0d3b56]">Secteur d'activité</label>
              <input
                id="secteurActivite"
                v-model="form.secteurActivite"
                type="text"
                required
                placeholder="Commerce"
                class="w-full rounded-xl border border-[#7cb342] bg-[#eef1ec] px-4 py-2.5 text-sm text-[#0d3b56] placeholder-gray-400 outline-none focus:ring-2 focus:ring-[#7cb342]"
              />
            </div>
          </div>

          <div class="mt-4">
            <p class="mb-1 text-sm font-bold text-[#0d3b56]">Forme juridique</p>
            <div class="flex gap-2">
              <button
                v-for="forme in formesJuridiques"
                :key="forme"
                type="button"
                class="rounded-full px-4 py-1.5 text-sm font-semibold transition"
                :class="
                  form.formeJuridique === forme
                    ? 'bg-[#0d3b56] text-white'
                    : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                "
                @click="form.formeJuridique = forme"
              >
                {{ forme }}
              </button>
            </div>
          </div>
        </div>

        <div>
          <h3 class="text-sm font-bold tracking-wide text-[#0d3b56]">IMMATRICULATION FISCAL</h3>
          <div class="mt-3 grid grid-cols-3 gap-6">
            <div>
              <label for="rccm" class="mb-1 block text-xs font-semibold text-[#0d3b56]">N° RCCM</label>
              <input
                id="rccm"
                v-model="form.rccm"
                type="text"
                required
                placeholder="CI-ABJ-2024"
                class="w-full rounded-xl border border-[#7cb342] bg-[#eef1ec] px-4 py-2.5 text-sm text-[#0d3b56] placeholder-gray-400 outline-none focus:ring-2 focus:ring-[#7cb342]"
              />
            </div>
            <div>
              <label for="compteContribuable" class="mb-1 block text-xs font-semibold text-[#0d3b56]">N° compte contribuable</label>
              <input
                id="compteContribuable"
                v-model="form.compteContribuable"
                type="text"
                placeholder="2400123K"
                class="w-full rounded-xl border border-[#7cb342] bg-[#eef1ec] px-4 py-2.5 text-sm text-[#0d3b56] placeholder-gray-400 outline-none focus:ring-2 focus:ring-[#7cb342]"
              />
            </div>
            <div>
              <label for="regimeFiscal" class="mb-1 block text-xs font-semibold text-[#0d3b56]">Régime fiscal</label>
              <input
                id="regimeFiscal"
                v-model="form.regimeFiscal"
                type="text"
                placeholder="Réel normal"
                class="w-full rounded-xl border border-[#7cb342] bg-[#eef1ec] px-4 py-2.5 text-sm text-[#0d3b56] placeholder-gray-400 outline-none focus:ring-2 focus:ring-[#7cb342]"
              />
            </div>
          </div>
        </div>

        <div>
          <h3 class="text-sm font-bold tracking-wide text-[#0d3b56]">ADRESSE ET CONTACT</h3>
          <div class="mt-3 grid grid-cols-3 gap-6">
            <div>
              <label for="adresse" class="mb-1 block text-xs font-semibold text-[#0d3b56]">Adresse</label>
              <input
                id="adresse"
                v-model="form.adresse"
                type="text"
                placeholder="01 BP 453 Abidjan 01"
                class="w-full rounded-xl border border-[#7cb342] bg-[#eef1ec] px-4 py-2.5 text-sm text-[#0d3b56] placeholder-gray-400 outline-none focus:ring-2 focus:ring-[#7cb342]"
              />
            </div>
            <div>
              <label for="exerciceComptable" class="mb-1 block text-xs font-semibold text-[#0d3b56]">Exercice comptable</label>
              <input
                id="exerciceComptable"
                v-model="form.exerciceComptable"
                type="text"
                placeholder="31/12 - 31/12"
                class="w-full rounded-xl border border-[#7cb342] bg-[#eef1ec] px-4 py-2.5 text-sm text-[#0d3b56] placeholder-gray-400 outline-none focus:ring-2 focus:ring-[#7cb342]"
              />
            </div>
            <div>
              <label for="ville" class="mb-1 block text-xs font-semibold text-[#0d3b56]">Ville</label>
              <input
                id="ville"
                v-model="form.ville"
                type="text"
                required
                placeholder="Abidjan"
                class="w-full rounded-xl border border-[#7cb342] bg-[#eef1ec] px-4 py-2.5 text-sm text-[#0d3b56] placeholder-gray-400 outline-none focus:ring-2 focus:ring-[#7cb342]"
              />
            </div>
          </div>

          <div class="mt-4 grid grid-cols-3 gap-6">
            <div>
              <label for="contactPrincipal" class="mb-1 block text-xs font-semibold text-[#0d3b56]">Contact principal</label>
              <input
                id="contactPrincipal"
                v-model="form.contactPrincipal"
                type="text"
                placeholder="Nom et fonction"
                class="w-full rounded-xl border border-[#7cb342] bg-[#eef1ec] px-4 py-2.5 text-sm text-[#0d3b56] placeholder-gray-400 outline-none focus:ring-2 focus:ring-[#7cb342]"
              />
            </div>
            <div>
              <label for="clientEmail" class="mb-1 block text-xs font-semibold text-[#0d3b56]">Email</label>
              <input
                id="clientEmail"
                v-model="form.email"
                type="email"
                placeholder="contact@client.ci"
                class="w-full rounded-xl border border-[#7cb342] bg-[#eef1ec] px-4 py-2.5 text-sm text-[#0d3b56] placeholder-gray-400 outline-none focus:ring-2 focus:ring-[#7cb342]"
              />
            </div>
            <div>
              <label for="telephone" class="mb-1 block text-xs font-semibold text-[#0d3b56]">Téléphone</label>
              <input
                id="telephone"
                v-model="form.telephone"
                type="tel"
                class="w-full rounded-xl border border-[#7cb342] bg-[#eef1ec] px-4 py-2.5 text-sm text-[#0d3b56] placeholder-gray-400 outline-none focus:ring-2 focus:ring-[#7cb342]"
              />
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-3 pt-2">
          <button
            type="button"
            class="rounded-full border border-gray-300 px-6 py-2.5 text-sm font-semibold text-gray-600 transition hover:bg-gray-50"
            @click="close"
          >
            Annuler
          </button>
          <button
            type="submit"
            class="rounded-full bg-[#7cb342] px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-[#6ca038]"
          >
            Enregistrer
          </button>
        </div>
      </form>
    </div>
    </div>
  </div>
</template>

<style scoped>
.scrollbar-hide {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
</style>
