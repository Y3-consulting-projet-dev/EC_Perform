<script setup>
import { reactive } from 'vue'
import DocumentChecklistView from './DocumentChecklistView.vue'

function docRow(n, description, statut = 'En attente de livraison') {
  return { n, description, version: 'Electronique', dateDemande: '17/05/2024', dateReception: '22/05/26', statut }
}

const checklist = reactive({
  recus: 15,
  total: 20,
  categories: [
    {
      title: 'DOCUMENT GENERAUX DE LA SOCIETE',
      documents: [
        docRow(1, 'Plan de localisation'),
        docRow(2, 'Copie des Statuts mis à jour'),
        docRow(3, 'Déclaration employeurs CNPS'),
      ],
    },
    {
      title: 'OPERATIONS DE TRESORERIE',
      documents: [
        docRow(4, 'Les relevés bancaires des banques de 2023'),
        docRow(5, "Les procès-verbaux d'inventaire de caisses"),
        docRow(6, 'Les brouillards de caisse ou état de suivi'),
      ],
    },
    {
      title: 'GESTION DE LA PAIE',
      documents: [
        docRow(7, 'Les contrats de travail des employés'),
        docRow(8, 'Le fichier complet de la gestion de la paie'),
        docRow(9, 'Livres de paie de 2023'),
      ],
    },
    {
      title: 'CADRE FISCALE ET SOCIALE',
      documents: [
        docRow(10, "L'ensemble des déclarations fiscales de 2023"),
        docRow(11, "L'ensemble des déclarations sociales de 2023", 'Partiellement reçu'),
        docRow(12, "La copie de la notification d'immatriculation"),
      ],
    },
  ],
})
</script>

<template>
  <DocumentChecklistView :checklist="checklist" />
</template>
