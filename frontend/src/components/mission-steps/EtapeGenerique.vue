<script setup>
import { reactive } from 'vue'
import DocumentChecklistView from './DocumentChecklistView.vue'

function docRow(n, description) {
  return { n, description, version: 'Electronique', dateDemande: '17/05/2024', dateReception: '22/05/26', statut: 'En attente de livraison' }
}

const checklist = reactive({
  recus: 0,
  total: 3,
  categories: [
    {
      title: 'DOCUMENTS REQUIS',
      documents: [
        docRow(1, 'Document justificatif 1'),
        docRow(2, 'Document justificatif 2'),
        docRow(3, 'Document justificatif 3'),
      ],
    },
  ],
})
</script>

<template>
  <DocumentChecklistView :checklist="checklist" />
</template>
