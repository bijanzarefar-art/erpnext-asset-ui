<template>
  <Dialog v-model="open" title="ساخت برنامه نگهداری" size="xl">
    <div class="space-y-4 text-sm">
      <DialogDescription class="sr-only">تیم و کارهای دوره‌ای این دارایی را مشخص کنید.</DialogDescription>
      <FormControl v-model="teamName" type="select" label="تیم نگهداری" :options="teamOptions" @update:model-value="onTeamChange" />
      <ErrorMessage :message="friendlyError(teams.error)" />

      <div v-if="teamName" class="space-y-3">
        <div v-for="(task, i) in tasks" :key="i" class="space-y-3 rounded-md border p-3">
          <div class="flex items-center justify-between">
            <span class="text-xs font-medium text-gray-600">کار {{ i + 1 }}</span>
            <button v-if="tasks.length > 1" type="button" class="text-xs text-red-600" @click="tasks.splice(i, 1)">حذف</button>
          </div>
          <FormControl v-model="task.maintenance_task" type="text" label="نام کار" />
          <div class="grid grid-cols-2 gap-3">
            <FormControl v-model="task.maintenance_type" type="select" label="نوع" :options="typeOptions" />
            <FormControl v-model="task.periodicity" type="select" label="دوره تکرار" :options="periodicityOptions" />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <JalaliDateInput v-model="task.start_date" label="تاریخ شروع (جلالی)" />
            <FormControl v-model="task.assign_to" type="select" label="مسئول" :options="memberOptions" />
          </div>
        </div>
        <Button v-if="tasks.length < 5" @click="addTask">افزودن کار دیگر</Button>
      </div>

      <ErrorMessage :message="error" />
      <p v-if="detail" class="ltr text-xs text-gray-600">{{ detail }}</p>
      <div class="flex justify-end gap-2 pt-2">
        <Button type="button" @click="open = false">انصراف</Button>
        <Button variant="solid" :loading="saving" :disabled="!canSave" @click="save">ساخت برنامه</Button>
      </div>
    </div>
  </Dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Button, Dialog, ErrorMessage, FormControl, createResource, toast } from 'frappe-ui'
import { DialogDescription } from 'reka-ui'
import JalaliDateInput from '@/components/JalaliDateInput.vue'
import { callApi } from '@/api/client'
import { autoResource } from '@/api/resource'
import { friendlyError } from '@/utils/format'
import { todayIso } from '@/utils/today'

const props = defineProps({ modelValue: Boolean, asset: { type: String, required: true } })
const emit = defineEmits(['update:modelValue', 'created'])

const open = ref(props.modelValue)
watch(() => props.modelValue, (v) => (open.value = v))
watch(open, (v) => {
  emit('update:modelValue', v)
  if (v) reset()
})

const today = todayIso()
const TYPE_OPTIONS = [
  { label: 'یک نوع انتخاب کنید', value: '' },
  { label: 'نگهداری پیشگیرانه', value: 'Preventive Maintenance' },
  { label: 'کالیبراسیون', value: 'Calibration' },
]
const PERIODS = [
  { label: 'روزانه', value: 'Daily' }, { label: 'هفتگی', value: 'Weekly' },
  { label: 'ماهانه', value: 'Monthly' }, { label: 'فصلی', value: 'Quarterly' },
  { label: 'شش‌ماهه', value: 'Half-yearly' }, { label: 'سالانه', value: 'Yearly' },
  { label: 'دوساله', value: '2 Yearly' }, { label: 'سه‌ساله', value: '3 Yearly' },
]
const typeOptions = TYPE_OPTIONS
const periodicityOptions = [{ label: 'یک دوره انتخاب کنید', value: '' }, ...PERIODS]

const teams = autoResource(createResource, { url: 'asset_api.api.maintenance.list_teams', auto: true })
const teamName = ref('')
const tasks = ref([])
const saving = ref(false)
const error = ref('')
const detail = ref('')

const teamOptions = computed(() => [
  { label: 'یک تیم انتخاب کنید', value: '' },
  ...(teams.data || []).map((t) => ({ label: t.maintenance_team_name, value: t.name })),
])
const currentTeam = computed(() => (teams.data || []).find((t) => t.name === teamName.value))
const memberOptions = computed(() => [
  { label: 'یک نفر انتخاب کنید', value: '' },
  ...(currentTeam.value?.members || []).map((m) => ({ label: m.full_name || m.team_member, value: m.team_member })),
])

function blankTask() {
  return { maintenance_task: '', maintenance_type: '', periodicity: '', start_date: today, assign_to: '' }
}
function reset() {
  teamName.value = ''
  tasks.value = [blankTask()]
  error.value = detail.value = ''
}
function addTask() {
  tasks.value.push(blankTask())
}
function onTeamChange() {
  tasks.value.forEach((t) => (t.assign_to = ''))
}

const canSave = computed(() =>
  teamName.value && tasks.value.length > 0 && tasks.value.every((t) =>
    t.maintenance_task.trim() && t.maintenance_type && t.periodicity && t.start_date && t.assign_to
  )
)

async function save() {
  saving.value = true
  error.value = detail.value = ''
  try {
    const result = await callApi('asset_api.api.maintenance.create_plan', {
      asset: props.asset, maintenance_team: teamName.value, tasks: tasks.value,
    })
    toast.success('برنامه نگهداری ساخته شد.')
    open.value = false
    emit('created', result)
  } catch (e) {
    error.value = e.message
    detail.value = e.detail || ''
  } finally {
    saving.value = false
  }
}
</script>
