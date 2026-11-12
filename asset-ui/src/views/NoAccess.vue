<template>
  <NoAccess>
    <p v-if="from" class="mt-2 text-xs text-gray-500">
      مسیر درخواستی: <span class="ltr">{{ from }}</span>
    </p>
  </NoAccess>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import NoAccess from '@/components/NoAccess.vue'

const route = useRoute()
const from = computed(() => (typeof route.query.from === 'string' ? route.query.from : ''))
</script>
