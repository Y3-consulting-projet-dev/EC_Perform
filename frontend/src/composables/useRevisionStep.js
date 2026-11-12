import { computed, inject, onActivated, watch } from 'vue'
import { getCycleRevision, getMissionRevisions } from './useCycleRevision'

const ETAPES_CODES = ['4a', '4b', '4c', '4d', '4e', '4f']

// Contexte commun aux écrans Phase 4 (étapes 4a-4f) et Phase 5 (revue par niveau) : cycle
// sélectionné, entrée de révision partagée, et choix d'un cycle par défaut à l'arrivée.
export function useRevisionStep(props, { niveau } = {}) {
  const nav = inject('revisionNav')
  const summary = getMissionRevisions(props.mission.id)

  function cycleParDefaut() {
    const cycles = summary.cycles
    // Revue : premier cycle en attente à ce niveau. Révision : d'abord les cycles renvoyés
    // (points à traiter), puis ceux en cours.
    const pertinent = niveau
      ? cycles.find((c) => c.niveauActif === niveau)
      : (cycles.find((c) => ETAPES_CODES.includes(c.statut) && c.retourDe) ??
        cycles.find((c) => ETAPES_CODES.includes(c.statut)))
    return (pertinent ?? cycles.find((c) => c.statut === 'non_commence') ?? cycles[0])?.code
  }

  watch(
    () => summary.loaded,
    (loaded) => {
      if (loaded && !nav.selectedCycle.value) nav.selectedCycle.value = cycleParDefaut()
    },
    { immediate: true },
  )

  const entry = computed(() =>
    nav.selectedCycle.value ? getCycleRevision(props.mission.id, nav.selectedCycle.value) : null,
  )
  watch(entry, (e) => e?.ensureLoaded(), { immediate: true })
  onActivated(() => entry.value?.ensureLoaded())

  const revision = computed(() => entry.value?.revision ?? null)
  const canEdit = computed(() => !!revision.value?.droits.editer)

  return { nav, summary, entry, revision, canEdit }
}
