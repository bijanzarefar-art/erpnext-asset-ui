<template>
  <div class="space-y-6">
    <h1 class="text-xl font-semibold">داشبورد دارایی‌ها</h1>

    <NoAccess v-if="denied" />
    <template v-else>
    <ErrorMessage :message="friendlyError(stats.error)" />

    <div v-if="!stats.error" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div class="rounded-lg border bg-white p-4">
        <div class="text-sm text-gray-600">تعداد کل دارایی‌ها</div>
        <div class="mt-2 text-2xl font-semibold">{{ formatNumber(totalCount) }}</div>
      </div>
      <div class="rounded-lg border bg-white p-4">
        <div class="text-sm text-gray-600">مجموع ارزش دفتری</div>
        <div class="mt-2 text-2xl font-semibold">{{ formatMoney(totalValue) }}</div>
      </div>
    </div>

    <section v-if="!stats.error" class="space-y-2">
      <h2 class="font-semibold">به تفکیک وضعیت</h2>
      <div class="overflow-x-auto rounded-lg border bg-white">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-gray-600">
            <tr>
              <th class="px-3 py-2 text-start font-medium">وضعیت</th>
              <th class="px-3 py-2 text-end font-medium">تعداد</th>
              <th class="px-3 py-2 text-end font-medium">ارزش دفتری</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!rows.length">
              <td colspan="3" class="px-3 py-6 text-center text-gray-600">
                {{ stats.loading ? 'در حال بارگذاری…' : 'داده‌ای نیست.' }}
              </td>
            </tr>
            <tr v-for="r in rows" :key="r.status" class="border-t">
              <td class="px-3 py-2"><StatusBadge :status="r.status" /></td>
              <td class="px-3 py-2 text-end">{{ formatNumber(r.count) }}</td>
              <td class="px-3 py-2 text-end">{{ formatMoney(r.value) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ErrorMessage, createResource } from 'frappe-ui'
import { autoResource } from '@/api/resource'
import StatusBadge from '@/components/StatusBadge.vue'
import NoAccess from '@/components/NoAccess.vue'
import { formatMoney, formatNumber, friendlyError } from '@/utils/format'

// Aggregated server-side under the caller's permissions
const stats = autoResource(createResource, {
  url: 'asset_api.api.reports.dashboard',
  auto: true,
})

// A 403 from the report endpoint means "no read permission", not "no data".
const denied = computed(() => {
  const raw = [stats.error?.exc_type, stats.error?.message, ...(stats.error?.messages || [])].join(' ')
  return /Permission|not permitted|403/i.test(raw)
})

const rows = computed(() => stats.data?.by_status || [])
const totalCount = computed(() => rows.value.reduce((s, r) => s + (r.count || 0), 0))
const totalValue = computed(() => rows.value.reduce((s, r) => s + (r.value || 0), 0))
</script>
