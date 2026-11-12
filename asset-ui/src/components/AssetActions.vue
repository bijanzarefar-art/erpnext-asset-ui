<template>
  <div class="flex flex-wrap gap-2">
    <router-link
      v-if="summary.can.create_movement"
      :to="{ name: 'MovementNew', query: { asset: summary.name } }"
    >
      <Button>جابه‌جایی</Button>
    </router-link>
    <Button v-if="summary.can.scrap" theme="red" @click="scrapOpen = true">اسقاط دارایی</Button>
    <Button v-if="summary.can.restore" @click="restoreOpen = true">بازگردانی دارایی</Button>

    <ConfirmAssetDialog
      v-model="scrapOpen"
      title="اسقاط دارایی"
      intro="اسقاط یک سند حسابداری ثبت می‌کند. فقط با بازگردانی می‌توان آن را برگرداند."
      :asset-name="summary.name"
      confirm-label="اسقاط شود"
      :ready="!!scrapDate && scrapDate <= today"
      :action="doScrap"
      @done="onDone('دارایی اسقاط شد.', $event)"
    >
      <template #fields>
        <JalaliDateInput v-model="scrapDate" label="تاریخ اسقاط (جلالی)" />
        <p v-if="scrapDate > today" class="text-xs text-red-600">تاریخ آینده مجاز نیست.</p>
      </template>
      <template #summary>
        اسقاط <b>{{ summary.asset_name }}</b> (<span class="ltr inline-block">{{ summary.name }}</span>)
        در تاریخ <b>{{ formatDate(scrapDate) }}</b>
      </template>
    </ConfirmAssetDialog>

    <ConfirmAssetDialog
      v-model="restoreOpen"
      title="بازگردانی دارایی"
      intro="سند اسقاط ابطال می‌شود و دارایی به وضعیت قبل برمی‌گردد."
      theme="amber"
      :asset-name="summary.name"
      confirm-label="بازگردانی شود"
      :action="doRestore"
      @done="onDone('دارایی بازگردانی شد.', $event)"
    >
      <template #summary>
        بازگردانی <b>{{ summary.asset_name }}</b> (<span class="ltr inline-block">{{ summary.name }}</span>)
        و ابطال سند اسقاط
      </template>
    </ConfirmAssetDialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Button, toast } from 'frappe-ui'
import ConfirmAssetDialog from '@/components/ConfirmAssetDialog.vue'
import JalaliDateInput from '@/components/JalaliDateInput.vue'
import { callApi } from '@/api/client'
import { formatDate } from '@/utils/format'
import { todayIso } from '@/utils/today'

const props = defineProps({ summary: { type: Object, required: true } })
const emit = defineEmits(['changed'])

const today = todayIso()
const scrapOpen = ref(false)
const restoreOpen = ref(false)
const scrapDate = ref(today)

const doScrap = () => callApi('asset_api.api.assets.scrap', { name: props.summary.name, scrap_date: scrapDate.value })
const doRestore = () => callApi('asset_api.api.assets.restore', { name: props.summary.name })

function onDone(message, result) {
  toast.success(message)
  emit('changed', result)
}
</script>
