<script setup>
import { ref } from 'vue'

// Liste déroulante à choix multiples : les éléments choisis s'affichent en étiquettes retirables.
const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: 'Choisir' },
  inputId: { type: String, default: undefined },
})
const emit = defineEmits(['update:modelValue'])

const open = ref(false)

function toggle(option) {
  const selected = props.modelValue.includes(option)
    ? props.modelValue.filter((value) => value !== option)
    : [...props.modelValue, option]
  emit('update:modelValue', selected)
}

function remove(option) {
  emit('update:modelValue', props.modelValue.filter((value) => value !== option))
}
</script>

<template>
  <div class="relative">
    <button
      :id="inputId"
      type="button"
      class="flex min-h-[42px] w-full flex-wrap items-center gap-1.5 rounded-xl border border-gray-200 bg-white px-3 py-1.5 text-left text-sm text-[#0d3b56] outline-none focus:ring-2 focus:ring-[#7cb342]"
      :aria-expanded="open"
      @click="open = !open"
    >
      <span v-if="modelValue.length === 0" class="px-1 text-gray-400">{{ placeholder }}</span>
      <span
        v-for="value in modelValue"
        :key="value"
        class="inline-flex items-center gap-1 rounded-full bg-[#e2f0e7] px-2.5 py-0.5 text-xs font-semibold text-[#0d3b56]"
      >
        {{ value }}
        <span
          role="button"
          class="text-gray-500 hover:text-red-600"
          :aria-label="`Retirer ${value}`"
          @click.stop="remove(value)"
          >✕</span
        >
      </span>
      <svg viewBox="0 0 24 24" class="ml-auto h-4 w-4 shrink-0 text-gray-400" fill="none" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="m6 9 6 6 6-6" />
      </svg>
    </button>

    <div v-if="open" class="fixed inset-0 z-10" @click="open = false"></div>
    <div
      v-if="open"
      class="absolute z-20 mt-1 max-h-56 w-full overflow-y-auto rounded-xl border border-gray-200 bg-white py-1 shadow-lg"
    >
      <p v-if="options.length === 0" class="px-4 py-2 text-sm text-gray-400">Aucun choix disponible</p>
      <label
        v-for="option in options"
        :key="option"
        class="flex cursor-pointer items-center gap-2 px-4 py-2 text-sm text-[#0d3b56] hover:bg-gray-50"
      >
        <input
          type="checkbox"
          class="h-4 w-4 accent-[#7cb342]"
          :checked="modelValue.includes(option)"
          @change="toggle(option)"
        />
        {{ option }}
      </label>
    </div>
  </div>
</template>
