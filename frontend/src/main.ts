import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import App from './App.vue'
import router from './router'
import './assets/main.css'
import './styles/tokens.css'

const app = createApp(App)
const pinia = createPinia()

// Register all Element Plus icons
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(pinia)
app.use(router)
app.use(ElementPlus, { locale: zhCn })

// Set page title
router.afterEach((to) => {
  const title = typeof to.meta?.title === 'string' && to.meta.title.trim()
    ? `${to.meta.title} - 废水监测系统`
    : '废水监测智能体系统'
  document.title = title
})

app.mount('#app')
