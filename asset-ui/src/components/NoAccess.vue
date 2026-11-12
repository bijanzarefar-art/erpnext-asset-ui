<template>
  <div class="mx-auto max-w-md rounded-lg border bg-white p-6 text-center">
    <h1 class="text-lg font-semibold">دسترسی ندارید</h1>
    <p class="mt-2 text-sm text-gray-600">{{ message }}</p>
    <slot />
    <div class="mt-4 flex justify-center gap-2">
      <router-link to="/dashboard"><Button>بازگشت به داشبورد</Button></router-link>
    </div>
  </div>
</template>

<script setup>
import { Button } from 'frappe-ui'

defineProps({
  message: {
    type: String,
    default: 'حساب شما اجازه دیدن این بخش را ندارد. اگر فکر می‌کنید اشتباهی رخ داده، با مدیر سیستم تماس بگیرید.',
  },
})
</script>
