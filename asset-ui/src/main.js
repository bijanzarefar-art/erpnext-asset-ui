import { createApp } from 'vue'
import { FrappeUI, setConfig, frappeRequest } from 'frappe-ui'
import router from './router'
import App from './App.vue'
import './style.css'

setConfig('resourceFetcher', frappeRequest)

createApp(App).use(router).use(FrappeUI).mount('#app')
