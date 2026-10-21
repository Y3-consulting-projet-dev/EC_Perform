<script setup>
import { computed, ref } from 'vue'
import CycleRevisionLayout from '../revision/CycleRevisionLayout.vue'
import { apiFetch, fileUrl, formatDateTime, newId } from '../../composables/useCycleRevision'
import { useRevisionStep } from '../../composables/useRevisionStep'

const props = defineProps({
  mission: { type: Object, required: true },
})

const { nav, summary, entry, revision, canEdit } = useRevisionStep(props)

const STATUTS = ['Reçue', 'En attente', 'Manquante']
const statutStyles = {
  Reçue: 'bg-[#e6f3ec] text-[#2f9e6b]',
  'En attente': 'bg-[#fbeee0] text-[#c9862c]',
  Manquante: 'bg-[#fbe6e4] text-[#c1483f]',
}

function save() {
  entry.value.scheduleSave('justification')
}

const constatsOuverts = computed(() => (revision.value?.constats ?? []).filter((c) => c.statut === 'Ouvert'))
const aCompleter = computed(() => revision.value?.conclusion?.decision === 'completer')

function ajouterPiece(r) {
  r.justification.pieces.push({ id: newId(), libelle: '', source: '', statut: 'En attente', fileName: null, fileUrl: null, ptEtape: null })
  save()
}

function supprimerPiece(r, index) {
  r.justification.pieces.splice(index, 1)
  save()
}

const busy = ref('')
const error = ref('')

async function deposerFichier(piece, event) {
  const fichier = event.target.files[0]
  event.target.value = ''
  if (!fichier) return
  busy.value = piece.id
  error.value = ''
  try {
    const form = new FormData()
    form.append('fichier', fichier)
    const result = await apiFetch(`/missions/${props.mission.id}/cycles/${revision.value.code}/revision/pieces`, {
      method: 'POST',
      form,
    })
    Object.assign(piece, result, { statut: 'Reçue', libelle: piece.libelle || result.fileName })
    save()
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = ''
  }
}

// Le PT (4b / 4d) est exporté en .xlsx et référencé comme pièce probante, figé à sa version.
async function rattacherPapier(r, etape) {
  busy.value = etape
  error.value = ''
  try {
    const base = `/missions/${props.mission.id}/cycles/${r.code}/papiers/${etape}`
    const papier = await apiFetch(base)
    const exported = await apiFetch(`${base}/export`, { method: 'POST' })
    r.justification.pieces.push({
      id: newId(),
      libelle: `${papier.titre} (v${exported.version})`,
      source: `Papier de travail ${etape}`,
      statut: 'Reçue',
      fileName: exported.fileName,
      fileUrl: exported.fileUrl,
      ptEtape: etape,
    })
    save()
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = ''
  }
}
</script>

<template>
  <CycleRevisionLayout
    :entry="entry"
    :summary="summary"
    etape="4c"
    title="Justification du solde"
    subtitle="Rassembler les pièces probantes et couvrir les assertions d'audit."
  >
    <template #default="{ revision: r }">
      <div v-if="aCompleter && constatsOuverts.length" class="rounded-xl border border-[#f1d9b5] bg-[#fdf6ec] p-4">
        <p class="text-xs font-bold uppercase tracking-wide text-[#c9862c]">
          Justification à compléter — points ouverts en 4e ({{ constatsOuverts.length }})
        </p>
        <ul class="mt-2 space-y-1 text-[13px]">
          <li v-for="constat in constatsOuverts" :key="constat.id">
            <span class="font-semibold">{{ constat.famille }}</span> · {{ constat.constat }}
            <span class="text-gray-500">— {{ constat.recommandation }}</span>
          </li>
        </ul>
        <button type="button" class="mt-2 text-xs font-semibold text-[#2c6e8f] hover:underline" @click="nav.goToStep('constats-risques')">
          Voir les constats →
        </button>
      </div>

      <div class="rounded-xl bg-white p-5 shadow-sm">
        <h3 class="text-sm font-bold text-[#0d3b56]">Assertions d'audit à couvrir</h3>
        <ul class="mt-2 divide-y divide-gray-100">
          <li v-for="assertion in r.justification.assertions" :key="assertion.cle" class="flex items-center justify-between gap-3 py-2.5">
            <label class="flex items-center text-[#1a2634] gap-2.5 text-[13px]">
              <input
                v-model="assertion.coche"
                type="checkbox"
                :disabled="!canEdit"
                class="h-4 w-4 accent-[#2f9e6b]"
                @change="save"
              />
              {{ assertion.libelle }}
            </label>
            <span v-if="assertion.le" class="text-[11px] text-gray-400">
              {{ assertion.coche ? 'Couverte' : 'Décochée' }} le {{ formatDateTime(assertion.le) }} par {{ assertion.par?.nom }}
            </span>
          </li>
        </ul>
      </div>

      <div class="rounded-xl bg-white shadow-sm">
        <div class="flex flex-wrap items-center justify-between gap-2 px-5 pt-4">
          <h3 class="text-sm font-bold text-[#0d3b56]">Pièces probantes</h3>
          <div v-if="canEdit" class="flex flex-wrap gap-2">
            <button
              v-for="etape in ['4b', '4d']"
              :key="etape"
              type="button"
              :disabled="!!busy"
              class="rounded-md border border-[#c3dcbc] bg-white px-3 py-1.5 text-xs font-semibold text-[#1d6a3a] hover:bg-[#eef3ec] disabled:opacity-50"
              @click="rattacherPapier(r, etape)"
            >
              {{ busy === etape ? 'Export…' : `+ Rattacher le PT ${etape}` }}
            </button>
            <button
              type="button"
              class="rounded-md bg-[#0d3b56] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#0a2f45]"
              @click="ajouterPiece(r)"
            >
              + Ajouter une pièce
            </button>
          </div>
        </div>
        <p v-if="error" class="px-5 pt-2 text-xs text-red-600">{{ error }}</p>
        <div class="mt-3 overflow-x-auto">
          <table class="w-full text-left text-[12.5px]">
            <thead>
              <tr class="bg-[#eef1f4] text-[11px] uppercase tracking-wide text-gray-500">
                <th class="px-3 py-2.5">Pièce probante</th>
                <th class="px-3 py-2.5">Source</th>
                <th class="px-3 py-2.5">Statut</th>
                <th class="px-3 py-2.5">Fichier</th>
                <th v-if="canEdit" class="px-3 py-2.5"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(piece, index) in r.justification.pieces" :key="piece.id" class="border-t border-gray-100">
                <td class="px-3 py-1.5">
                  <input
                    v-model="piece.libelle"
                    :disabled="!canEdit"
                    type="text"
                    placeholder="Ex. Balance âgée clients au 31/12"
                    class="w-full text-[#1a2634] rounded-md border border-gray-200 px-2 py-1 text-xs outline-none focus:ring-2 focus:ring-[#7cb342] disabled:border-transparent disabled:bg-transparent"
                    @input="save"
                  />
                </td>
                <td class="px-3 py-1.5">
                  <input
                    v-model="piece.source"
                    :disabled="!canEdit"
                    type="text"
                    placeholder="ERP client, envoi cabinet..."
                    class="w-full text-[#1a2634] rounded-md border border-gray-200 px-2 py-1 text-xs outline-none focus:ring-2 focus:ring-[#7cb342] disabled:border-transparent disabled:bg-transparent"
                    @input="save"
                  />
                </td>
                <td class="px-3 py-1.5">
                  <select
                    v-if="canEdit"
                    v-model="piece.statut"
                    class="rounded-full border-0 px-2.5 py-1 text-[11px] font-bold outline-none"
                    :class="statutStyles[piece.statut]"
                    @change="save"
                  >
                    <option v-for="s in STATUTS" :key="s" :value="s">{{ s }}</option>
                  </select>
                  <span v-else class="rounded-full px-2.5 py-1 text-[11px] font-bold" :class="statutStyles[piece.statut]">{{ piece.statut }}</span>
                </td>
                <td class="px-3 py-1.5 text-xs">
                  <a v-if="piece.fileUrl" :href="fileUrl(piece.fileUrl)" target="_blank" class="font-semibold text-[#2c6e8f] hover:underline">
                    📎 {{ piece.fileName }}
                  </a>
                  <label v-else-if="canEdit" class="cursor-pointer font-semibold text-gray-500 hover:text-[#0d3b56]">
                    {{ busy === piece.id ? 'Envoi…' : 'Joindre…' }}
                    <input type="file" class="hidden" @change="deposerFichier(piece, $event)" />
                  </label>
                  <span v-else class="text-gray-400">—</span>
                </td>
                <td v-if="canEdit" class="px-3 py-1.5 text-right">
                  <button type="button" class="text-gray-400 hover:text-[#c1483f]" aria-label="Supprimer la pièce" @click="supprimerPiece(r, index)">
                    ✕
                  </button>
                </td>
              </tr>
              <tr v-if="!r.justification.pieces.length">
                <td colspan="5" class="px-3 py-4 text-center text-gray-400">Aucune pièce probante rattachée.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="rounded-xl bg-white p-5 shadow-sm">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h3 class="text-sm font-bold text-[#0d3b56]">Commentaire du préparateur</h3>
          <span v-if="r.justification.commentaire.le" class="text-[11px] text-gray-400">
            Modifié le {{ formatDateTime(r.justification.commentaire.le) }} par {{ r.justification.commentaire.par?.nom }}
          </span>
        </div>
        <textarea
          v-model="r.justification.commentaire.texte"
          :disabled="!canEdit"
          rows="4"
          class="mt-3 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-[#1a2634] outline-none focus:ring-2 focus:ring-[#7cb342] disabled:bg-gray-50"
          @input="save"
        ></textarea>
      </div>

      <div class="flex justify-end">
        <button
          type="button"
          class="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-semibold text-[#0d3b56] hover:bg-gray-50"
          @click="nav.goToStep('controle-detaille')"
        >
          Passer aux contrôles détaillés →
        </button>
      </div>
    </template>
  </CycleRevisionLayout>
</template>
