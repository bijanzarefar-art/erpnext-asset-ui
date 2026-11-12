<template>
  <section class="space-y-6">
    <!-- Repairs -->
    <div class="space-y-2">
      <div class="flex items-center justify-between">
        <h2 class="font-semibold">تعمیرات</h2>
        <Button v-if="props.can.create_repair" @click="openNewRepair">ثبت تعمیر</Button>
      </div>
      <ErrorMessage :message="friendlyError(repairs.error)" />
      <div v-if="!repairs.error" class="overflow-x-auto rounded-lg border bg-white">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-gray-600">
            <tr>
              <th class="px-3 py-2 text-start font-medium">تاریخ خرابی</th>
              <th class="px-3 py-2 text-start font-medium">شرح</th>
              <th class="px-3 py-2 text-start font-medium">وضعیت</th>
              <th class="px-3 py-2 text-end font-medium">هزینه</th>
              <th class="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!repairs.data?.length">
              <td colspan="5" class="px-3 py-6 text-center text-gray-600">تعمیری ثبت نشده است.</td>
            </tr>
            <tr v-for="r in repairs.data" :key="r.name" class="border-t">
              <td class="px-3 py-2">{{ formatDate(r.failure_date) }}</td>
              <td class="px-3 py-2">{{ r.description }}</td>
              <td class="px-3 py-2"><Badge :label="repairLabel(r.repair_status)" :theme="r.repair_status === 'Completed' ? 'green' : 'amber'" variant="subtle" /></td>
              <td class="px-3 py-2 text-end">{{ r.docstatus === 1 ? formatMoney(r.total_repair_cost) : '—' }}</td>
              <td class="px-3 py-2 text-end">
                <Button v-if="props.can.write && r.repair_status === 'Pending'" size="sm" @click="openComplete(r)">تکمیل</Button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Maintenance logs -->
    <div class="space-y-2">
      <div class="flex items-center justify-between">
        <h2 class="font-semibold">برنامه نگهداری</h2>
        <Button v-if="props.can.create_maintenance_plan && plan.fetched && !plan.data" @click="planFormOpen = true">ساخت برنامه نگهداری</Button>
      </div>
      <p v-if="plan.data" class="text-xs text-gray-600">
        تیم: {{ plan.data.maintenance_team }} — {{ plan.data.tasks.length }} کار برنامه‌ریزی‌شده
      </p>
      <ErrorMessage :message="friendlyError(logs.error) || friendlyError(plan.error)" />
      <div v-if="!logs.error" class="overflow-x-auto rounded-lg border bg-white">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-gray-600">
            <tr>
              <th class="px-3 py-2 text-start font-medium">کار</th>
              <th class="px-3 py-2 text-start font-medium">سررسید</th>
              <th class="px-3 py-2 text-start font-medium">وضعیت</th>
              <th class="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!logs.data?.length">
              <td colspan="4" class="px-3 py-6 text-center text-gray-600">برنامه نگهداری‌ای برای این دارایی نیست.</td>
            </tr>
            <tr v-for="l in logs.data" :key="l.name" class="border-t">
              <td class="px-3 py-2">{{ l.task_name || '—' }}</td>
              <td class="px-3 py-2">{{ formatDate(l.due_date) }}</td>
              <td class="px-3 py-2"><Badge :label="logLabel(l.maintenance_status)" :theme="logTheme(l.maintenance_status)" variant="subtle" /></td>
              <td class="px-3 py-2 text-end">
                <Button v-if="props.can.write && l.docstatus === 0 && ['Planned', 'Overdue'].includes(l.maintenance_status)" size="sm" @click="openLog(l)">تکمیل</Button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- One reusable form dialog -->
    <Dialog v-model="dialog.open" :title="dialog.title" size="md">
      <form class="space-y-4 text-sm" @submit.prevent="submit">
        <DialogDescription class="sr-only">{{ dialogMessage }}</DialogDescription>
        <FormControl v-if="dialog.kind === 'new'" v-model="form.description" type="textarea" label="شرح خرابی" />
        <JalaliDateInput v-model="form.date" :label="dateLabel" />
        <p v-if="form.date > today" class="text-xs text-red-600">تاریخ آینده مجاز نیست.</p>
        <FormControl v-if="dialog.kind !== 'new'" v-model="form.actions" type="textarea" label="اقدامات انجام‌شده" />
        <p v-if="dialog.kind === 'repair'" class="text-xs text-gray-600">هزینه تعمیر از فاکتورهای خرید و اقلام مصرفی محاسبه می‌شود و اینجا وارد نمی‌شود.</p>
        <ErrorMessage :message="dialog.error" />
        <p v-if="dialog.detail" class="ltr text-xs text-gray-600">{{ dialog.detail }}</p>
        <div class="flex justify-end gap-2">
          <Button type="button" @click="dialog.open = false">انصراف</Button>
          <Button variant="solid" type="submit" :loading="dialog.loading" :disabled="!valid">ثبت</Button>
        </div>
      </form>
    </Dialog>

    <MaintenancePlanForm v-model="planFormOpen" :asset="asset" @created="onPlanCreated" />
  </section>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { Badge, Button, Dialog, ErrorMessage, FormControl, createResource, toast } from 'frappe-ui'
import { DialogDescription } from 'reka-ui'
import JalaliDateInput from '@/components/JalaliDateInput.vue'
import MaintenancePlanForm from '@/components/MaintenancePlanForm.vue'
import { callApi } from '@/api/client'
import { autoResource } from '@/api/resource'
import { formatDate, formatMoney, friendlyError } from '@/utils/format'
import { todayIso } from '@/utils/today'

const props = defineProps({ asset: { type: String, required: true }, can: { type: Object, required: true } })
const today = todayIso()

const repairs = autoResource(createResource, { url: 'asset_api.api.maintenance.list_repairs', params: { asset: props.asset }, auto: true })
const logs = autoResource(createResource, { url: 'asset_api.api.maintenance.list_logs', params: { asset: props.asset }, auto: true })
const plan = autoResource(createResource, { url: 'asset_api.api.maintenance.get_plan', params: { asset: props.asset }, auto: true })
const planFormOpen = ref(false)
function onPlanCreated() {
  plan.reload()
  logs.reload()
}

const REPAIR = { Pending: 'در انتظار', Completed: 'تکمیل‌شده', Cancelled: 'لغوشده' }
const LOG = { Planned: 'برنامه‌ریزی‌شده', Completed: 'انجام‌شده', Overdue: 'معوق', Cancelled: 'لغوشده' }
const repairLabel = (s) => REPAIR[s] || s
const logLabel = (s) => LOG[s] || s
const logTheme = (s) => ({ Completed: 'green', Overdue: 'red' })[s] || 'amber'

const dialog = reactive({ open: false, kind: '', title: '', target: '', loading: false, error: '', detail: '' })
const form = reactive({ description: '', date: today, actions: '' })

const dateLabel = computed(() => (dialog.kind === 'new' ? 'تاریخ خرابی (جلالی)' : 'تاریخ تکمیل (جلالی)'))
const DIALOG_MESSAGE = {
  new: 'یک رویداد تعمیر جدید برای این دارایی ثبت می‌شود.',
  repair: 'این تعمیر با وضعیت تکمیل‌شده ثبت و تأیید می‌شود.',
  log: 'این کار نگهداری با وضعیت انجام‌شده ثبت می‌شود و نوبت بعدی خودکار ساخته می‌شود.',
}
const dialogMessage = computed(() => DIALOG_MESSAGE[dialog.kind] || '')
const valid = computed(() => {
  if (!form.date || form.date > today) return false
  if (dialog.kind === 'new') return form.description.trim().length > 0
  return form.actions.trim().length > 0
})

function open(kind, title, target = '') {
  Object.assign(dialog, { open: true, kind, title, target, loading: false, error: '', detail: '' })
  Object.assign(form, { description: '', date: today, actions: '' })
}
const openNewRepair = () => open('new', 'ثبت تعمیر جدید')
const openComplete = (r) => open('repair', 'تکمیل تعمیر', r.name)
const openLog = (l) => open('log', 'تکمیل کار نگهداری', l.name)

// Date-only input: time is fixed at 00:00, which is never in the future for today
const at = (iso) => `${iso} 00:00:00`

async function submit() {
  dialog.loading = true
  dialog.error = dialog.detail = ''
  try {
    if (dialog.kind === 'new') {
      await callApi('asset_api.api.maintenance.create_repair', { asset: props.asset, failure_date: at(form.date), description: form.description })
      toast.success('تعمیر ثبت شد.')
    } else if (dialog.kind === 'repair') {
      await callApi('asset_api.api.maintenance.complete_repair', { name: dialog.target, completion_date: at(form.date), actions_performed: form.actions })
      toast.success('تعمیر تکمیل شد.')
    } else {
      await callApi('asset_api.api.maintenance.complete_log', { name: dialog.target, completion_date: form.date, actions_performed: form.actions })
      toast.success('کار نگهداری تکمیل شد.')
    }
    dialog.open = false
    repairs.reload()
    logs.reload()
  } catch (e) {
    dialog.error = e.message
    dialog.detail = e.detail || ''
  } finally {
    dialog.loading = false
  }
}
</script>
