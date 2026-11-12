<template>
  <div class="min-h-screen bg-gray-50 text-gray-900 md:flex">
    <!-- In RTL the first flex child sits on the right: that is the sidebar side -->
    <aside class="md:w-60 shrink-0 border-b md:border-b-0 md:border-e bg-white">
      <div class="px-4 py-4 text-lg font-semibold">دارایی‌ها</div>
      <nav class="px-2 pb-2 space-y-1">
        <router-link
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          class="block rounded-md px-3 py-2 text-sm hover:bg-gray-100"
          active-class="bg-gray-100 font-medium"
        >
          {{ item.label }}
        </router-link>
      </nav>
      <div class="border-t px-4 py-3 text-xs text-gray-600 md:mt-auto">
        <div class="ltr truncate">{{ session.user }}</div>
        <button class="mt-1 text-gray-900 underline" @click="doLogout">خروج</button>
      </div>
    </aside>
    <main class="flex-1 min-w-0 p-4 md:p-6">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { session, logout } from '@/api/session'

const router = useRouter()
const allNav = [
  { to: '/dashboard', label: 'داشبورد', needs: 'asset_list' },
  { to: '/asset-list', label: 'فهرست دارایی‌ها', needs: 'asset_list' },
  { to: '/asset/new', label: 'ثبت دارایی جدید', needs: 'asset_create' },
]
// Hide entries the caller cannot use. The server still enforces every call.
const nav = computed(() => allNav.filter((i) => session.features[i.needs]))

async function doLogout() {
  await logout()
  router.replace({ name: 'Login' })
}
</script>
