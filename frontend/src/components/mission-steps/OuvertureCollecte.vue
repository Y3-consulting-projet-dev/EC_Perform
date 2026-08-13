<script setup>
import DocumentChecklistView from './DocumentChecklistView.vue'

const props = defineProps({
  mission: { type: Object, required: true },
})
</script>

<template>
  <DocumentChecklistView :mission="props.mission" />
</template>
