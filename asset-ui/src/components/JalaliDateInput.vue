<template>
  <div>
    <FormControl
      type="text"
      :label="label"
      :placeholder="placeholder"
      :model-value="text"
      class="ltr"
      inputmode="numeric"
      @update:model-value="onInput"
      @blur="onBlur"
    />
    <p v-if="error" class="mt-1 text-xs text-red-600">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { FormControl } from 'frappe-ui'
import { isoToJalali, jalaliToIso } from '@/utils/jalali'

// v-model carries the Gregorian ISO date (what ERPNext stores); the user types Jalali.
const props = defineProps({
  modelValue: { type: String, default: '' },
  label: String,
  placeholder: { type: String, default: '1405/01/01' },
})
const emit = defineEmits(['update:modelValue'])

const text = ref(isoToJalali(props.modelValue))
const error = ref('')

watch(
  () => props.modelValue,
  (iso) => {
    // Do not overwrite what the user is typing when it already maps to this value
    if (jalaliToIso(text.value) !== iso) text.value = isoToJalali(iso)
  },
)

function onInput(v) {
  text.value = v
  const iso = jalaliToIso(v)
  if (iso) {
    error.value = ''
    emit('update:modelValue', iso)
  }
}

function onBlur() {
  if (!text.value) {
    error.value = ''
    emit('update:modelValue', '')
  } else if (!jalaliToIso(text.value)) {
    error.value = 'تاریخ معتبر نیست. نمونه: 1405/08/15'
  } else {
    text.value = isoToJalali(jalaliToIso(text.value))
  }
}
</script>
