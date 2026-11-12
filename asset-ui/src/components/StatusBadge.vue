<template>
  <Badge :label="meta.label" :theme="meta.theme" variant="subtle" />
</template>

<script setup>
import { computed } from 'vue'
import { Badge } from 'frappe-ui'
import { statusMeta } from '@/utils/format'

const props = defineProps({ status: String })
const meta = computed(() => statusMeta(props.status))
</script>
