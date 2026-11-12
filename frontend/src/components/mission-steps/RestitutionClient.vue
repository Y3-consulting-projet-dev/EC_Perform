<script setup>
import { computed, onMounted, ref } from 'vue'
import { formatDateTime } from '../../composables/useCycleRevision'
import { api } from '../../composables/useRapport'

// Phase 6 – Restitution client : réunion de présentation des travaux au client (date, lieu,
// participants) et, pour chaque constat de la Phase 4, le commentaire du client et la réponse du
// management. Le rapport final reprend ces éléments tels que saisis.
const props = defineProps({
  mission: { type: Object, required: true },
})

const restitution = ref(null)
const employes = ref([])
const form = ref(null)
const initial = ref('')
const chargement = ref(false)
const enregistrement = ref(false)
const erreur = ref('')
const message = ref('')
const ajout = ref('')

const base = computed(() => `/missions/${props.mission.id}/restitution`)
const modifie = computed(() => form.value && JSON.stringify(form.value) !== initial.value)
const nomEmploye = (id) => {
  const e = employes.value.find((x) => x.id === id)
  return e ? `${e.prenoms} ${e.nom}` : id
}
const employesDisponibles = computed(() =>
  employes.value.filter((e) => !form.value?.reunion.participantsCabinet.includes(e.id)),
)
const SEVERITES = { Élevé: 'bg-red-50 text-red-600', Moyen: 'bg-[#fbeee0] text-[#c9862c]', Faible: 'bg-[#eef6e6] text-[#5a8a2c]' }

function appliquer(data) {
  restitution.value = data
  const reunion = data.reunion ?? {}
  const commentaires = {}
  for (const c of data.constats) {
    const existant = data.commentaires?.[c.id] ?? {}
    commentaires[c.id] = {
      commentaireClient: existant.commentaireClient ?? '',
      reponseManagement: existant.reponseManagement ?? '',
    }
  }
  form.value = {
    reunion: {
      date: reunion.date ?? '',
      lieu: reunion.lieu ?? '',
      participantsCabinet: (reunion.participantsCabinet ?? []).map((p) => p.id).filter(Boolean),
      participantsClient: (reunion.participantsClient ?? []).map((p) => ({ nom: p.nom, fonction: p.fonction })),
    },
    commentaires,
  }
  initial.value = JSON.stringify(form.value)
}

async function charger() {
  chargement.value = true
  erreur.value = ''
  try {
    const [data, liste] = await Promise.all([api(base.value), api('/employees')])
    employes.value = liste
    appliquer(data)
  } catch (e) {
    erreur.value = e.message
  } finally {
    chargement.value = false
  }
}

async function enregistrer() {
  enregistrement.value = true
  erreur.value = ''
  message.value = ''
  try {
    appliquer(
      await api(base.value, {
        method: 'PUT',
        body: { ...form.value, version: restitution.value.version },
      }),
    )
    message.value = 'Restitution enregistrée. Régénérez le rapport final pour y intégrer les commentaires.'
  } catch (e) {
    erreur.value = e.message
  } finally {
    enregistrement.value = false
  }
}

function ajouterParticipant() {
  if (ajout.value) form.value.reunion.participantsCabinet.push(ajout.value)
  ajout.value = ''
}

onMounted(charger)
</script>

<template>
  <div class="mt-4 space-y-4">
    <div class="rounded-xl bg-white p-5 shadow-sm">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 class="text-sm font-bold text-[#0d3b56]">Restitution client</h3>
          <p class="text-xs text-gray-400">
            Réunion de restitution et commentaires du client sur chaque constat, repris dans le rapport final.
          </p>
        </div>
        <div class="flex items-center gap-3">
          <span v-if="modifie" class="text-xs font-semibold text-[#c9862c]">Modifications non enregistrées</span>
          <button
            type="button"
            :disabled="!restitution?.modifiable || !modifie || enregistrement"
            class="rounded-lg bg-[#0d3b56] px-4 py-2 text-sm font-semibold text-white hover:bg-[#0a2f45] disabled:opacity-50"
            @click="enregistrer"
          >
            {{ enregistrement ? 'Enregistrement...' : 'Enregistrer' }}
          </button>
        </div>
      </div>

      <p v-if="chargement && !form" class="mt-3 text-sm text-gray-400">Chargement...</p>
      <p v-if="erreur" class="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">{{ erreur }}</p>
      <p v-if="message" class="mt-3 rounded-lg bg-[#eef6e6] px-3 py-2 text-xs text-[#5a8a2c]">{{ message }}</p>
      <p v-if="restitution && !restitution.modifiable" class="mt-3 rounded-lg bg-[#fbeee0] px-3 py-2 text-xs text-[#c9862c]">
        {{ restitution.raisonLectureSeule }}
      </p>
      <p v-if="restitution?.updatedAt" class="mt-2 text-xs text-gray-400">
        Dernière mise à jour le {{ formatDateTime(restitution.updatedAt) }} par {{ restitution.updatedBy?.nom }}
      </p>

      <fieldset v-if="form" :disabled="!restitution.modifiable" class="mt-4 space-y-4">
        <div class="grid gap-4 md:grid-cols-3">
          <label class="block text-xs font-semibold text-gray-600">
            Date de la réunion
            <input v-model="form.reunion.date" type="date" class="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
          </label>
          <label class="block text-xs font-semibold text-gray-600 md:col-span-2">
            Lieu
            <input v-model="form.reunion.lieu" type="text" placeholder="ex. Siège du client, visioconférence" class="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
          </label>
        </div>

        <div class="grid gap-4 md:grid-cols-2">
          <div>
            <p class="text-xs font-bold text-[#0d3b56]">Participants du cabinet</p>
            <div class="mt-2 flex flex-wrap gap-2">
              <span
                v-for="(id, i) in form.reunion.participantsCabinet"
                :key="id"
                class="flex items-center gap-1 rounded-full bg-[#eef2f6] px-2.5 py-1 text-xs text-[#0d3b56]"
              >
                {{ nomEmploye(id) }}
                <button type="button" class="text-gray-400 hover:text-red-500" aria-label="Retirer" @click="form.reunion.participantsCabinet.splice(i, 1)">✕</button>
              </span>
            </div>
            <div class="mt-2 flex gap-2">
              <select v-model="ajout" class="flex-1 rounded-lg border border-gray-200 px-3 py-1.5 text-xs">
                <option value="">Ajouter un collaborateur...</option>
                <option v-for="e in employesDisponibles" :key="e.id" :value="e.id">{{ e.prenoms }} {{ e.nom }} · {{ e.grade }}</option>
              </select>
              <button type="button" :disabled="!ajout" class="rounded-lg bg-[#2c6e8f] px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50" @click="ajouterParticipant">
                Ajouter
              </button>
            </div>
          </div>
          <div>
            <div class="flex items-center justify-between">
              <p class="text-xs font-bold text-[#0d3b56]">Participants du client</p>
              <button type="button" class="text-xs font-semibold text-[#2c6e8f] hover:underline" @click="form.reunion.participantsClient.push({ nom: '', fonction: '' })">
                + Ajouter
              </button>
            </div>
            <div v-for="(p, i) in form.reunion.participantsClient" :key="i" class="mt-2 flex gap-2">
              <input v-model="p.nom" type="text" placeholder="Nom" class="flex-1 rounded-lg border border-gray-200 px-3 py-1.5 text-xs" />
              <input v-model="p.fonction" type="text" placeholder="Fonction" class="flex-1 rounded-lg border border-gray-200 px-3 py-1.5 text-xs" />
              <button type="button" class="text-xs text-red-500 hover:underline" @click="form.reunion.participantsClient.splice(i, 1)">Retirer</button>
            </div>
          </div>
        </div>
      </fieldset>
    </div>

    <div v-if="form" class="rounded-xl bg-white p-5 shadow-sm">
      <h3 class="text-sm font-bold text-[#0d3b56]">Commentaires sur les constats</h3>
      <p class="text-xs text-gray-400">Un champ vide n'apparaît pas dans le rapport.</p>
      <p v-if="!restitution.constats.length" class="mt-3 text-sm text-gray-400">Aucun constat saisi en Phase 4.</p>
      <fieldset :disabled="!restitution.modifiable" class="mt-3 space-y-3">
        <div v-for="c in restitution.constats" :key="c.id" class="rounded-lg border border-gray-100 p-4">
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-xs font-bold text-[#0d3b56]">{{ c.cycleCode }} – {{ c.cycleLibelle }}</span>
            <span class="text-xs text-gray-400">· {{ c.famille }}</span>
            <span class="rounded-full px-2 py-0.5 text-[11px] font-bold" :class="SEVERITES[c.severite] ?? 'bg-gray-100 text-gray-500'">
              {{ c.severite }}
            </span>
          </div>
          <p class="mt-2 text-sm text-gray-700">{{ c.constat }}</p>
          <p v-if="c.recommandation" class="mt-1 text-xs text-gray-500"><span class="font-semibold">Recommandation :</span> {{ c.recommandation }}</p>
          <div class="mt-3 grid gap-3 md:grid-cols-2">
            <label class="block text-xs font-semibold text-gray-600">
              Commentaire du client
              <textarea v-model="form.commentaires[c.id].commentaireClient" rows="3" class="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
            </label>
            <label class="block text-xs font-semibold text-gray-600">
              Réponse du management
              <textarea v-model="form.commentaires[c.id].reponseManagement" rows="3" class="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
            </label>
          </div>
        </div>
      </fieldset>
    </div>
  </div>
</template>
