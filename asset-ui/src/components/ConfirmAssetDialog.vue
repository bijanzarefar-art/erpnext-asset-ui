<template>
  <Dialog v-model="open" :title="title" :theme="theme" size="md">
    <div class="space-y-4 text-sm">
      <DialogDescription class="sr-only">{{ intro }}</DialogDescription>
      <!-- Step 1: inputs -->
      <template v-if="step === 1">
        <p class="text-gray-700">{{ intro }}</p>
        <slot name="fields" />
        <div class="flex justify-end gap-2 pt-2">
          <Button @click="open = false">انصراف</Button>
          <Button variant="solid" :disabled="!ready" @click="step = 2">ادامه</Button>
        </div>
      </template>

      <!-- Step 2: explicit confirmation, user types the asset code -->
      <template v-else>
        <div class="rounded-md border border-amber-300 bg-amber-50 p-3 text-gray-800">
          <slot name="summary" />
        </div>
        <FormControl
          v-model="typed"
          type="text"
          :label="`برای تأیید، کد دارایی را وارد کنید: ${assetName}`"
          class="ltr"
          autocomplete="off"
        />
        <ErrorMessage :message="error" />
        <p v-if="detail" class="ltr text-xs text-gray-600">{{ detail }}</p>
        <div class="flex justify-end gap-2 pt-2">
          <Button :disabled="loading" @click="step = 1">بازگشت</Button>
          <Button variant="solid" theme="red" :disabled="typed.trim() !== assetName" :loading="loading" @click="run">
            {{ confirmLabel }}
          </Button>
        </div>
      </template>
    </div>
  </Dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Button, Dialog, ErrorMessage, FormControl } from 'frappe-ui'
import { DialogDescription } from 'reka-ui'

const props = defineProps({
  modelValue: Boolean,
  title: String,
  intro: String,
  assetName: { type: String, required: true },
  confirmLabel: { type: String, default: 'تأیید' },
  theme: { type: String, default: 'red' },
  ready: { type: Boolean, default: true },
  action: { type: Function, required: true },
})
const emit = defineEmits(['update:modelValue', 'done'])

const open = ref(props.modelValue)
const step = ref(1)
const typed = ref('')
const loading = ref(false)
const error = ref('')
const detail = ref('')

watch(() => props.modelValue, (v) => (open.value = v))
watch(open, (v) => {
  emit('update:modelValue', v)
  if (v) {
    step.value = 1
    typed.value = ''
    error.value = ''
    detail.value = ''
  }
})

async function run() {
  loading.value = true
  error.value = ''
  detail.value = ''
  try {
    const result = await props.action()
    open.value = false
    emit('done', result)
  } catch (e) {
    error.value = e.message
    detail.value = e.detail || ''
  } finally {
    loading.value = false
  }
}
</script>
