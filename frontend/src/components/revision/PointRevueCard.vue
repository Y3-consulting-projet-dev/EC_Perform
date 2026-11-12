<script setup>
import { computed, inject, ref } from 'vue'
import { ETAPES, fileUrl, formatDateTime } from '../../composables/useCycleRevision'

const props = defineProps({
  point: { type: Object, required: true },
  entry: { type: Object, required: true },
  canRespond: { type: Boolean, default: false },
  canChangeStatus: { type: Boolean, default: false },
  showGoTo: { type: Boolean, default: true },
})

const nav = inject('revisionNav')

const etape = computed(() => ETAPES.find((e) => e.code === props.point.cible.etape))

const cibleLabel = computed(() => {
  const { ptEtape, onglet, cellule } = props.point.cible
  const parts = [`${props.point.cible.etape} · ${etape.value?.label ?? ''}`]
  if (ptEtape) parts.push(`PT ${ptEtape}`)
  if (onglet) parts.push(onglet)
  if (cellule) parts.push(cellule)
  return parts.join(' / ')
})

const roundLabel = computed(() => {
  const n = props.point.roundCount
  if (props.point.statut === 'cleared') return n ? `Traité en ${n} retour${n > 1 ? 's' : ''}` : 'Traité sans retour'
  if (n === 0) return 'Pas encore renvoyé au collaborateur'
  return n === 1 ? '1er retour sur ce point' : `${n}e retour sur ce point`
})

const texte = ref('')
const ptRef = ref('')
const fichiers = ref([])
const fileInput = ref(null)
const busy = ref(false)
const error = ref('')

function onFiles(event) {
  fichiers.value = [...event.target.files]
}

async function envoyer() {
  busy.value = true
  error.value = ''
  try {
    await props.entry.repondre(props.point.id, texte.value, ptRef.value, fichiers.value)
    texte.value = ''
    ptRef.value = ''
    fichiers.value = []
    if (fileInput.value) fileInput.value.value = ''
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

async function changerStatut(statut) {
  busy.value = true
  error.value = ''
  try {
    await props.entry.changerStatutPoint(props.point.id, statut)
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div
    class="rounded-xl border bg-white px-4 py-3.5"
    :class="point.alerte && point.statut === 'ouvert' ? 'border-[#f0c9c5]' : 'border-gray-200'"
  >
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div class="flex flex-wrap items-center gap-2">
        <span class="rounded-md bg-[#eaf1f7] px-2 py-0.5 text-[11px] font-bold text-[#2c6e8f]">REF {{ point.ref }}</span>
        <span class="text-xs font-bold text-[#0d3b56]">{{ point.auteur.nom }}</span>
        <span class="text-[11px] text-gray-400">· {{ point.niveauLabel }} · {{ formatDateTime(point.createdAt) }}</span>
      </div>
      <div class="flex items-center gap-2">
        <span
          v-if="point.alerte && point.statut === 'ouvert'"
          class="rounded-full bg-[#fbe6e4] px-2.5 py-0.5 text-[11px] font-bold text-[#c1483f]"
        >
          À traiter en séance de travail
        </span>
        <span
          class="rounded-full px-2.5 py-0.5 text-[11px] font-bold"
          :class="point.statut === 'ouvert' ? 'bg-[#fbeee0] text-[#c9862c]' : 'bg-[#e6f3ec] text-[#2f9e6b]'"
        >
          {{ point.statut === 'ouvert' ? 'Ouvert' : 'Cleared' }}
        </span>
      </div>
    </div>

    <p class="mt-2 whitespace-pre-line text-[13px] leading-relaxed text-[#1a2634]">{{ point.corps }}</p>

    <div
      v-for="reponse in point.reponses"
      :key="reponse.id"
      class="mt-2 rounded-r-md border-l-[3px] border-gray-200 bg-[#fafbfc] px-3 py-2 text-[13px]"
    >
      <p class="text-[11px] font-bold text-[#2f9e6b]">
        Réponse de {{ reponse.auteur.nom }} · {{ formatDateTime(reponse.le) }}
      </p>
      <p v-if="reponse.texte" class="whitespace-pre-line">{{ reponse.texte }}</p>
      <p v-if="reponse.ptRef" class="mt-1 text-xs text-gray-500">Feuille de travail : {{ reponse.ptRef }}</p>
      <p v-for="piece in reponse.pieces" :key="piece.fileUrl" class="mt-1 text-xs">
        📎 <a :href="fileUrl(piece.fileUrl)" target="_blank" class="font-semibold text-[#2c6e8f] hover:underline">{{ piece.fileName }}</a>
      </p>
    </div>

    <form
      v-if="canRespond && point.statut === 'ouvert'"
      class="mt-3 space-y-2 rounded-lg bg-[#f4f6f8] p-3"
      @submit.prevent="envoyer"
    >
      <textarea
        v-model="texte"
        rows="2"
        placeholder="Votre réponse au point de revue..."
        class="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#7cb342]"
      ></textarea>
      <div class="flex flex-wrap items-center gap-2">
        <input
          v-model="ptRef"
          type="text"
          placeholder="Réf. feuille de travail (ex. 4d / Balance âgée / B6)"
          class="min-w-56 flex-1 rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs outline-none focus:ring-2 focus:ring-[#7cb342]"
        />
        <input ref="fileInput" type="file" multiple class="text-xs" @change="onFiles" />
        <button
          type="submit"
          :disabled="busy || (!texte.trim() && !fichiers.length)"
          class="rounded-md bg-[#0d3b56] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#0a2f45] disabled:opacity-50"
        >
          Répondre
        </button>
      </div>
    </form>

    <div class="mt-3 flex flex-wrap items-center justify-between gap-2">
      <span class="text-[11px]" :class="point.alerte ? 'font-bold text-[#c1483f]' : 'text-gray-400'">
        {{ roundLabel }} · Cible : {{ cibleLabel }}
      </span>
      <div class="flex gap-2">
        <button
          v-if="showGoTo && etape"
          type="button"
          class="rounded-md border border-gray-200 bg-white px-3 py-1 text-[11px] font-semibold text-[#0d3b56] hover:bg-gray-50"
          @click="nav.goToStep(etape.stepId)"
        >
          Voir la feuille de travail
        </button>
        <template v-if="canChangeStatus">
          <button
            v-if="point.statut === 'ouvert'"
            type="button"
            :disabled="busy"
            class="rounded-md bg-[#2f9e6b] px-3 py-1 text-[11px] font-semibold text-white hover:opacity-90 disabled:opacity-50"
            @click="changerStatut('cleared')"
          >
            ✓ Marquer Cleared
          </button>
          <button
            v-else
            type="button"
            :disabled="busy"
            class="rounded-md border border-gray-200 bg-white px-3 py-1 text-[11px] font-semibold text-[#c9862c] hover:bg-gray-50 disabled:opacity-50"
            @click="changerStatut('ouvert')"
          >
            Rouvrir
          </button>
        </template>
      </div>
    </div>
    <p v-if="error" class="mt-2 text-xs text-red-600">{{ error }}</p>
  </div>
</template>
