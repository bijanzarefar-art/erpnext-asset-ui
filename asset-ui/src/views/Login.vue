<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 px-4">
    <form class="w-full max-w-sm rounded-xl bg-white p-6 shadow-sm space-y-4" @submit.prevent="submit">
      <h1 class="text-xl font-semibold text-gray-900">ورود به مدیریت دارایی‌ها</h1>
      <FormControl v-model="usr" label="نام کاربری یا ایمیل" type="text" autocomplete="username" class="ltr" />
      <FormControl v-model="pwd" label="گذرواژه" type="password" autocomplete="current-password" class="ltr" />
      <ErrorMessage :message="error" />
      <Button variant="solid" class="w-full" type="submit" :loading="loading">ورود</Button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, FormControl, ErrorMessage } from 'frappe-ui'
import { login } from '@/api/session'

const route = useRoute()
const router = useRouter()
const usr = ref('')
const pwd = ref('')
const loading = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await login(usr.value, pwd.value)
    // Only follow an in-app path; anything else (array, absolute or protocol-relative URL) goes home
    const target = route.query.redirect
    const safe = typeof target === 'string' && target.startsWith('/') && !target.startsWith('//')
    router.replace(safe ? target : { name: 'Dashboard' })
  } catch (e) {
    error.value = e.status === 401 ? 'نام کاربری یا گذرواژه نادرست است.' : 'ورود انجام نشد. دوباره تلاش کنید.'
  } finally {
    loading.value = false
  }
}
</script>
