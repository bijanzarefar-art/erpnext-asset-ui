<template>
  <div class="max-w-xl space-y-4">
    <div class="flex items-center gap-3 text-sm">
      <router-link to="/asset-list" class="text-gray-600 underline">فهرست دارایی‌ها</router-link>
      <span class="text-gray-400">/</span>
      <span>جابه‌جایی دارایی</span>
    </div>
    <h1 class="text-xl font-semibold">جابه‌جایی دارایی</h1>

    <NoAccess v-if="denied" />
    <template v-else>
    <ErrorMessage :message="friendlyError(assets.error)" />

    <form class="space-y-4 rounded-lg border bg-white p-4" @submit.prevent="step = 2" v-if="step === 1">
      <FormControl v-model="asset" type="select" label="دارایی" :options="assetOptions" />
      <FormControl v-model="purpose" type="select" label="نوع جابه‌جایی" :options="purposeOptions" />
      <FormControl v-model="target" type="select" label="محل مقصد" :options="locationOptions" />
      <p v-if="sameLocation" class="text-xs text-red-600">محل مقصد با محل فعلی یکی است.</p>
      <div class="flex justify-end gap-2">
        <Button @click="$router.back()">انصراف</Button>
        <Button variant="solid" type="submit" :disabled="!canContinue">مرور و ثبت</Button>
      </div>
    </form>

    <div v-else class="space-y-4 rounded-lg border bg-white p-4 text-sm">
      <h2 class="font-semibold">مرور نهایی</h2>
      <dl class="space-y-2">
        <div><dt class="inline text-gray-600">دارایی: </dt><dd class="inline font-medium">{{ current?.asset_name }} (<span class="ltr inline-block">{{ asset }}</span>)</dd></div>
        <div><dt class="inline text-gray-600">نوع: </dt><dd class="inline font-medium">{{ purposeLabel }}</dd></div>
        <div><dt class="inline text-gray-600">از: </dt><dd class="inline font-medium">{{ current?.location || '—' }}</dd></div>
        <div><dt class="inline text-gray-600">به: </dt><dd class="inline font-medium">{{ target }}</dd></div>
      </dl>
      <ErrorMessage :message="error" />
      <p v-if="detail" class="ltr text-xs text-gray-600">{{ detail }}</p>
      <div class="flex justify-end gap-2">
        <Button :disabled="saving" @click="step = 1">بازگشت</Button>
        <Button variant="solid" :loading="saving" @click="save">ثبت جابه‌جایی</Button>
      </div>
    </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, ErrorMessage, FormControl, createListResource, toast } from 'frappe-ui'
import NoAccess from '@/components/NoAccess.vue'
import { callApi } from '@/api/client'
import { autoResource } from '@/api/resource'
import { friendlyError } from '@/utils/format'

const route = useRoute()
const router = useRouter()

const PURPOSES = [
  { label: 'انتقال بین محل‌ها', value: 'Transfer' },
]
const purposeOptions = PURPOSES
const purpose = ref('Transfer')
const asset = ref(String(route.query.asset || ''))
const target = ref('')
const step = ref(1)
const saving = ref(false)
const error = ref('')
const detail = ref('')

const assets = autoResource(createListResource, {
  doctype: 'Asset',
  fields: ['name', 'asset_name', 'location', 'status'],
  filters: { docstatus: 1, status: ['not in', ['Scrapped', 'Sold', 'Cancelled', 'Capitalized']] },
  orderBy: 'asset_name asc',
  pageLength: 200,
  auto: true,
})
const locations = autoResource(createListResource, {
  doctype: 'Location',
  fields: ['name'],
  filters: { is_group: 0 },
  orderBy: 'name asc',
  pageLength: 200,
  auto: true,
})

// A 403 from the asset list means "no read permission", not "no rows".
const denied = computed(() => {
  const raw = [assets.error?.exc_type, assets.error?.message, ...(assets.error?.messages || [])].join(' ')
  return /Permission|not permitted|403/i.test(raw)
})

const assetOptions = computed(() => [
  { label: 'یک دارایی انتخاب کنید', value: '' },
  ...(assets.data || []).map((a) => ({ label: `${a.asset_name} (${a.name})`, value: a.name })),
])
const locationOptions = computed(() => [
  { label: 'یک محل انتخاب کنید', value: '' },
  ...(locations.data || []).map((l) => ({ label: l.name, value: l.name })),
])
const current = computed(() => (assets.data || []).find((a) => a.name === asset.value))
const sameLocation = computed(() => !!target.value && current.value?.location === target.value)
const canContinue = computed(() => !!asset.value && !!target.value && !sameLocation.value)
const purposeLabel = computed(() => PURPOSES.find((p) => p.value === purpose.value)?.label)

async function save() {
  saving.value = true
  error.value = ''
  detail.value = ''
  try {
    await callApi('asset_api.api.movements.create', {
      assets: [asset.value],
      purpose: purpose.value,
      target_location: target.value,
    })
    toast.success('جابه‌جایی ثبت شد.')
    router.replace({ name: 'Asset', params: { name: asset.value } })
  } catch (e) {
    error.value = e.message
    detail.value = e.detail || ''
  } finally {
    saving.value = false
  }
}
</script>
