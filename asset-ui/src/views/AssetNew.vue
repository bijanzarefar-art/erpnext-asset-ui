<template>
  <div class="max-w-xl space-y-4">
    <div class="flex items-center gap-3 text-sm">
      <router-link to="/asset-list" class="text-gray-600 underline">فهرست دارایی‌ها</router-link>
      <span class="text-gray-400">/</span>
      <span>ثبت دارایی جدید</span>
    </div>
    <h1 class="text-xl font-semibold">ثبت دارایی جدید</h1>

    <NoAccess v-if="denied" />
    <template v-else>
    <ErrorMessage :message="friendlyError(options.error)" />

    <form v-if="!options.error && step === 1" class="space-y-4 rounded-lg border bg-white p-4" @submit.prevent="step = 2">
      <FormControl v-model="form.item_code" type="select" label="کالا" :options="itemOptions" @update:model-value="onItemChange" />
      <FormControl v-model="form.asset_name" type="text" label="نام دارایی" />
      <FormControl v-model="form.company" type="select" label="شرکت" :options="companyOptions" />
      <FormControl v-model="form.location" type="select" label="محل" :options="locationOptions" />
      <JalaliDateInput v-model="form.purchase_date" label="تاریخ خرید (جلالی)" />
      <p v-if="form.purchase_date > today" class="text-xs text-red-600">تاریخ آینده مجاز نیست.</p>
      <JalaliDateInput v-model="form.available_for_use_date" label="تاریخ آماده‌به‌کار شدن (جلالی)" />
      <p v-if="form.available_for_use_date && form.purchase_date && form.available_for_use_date < form.purchase_date"
         class="text-xs text-red-600">باید بعد از تاریخ خرید باشد.</p>
      <FormControl v-model.number="form.net_purchase_amount" type="number" label="مبلغ خرید خالص (ریال)" class="ltr" />
      <p v-if="form.net_purchase_amount !== null && form.net_purchase_amount !== '' && Number(form.net_purchase_amount) <= 0" class="text-xs text-red-600">باید بیشتر از صفر باشد.</p>
      <div class="flex justify-end gap-2">
        <Button @click="$router.back()">انصراف</Button>
        <Button variant="solid" type="submit" :disabled="!canContinue">مرور و ثبت</Button>
      </div>
    </form>

    <div v-else-if="!options.error" class="space-y-4 rounded-lg border bg-white p-4 text-sm">
      <h2 class="font-semibold">مرور نهایی</h2>
      <dl class="grid grid-cols-2 gap-2">
        <div><dt class="text-gray-600">نام دارایی</dt><dd class="font-medium">{{ form.asset_name }}</dd></div>
        <div><dt class="text-gray-600">کالا</dt><dd class="font-medium">{{ itemLabel }}</dd></div>
        <div><dt class="text-gray-600">شرکت</dt><dd class="font-medium">{{ form.company }}</dd></div>
        <div><dt class="text-gray-600">محل</dt><dd class="font-medium">{{ form.location }}</dd></div>
        <div><dt class="text-gray-600">تاریخ خرید</dt><dd class="font-medium">{{ formatDate(form.purchase_date) }}</dd></div>
        <div><dt class="text-gray-600">تاریخ آماده‌به‌کار</dt><dd class="font-medium">{{ formatDate(form.available_for_use_date) }}</dd></div>
        <div class="col-span-2"><dt class="text-gray-600">مبلغ خرید خالص</dt><dd class="font-medium">{{ formatMoney(form.net_purchase_amount) }}</dd></div>
      </dl>
      <ErrorMessage :message="error" />
      <p v-if="detail" class="ltr text-xs text-gray-600">{{ detail }}</p>
      <div class="flex justify-end gap-2">
        <Button :disabled="saving" @click="step = 1">بازگشت</Button>
        <Button variant="solid" :loading="saving" @click="save">ثبت دارایی</Button>
      </div>
    </div>
    </template>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button, ErrorMessage, FormControl, createResource, toast } from 'frappe-ui'
import JalaliDateInput from '@/components/JalaliDateInput.vue'
import NoAccess from '@/components/NoAccess.vue'
import { callApi } from '@/api/client'
import { autoResource } from '@/api/resource'
import { formatDate, formatMoney, friendlyError } from '@/utils/format'
import { todayIso } from '@/utils/today'

const router = useRouter()
const today = todayIso()
const step = ref(1)
const saving = ref(false)
const error = ref('')
const detail = ref('')

const form = reactive({
  item_code: '', asset_name: '', company: '', location: '',
  purchase_date: today, available_for_use_date: today, net_purchase_amount: null,
})

const options = autoResource(createResource, { url: 'asset_api.api.options.new_asset_form', auto: true })

// A 403 from the options endpoint means "no permission", not "no options".
const denied = computed(() => {
  const raw = [options.error?.exc_type, options.error?.message, ...(options.error?.messages || [])].join(' ')
  return /Permission|not permitted|403/i.test(raw)
})

const itemOptions = computed(() => [
  { label: 'یک کالا انتخاب کنید', value: '' },
  ...(options.data?.items || []).map((i) => ({ label: `${i.item_name} (${i.asset_category || '—'})`, value: i.item_code })),
])
const companyOptions = computed(() => [
  { label: 'یک شرکت انتخاب کنید', value: '' },
  ...(options.data?.companies || []).map((c) => ({ label: c.name, value: c.name })),
])
const locationOptions = computed(() => [
  { label: 'یک محل انتخاب کنید', value: '' },
  ...(options.data?.locations || []).map((l) => ({ label: l.name, value: l.name })),
])
const itemLabel = computed(() => itemOptions.value.find((o) => o.value === form.item_code)?.label)

function onItemChange(code) {
  const item = options.data?.items.find((i) => i.item_code === code)
  if (item && !form.asset_name) form.asset_name = item.item_name
}

const canContinue = computed(() =>
  form.item_code && form.asset_name.trim() && form.company && form.location &&
  form.purchase_date && form.purchase_date <= today &&
  form.available_for_use_date && form.available_for_use_date >= form.purchase_date &&
  Number(form.net_purchase_amount) > 0
)

async function save() {
  saving.value = true
  error.value = detail.value = ''
  try {
    const result = await callApi('asset_api.api.assets.create', { ...form, net_purchase_amount: Number(form.net_purchase_amount) })
    toast.success('دارایی ثبت شد.')
    router.replace({ name: 'Asset', params: { name: result.name } })
  } catch (e) {
    error.value = e.message
    detail.value = e.detail || ''
  } finally {
    saving.value = false
  }
}
</script>
