<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import jspreadsheet from 'jspreadsheet-ce'
import 'jsuites/dist/jsuites.css'
import 'jspreadsheet-ce/dist/jspreadsheet.css'

// Classeur multi-onglets (Jspreadsheet CE, MIT). Les données sont lues une seule fois au
// montage : le parent remonte le composant (via :key) pour recharger un autre contenu.
const props = defineProps({
  feuilles: { type: Array, required: true },
  readOnly: { type: Boolean, default: false },
})
const emit = defineEmits(['change'])

const container = ref(null)
let worksheets = []

function snapshot() {
  return worksheets.map((ws, index) => ({
    nom: ws.options.worksheetName ?? props.feuilles[index]?.nom ?? `Feuille ${index + 1}`,
    colonnes: ws.getHeaders(true),
    // getData() sans argument renvoie les valeurs saisies (formules comprises), pas le rendu.
    data: ws.getData().map((row) => row.map((cell) => (cell === undefined ? '' : cell))),
  }))
}

function notify() {
  emit('change', snapshot())
}

onMounted(() => {
  const feuilles = JSON.parse(JSON.stringify(props.feuilles))
  worksheets = jspreadsheet(container.value, {
    worksheets: feuilles.map((feuille) => ({
      worksheetName: feuille.nom,
      data: feuille.data.length ? feuille.data : [feuille.colonnes.map(() => '')],
      columns: feuille.colonnes.map((title) => ({ title, type: 'text', width: 150 })),
      minDimensions: [feuille.colonnes.length || 5, 12],
      editable: !props.readOnly,
      allowInsertColumn: !props.readOnly,
      allowDeleteColumn: !props.readOnly,
      allowInsertRow: !props.readOnly,
      allowDeleteRow: !props.readOnly,
      tableOverflow: true,
      tableWidth: '100%',
    })),
    onafterchanges: notify,
    oninsertrow: notify,
    ondeleterow: notify,
    oninsertcolumn: notify,
    ondeletecolumn: notify,
    onchangeheader: notify,
    onmoverow: notify,
    onmovecolumn: notify,
    onsort: notify,
    onundo: notify,
    onredo: notify,
  })
})

onBeforeUnmount(() => {
  // false : les écouteurs globaux sont partagés avec les autres classeurs encore montés (4b / 4d).
  if (container.value) jspreadsheet.destroy(container.value, false)
})
</script>

<template>
  <div class="tableur overflow-x-auto bg-white text-blue-900 rounded-md shadow-sm border border-gray-300" :class="{ 'opacity-50 pointer-events-none': readOnly }">
    <div ref="container"></div>
  </div>
</template>

<style scoped>
.tableur :deep(.jss_worksheet) {
  font-size: 12px;
}
.tableur :deep(.jtabs-headers > div.jtabs-selected) {
  color: #1d6a3a;
  font-weight: 700;
}
</style>
