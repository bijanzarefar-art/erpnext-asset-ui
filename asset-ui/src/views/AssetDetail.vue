<template>
  <div class="space-y-6">
    <div class="flex items-center gap-3">
      <router-link to="/asset-list" class="text-sm text-gray-600 underline">فهرست دارایی‌ها</router-link>
      <span class="text-gray-400">/</span>
      <span class="ltr text-sm">{{ name }}</span>
    </div>

    <NoAccess v-if="denied" />
    <template v-else>
    <ErrorMessage :message="friendlyError(asset.error)" />
    <div v-if="asset.loading && !asset.data" class="text-gray-600">در حال بارگذاری…</div>

    <template v-if="asset.data">
      <div class="flex flex-wrap items-center gap-3">
        <h1 class="text-xl font-semibold">{{ asset.data.asset_name }}</h1>
        <StatusBadge :status="asset.data.status" />
      </div>

      <AssetActions :summary="asset.data" @changed="asset.reload()" />

      <dl class="grid gap-4 rounded-lg border bg-white p-4 sm:grid-cols-2 lg:grid-cols-3 text-sm">
        <div v-for="f in fields" :key="f.label">
          <dt class="text-gray-600">{{ f.label }}</dt>
          <dd class="mt-1 font-medium">{{ f.value }}</dd>
        </div>
      </dl>

      <section class="space-y-2">
        <h2 class="font-semibold">جدول استهلاک</h2>
        <div class="overflow-x-auto rounded-lg border bg-white">
          <table class="w-full text-sm">
            <thead class="bg-gray-50 text-gray-600">
              <tr>
                <th class="px-3 py-2 text-start font-medium">تاریخ</th>
                <th class="px-3 py-2 text-end font-medium">مبلغ استهلاک</th>
                <th class="px-3 py-2 text-end font-medium">استهلاک انباشته</th>
                <th class="px-3 py-2 text-start font-medium">سند</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!schedule.length">
                <td colspan="4" class="px-3 py-6 text-center text-gray-600">جدول استهلاکی ثبت نشده است.</td>
              </tr>
              <tr v-for="row in schedule" :key="row.schedule_date" class="border-t">
                <td class="px-3 py-2">{{ formatDate(row.schedule_date) }}</td>
                <td class="px-3 py-2 text-end">{{ formatMoney(row.depreciation_amount) }}</td>
                <td class="px-3 py-2 text-end">{{ formatMoney(row.accumulated_depreciation_amount) }}</td>
                <td class="px-3 py-2 ltr">{{ row.journal_entry || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <AssetMaintenance :asset="name" :can="asset.data.can" />
    </template>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ErrorMessage, createResource } from 'frappe-ui'
import { autoResource } from '@/api/resource'
import StatusBadge from '@/components/StatusBadge.vue'
import AssetActions from '@/components/AssetActions.vue'
import AssetMaintenance from '@/components/AssetMaintenance.vue'
import NoAccess from '@/components/NoAccess.vue'
import { formatDate, formatMoney, friendlyError } from '@/utils/format'

const props = defineProps({ name: { type: String, required: true } })

// One call: asset details + Active depreciation schedule + allowed actions
const asset = autoResource(createResource, {
  url: 'asset_api.api.assets.get_summary',
  params: { name: props.name },
  auto: true,
})

// A 403 here means the asset exists but is outside the caller's User Permission scope.
const denied = computed(() => {
  const raw = [asset.error?.exc_type, asset.error?.message, ...(asset.error?.messages || [])].join(' ')
  return /Permission|not permitted|403/i.test(raw)
})

const schedule = computed(() => asset.data?.depreciation_schedule || [])

const fields = computed(() => {
  const a = asset.data
  return [
    { label: 'شرکت', value: a.company || '—' },
    { label: 'دسته‌بندی', value: a.asset_category || '—' },
    { label: 'محل', value: a.location || '—' },
    { label: 'متصدی', value: a.custodian || '—' },
    { label: 'تاریخ خرید', value: formatDate(a.purchase_date) },
    { label: 'تاریخ آماده‌به‌کار شدن', value: formatDate(a.available_for_use_date) },
    { label: 'مبلغ خرید خالص', value: formatMoney(a.net_purchase_amount) },
    { label: 'بهای تمام‌شده کل', value: formatMoney(a.total_asset_cost) },
    { label: 'ارزش دفتری', value: formatMoney(a.value_after_depreciation) },
  ]
})
</script>
