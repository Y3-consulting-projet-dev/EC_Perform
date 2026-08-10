<script setup>
import { ref, watch } from 'vue'
import MissionWorkspaceModal from './MissionWorkspaceModal.vue'
import NewMissionModal from './NewMissionModal.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  client: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue'])

const activeTab = ref('informations')
const showNewMissionModal = ref(false)
const showMissionWorkspace = ref(false)
const selectedMission = ref(null)

function openMission(mission) {
  selectedMission.value = mission
  showMissionWorkspace.value = true
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) activeTab.value = 'informations'
  },
)

function close() {
  emit('update:modelValue', false)
}

function handleMissionCreated(mission) {
  if (!props.client) return
  props.client.missions = [...(props.client.missions ?? []), mission]
  props.client.missionsEnCours = (props.client.missionsEnCours ?? 0) + 1
  activeTab.value = 'missions'
}

const statutStyles = {
  'En cours': 'bg-sky-100 text-sky-700',
  Terminée: 'bg-[#7cb342] text-white',
}

const infoRows = [
  [
    { label: 'Raison sociale', key: 'raisonSociale' },
    { label: 'Forme juridique', key: 'formeJuridique' },
    { label: "Secteur d'activité", key: 'secteurActivite' },
  ],
  [
    { label: 'N° RCCM', key: 'rccm' },
    { label: 'N° compte contribuable', key: 'compteContribuable' },
    { label: 'Régime fiscal', key: 'regimeFiscal' },
  ],
  [
    { label: 'Adresse', key: 'adresse' },
    { label: 'Ville', key: 'ville' },
    { label: 'Exercice comptable', key: 'exerciceComptable' },
  ],
  [
    { label: 'Contact principal', key: 'contactPrincipal' },
    { label: 'Email', key: 'email' },
    { label: 'Téléphone', key: 'telephone' },
  ],
]
</script>

<template>
  <div
    v-if="modelValue && client"
    class="fixed inset-0 z-30 flex items-center justify-center bg-black/40 p-6"
    @click.self="close"
  >
    <div class="max-h-[90vh] w-full max-w-3xl overflow-hidden rounded-2xl bg-white shadow-xl">
      <div class="scrollbar-hide max-h-[90vh] overflow-y-auto p-8">
        <div class="flex items-start justify-between">
          <p class="text-xs font-semibold text-gray-400">Liste des clients</p>
          <button type="button" class="text-gray-400 hover:text-gray-600" aria-label="Fermer" @click="close">
            ✕
          </button>
        </div>

        <div class="mt-1 flex items-center gap-3">
          <h2 class="text-lg font-bold text-[#0d3b56]">{{ client.raisonSociale }}</h2>
          <span class="rounded-full bg-[#e2f0e7] px-3 py-1 text-xs font-semibold text-[#4b7a5c]">
            {{ client.missionsEnCours ?? 0 }} mission{{ (client.missionsEnCours ?? 0) > 1 ? 's' : '' }} en cours
          </span>
        </div>
        <p class="mt-1 text-sm text-gray-500">
          {{ client.secteurActivite }} · {{ client.ville }} · RCCM {{ client.rccm }}
        </p>

        <div class="mt-4 flex items-center gap-3">
          <button
            type="button"
            class="rounded-full border border-gray-300 px-5 py-2 text-sm font-semibold text-gray-600 transition hover:bg-gray-50"
          >
            Modifier
          </button>
          <button
            type="button"
            class="rounded-full bg-[#0d3b56] px-5 py-2 text-sm font-semibold text-white transition hover:bg-[#0a2f45]"
            @click="showNewMissionModal = true"
          >
            Nouvelle mission
          </button>
        </div>

        <div class="mt-6 flex gap-6 border-b border-gray-100">
          <button
            type="button"
            class="border-b-2 pb-3 text-sm font-semibold transition"
            :class="
              activeTab === 'informations'
                ? 'border-[#7cb342] text-[#0d3b56]'
                : 'border-transparent text-gray-400 hover:text-gray-600'
            "
            @click="activeTab = 'informations'"
          >
            Informations
          </button>
          <button
            type="button"
            class="border-b-2 pb-3 text-sm font-semibold transition"
            :class="
              activeTab === 'missions'
                ? 'border-[#7cb342] text-[#0d3b56]'
                : 'border-transparent text-gray-400 hover:text-gray-600'
            "
            @click="activeTab = 'missions'"
          >
            Missions
          </button>
        </div>

        <div v-if="activeTab === 'informations'" class="mt-6 space-y-6">
          <div v-for="(row, index) in infoRows" :key="index" class="grid grid-cols-3 gap-6">
            <div v-for="field in row" :key="field.key">
              <p class="text-sm font-bold text-[#0d3b56]">{{ field.label }}</p>
              <p class="mt-1 text-sm text-gray-600">{{ client[field.key] || '—' }}</p>
            </div>
          </div>
        </div>

        <div v-else class="mt-6">
          <table v-if="client.missions?.length" class="w-full text-left text-sm">
            <thead>
              <tr class="text-xs text-gray-400">
                <th class="pb-2 font-semibold">Exercice</th>
                <th class="pb-2 font-semibold">Phase</th>
                <th class="pb-2 font-semibold">Statut</th>
                <th class="pb-2 font-semibold">Rapport</th>
                <th class="pb-2 font-semibold">Action</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="mission in client.missions" :key="mission.exercice" class="border-t border-gray-100">
                <td class="py-3 font-medium text-[#0d3b56]">{{ mission.exercice }}</td>
                <td class="py-3 text-gray-500">{{ mission.phase }}</td>
                <td class="py-3">
                  <span class="rounded-full px-3 py-1 text-xs font-semibold" :class="statutStyles[mission.statut]">
                    {{ mission.statut }}
                  </span>
                </td>
                <td class="py-3">
                  <span
                    v-if="mission.rapport === 'Avec observations'"
                    class="rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-600"
                  >
                    {{ mission.rapport }}
                  </span>
                  <span v-else-if="mission.rapport" class="text-gray-500">{{ mission.rapport }}</span>
                  <span v-else class="text-gray-300">—</span>
                </td>
                <td class="py-3">
                  <button
                    type="button"
                    class="rounded-full bg-[#7cb342] px-5 py-1.5 text-xs font-semibold text-white transition hover:bg-[#6ca038]"
                    @click="openMission(mission)"
                  >
                    Ouvrir
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-else class="text-sm text-gray-500">Aucune mission pour ce client.</p>
        </div>
      </div>
    </div>

    <NewMissionModal v-model="showNewMissionModal" :client="client" @created="handleMissionCreated" />
    <MissionWorkspaceModal v-model="showMissionWorkspace" :client="client" :mission="selectedMission" />
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
