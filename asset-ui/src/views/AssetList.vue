<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center gap-3">
      <h1 class="text-xl font-semibold">فهرست دارایی‌ها</h1>
      <router-link v-if="session.features.asset_create" to="/asset/new" class="me-auto"><Button variant="solid">ثبت دارایی جدید</Button></router-link>
      <template v-if="!denied">
        <FormControl v-model="search" type="text" placeholder="جستجوی نام یا کد دارایی" class="w-64" />
        <FormControl v-model="status" type="select" :options="statusOptions" class="w-44" />
      </template>
    </div>

    <NoAccess v-if="denied" />
    <template v-else>
    <ErrorMessage :message="friendlyError(assets.error)" />

    <div class="overflow-x-auto rounded-lg border bg-white">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-gray-600">
          <tr>
            <th class="px-3 py-2 text-start font-medium">کد</th>
            <th class="px-3 py-2 text-start font-medium">نام دارایی</th>
            <th class="px-3 py-2 text-start font-medium">دسته‌بندی</th>
            <th class="px-3 py-2 text-start font-medium">محل</th>
            <th class="px-3 py-2 text-start font-medium">وضعیت</th>
            <th class="px-3 py-2 text-start font-medium">تاریخ خرید</th>
            <th class="px-3 py-2 text-end font-medium">ارزش دفتری</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="assets.loading && !assets.data?.length">
            <td colspan="7" class="px-3 py-6 text-center text-gray-600">در حال بارگذاری…</td>
          </tr>
          <tr v-else-if="!assets.data?.length">
            <td colspan="7" class="px-3 py-6 text-center text-gray-600">دارایی‌ای یافت نشد.</td>
          </tr>
          <tr
            v-for="row in assets.data"
            :key="row.name"
            class="cursor-pointer border-t hover:bg-gray-50"
            @click="$router.push({ name: 'Asset', params: { name: row.name } })"
          >
            <td class="px-3 py-2 ltr">{{ row.name }}</td>
            <td class="px-3 py-2">{{ row.asset_name }}</td>
            <td class="px-3 py-2">{{ row.asset_category || '—' }}</td>
            <td class="px-3 py-2">{{ row.location || '—' }}</td>
            <td class="px-3 py-2"><StatusBadge :status="row.status" /></td>
            <td class="px-3 py-2">{{ formatDate(row.purchase_date) }}</td>
            <td class="px-3 py-2 text-end">{{ formatMoney(row.value_after_depreciation) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="flex items-center justify-between text-sm text-gray-600">
      <span>{{ formatNumber(assets.data?.length || 0) }} مورد نمایش داده شد</span>
      <Button v-if="hasMore" :loading="assets.loading" @click="assets.next()">نمایش بیشتر</Button>
    </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Button, ErrorMessage, FormControl, createListResource } from 'frappe-ui'
import StatusBadge from '@/components/StatusBadge.vue'
import NoAccess from '@/components/NoAccess.vue'
import { ASSET_STATUS, formatDate, formatMoney, formatNumber, friendlyError } from '@/utils/format'
import { session } from '@/api/session'
import { autoResource } from '@/api/resource'

const PAGE = 20
const search = ref('')
const status = ref('')

const statusOptions = [
  { label: 'همه وضعیت‌ها', value: '' },
  ...Object.entries(ASSET_STATUS).map(([value, m]) => ({ label: m.label, value })),
]

const assets = autoResource(createListResource, {
  doctype: 'Asset',
  fields: [
    'name', 'asset_name', 'asset_category', 'location', 'status',
    'purchase_date', 'value_after_depreciation',
  ],
  orderBy: 'modified desc',
  pageLength: PAGE,
  auto: true,
})

// A 403 from the list endpoint means "no read permission", not "no rows".
const denied = computed(() => {
  const raw = [assets.error?.exc_type, assets.error?.message, ...(assets.error?.messages || [])].join(' ')
  return /Permission|not permitted|403/i.test(raw)
})

const hasMore = computed(() => {
  const n = assets.data?.length || 0
  return n > 0 && n % PAGE === 0
})

function applyFilters() {
  const filters = {}
  if (status.value) filters.status = status.value
  const or_filters = search.value
    ? [['asset_name', 'like', `%${search.value}%`], ['name', 'like', `%${search.value}%`]]
    : []
  assets.update({ filters, orFilters: or_filters })
  assets.reload()
}

let timer
watch([search, status], () => {
  clearTimeout(timer)
  timer = setTimeout(applyFilters, 300)
})
</script>
