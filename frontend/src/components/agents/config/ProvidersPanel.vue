<!-- frontend/src/components/agents/config/ProvidersPanel.vue -->
<template>
  <div class="pv">
    <div class="pv-t">模型供应商
      <span class="pv-sub" v-if="currentDefault">已保存默认：{{ currentDefault }}（重启后加载）</span>
    </div>
    <p class="pv-meta">供应商编辑、启停、删除和默认选择保存后需重启加载；连接测试通过不代表运行中正在使用。</p>
    <div class="pv-grid">
      <div v-for="p in providers" :key="p.name" class="pv-card" :class="{ off: !p.enabled, def: p.name === currentDefault }">
        <div class="pv-head">
          <div class="pv-name">{{ p.name }}
            <span v-if="p.name === currentDefault" class="pv-badge def">默认</span>
            <span class="pv-badge" :class="p.tested_ok ? 'ok' : 'bad'">{{ p.tested_ok ? '✓ 已测通' : '未测通' }}</span>
            <span v-if="!p.enabled" class="pv-badge off">已禁用</span>
          </div>
        </div>
        <div class="pv-meta">{{ p.model }} · {{ p.base_url }}</div>
        <div class="pv-key">key: {{ p.api_key || '—' }}</div>
        <div class="pv-acts">
          <button class="btn xs" @click="test(p.name)" :disabled="testing === p.name">{{ testing === p.name ? '测试中…' : '测试连接' }}</button>
          <button class="btn xs primary" @click="setDefault(p.name)"
                  :disabled="!p.tested_ok || p.name === currentDefault">设为默认</button>
          <button class="btn xs" @click="openEdit(p)">编辑</button>
          <button class="btn xs" @click="toggleEnabled(p)">{{ p.enabled ? '禁用' : '启用' }}</button>
          <button class="btn xs danger" @click="del(p.name)">删除</button>
        </div>
        <div v-if="lastTest[p.name]" class="pv-test" :class="lastTest[p.name].ok ? 'ok' : 'bad'">
          {{ lastTest[p.name].ok ? `✓ 连通 ${lastTest[p.name].latency_ms}ms` : `✗ ${lastTest[p.name].error}` }}
        </div>
      </div>
    </div>
    <div class="pv-foot">
      <button class="btn" @click="openCreate">+ 新增供应商</button>
      <button class="btn primary" @click="$emit('restart')">一键重启 agent</button>
    </div>

    <div v-if="showForm" class="pv-mask" @click.self="closeForm">
      <div class="pv-modal">
        <div class="pv-mh">{{ form.name && isEdit ? '编辑供应商' : '新增供应商' }}</div>
        <div class="pv-mrow"><label>名称</label><input v-model="form.name" class="pv-in" :disabled="isEdit" placeholder="deepseek" /></div>
        <div class="pv-mrow"><label>base_url</label><input v-model="form.base_url" class="pv-in" placeholder="https://api.example.com/v1" /></div>
        <div class="pv-mrow"><label>model</label><input v-model="form.model" class="pv-in" placeholder="model-name" /></div>
        <div class="pv-mrow"><label>api_key（编辑留空=不修改）</label>
          <input v-model="form.api_key" type="password" class="pv-in" :placeholder="isEdit ? '•••（不修改请留空）' : 'sk-…'" /></div>
        <div class="pv-mf">
          <button class="btn" @click="closeForm">取消</button>
          <button class="btn primary" @click="save" :disabled="saving">{{ saving ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentConfigService, type ProviderRow } from '@/api/modules/agentConfig'
import { requireSuccess } from '@/composables/useConfigDraft'

defineEmits<{ (e: 'restart'): void }>()

const providers = ref<ProviderRow[]>([])
const eligible = ref<string[]>([])
const currentDefault = ref('')
const testing = ref('')
const lastTest = ref<Record<string, { ok: boolean; latency_ms?: number; error?: string | null }>>({})
const showForm = ref(false)
const isEdit = ref(false)
const saving = ref(false)
const form = ref({ name: '', base_url: '', model: '', api_key: '' })
const formBaseline = ref(JSON.stringify(form.value))
const dirty = computed(() => saving.value || (showForm.value && JSON.stringify(form.value) !== formBaseline.value))
defineExpose({ dirty })
function canDiscard() { return !dirty.value || window.confirm('有未保存的供应商编辑，确定丢弃？') }
function closeForm() { if (saving.value || !canDiscard()) return; showForm.value = false }

async function load() {
  const r: any = await agentConfigService.getProviders()
  requireSuccess(r)
  const d = r.data ?? r
  providers.value = d.providers
  eligible.value = d.eligible
  currentDefault.value = d.current_default
}
onMounted(() => load().catch(e => ElMessage.error('供应商读取失败：' + e.message)))

async function test(name: string) {
  testing.value = name
  try {
    const r: any = await agentConfigService.testProvider(name)
    lastTest.value[name] = r
    ElMessage[r.ok ? 'success' : 'warning'](r.ok ? `连通 ${r.latency_ms}ms` : `失败：${r.error}`)
    await load()
  } catch (e: any) { ElMessage.error('测试失败：' + (e?.message || e)) }
  finally { testing.value = '' }
}

async function setDefault(name: string) {
  try {
    requireSuccess(await agentConfigService.setDefaultProvider(name))
    ElMessage.success(`已设 ${name} 为默认（重启 agent 后生效）`)
    await load()
  } catch (e: any) { ElMessage.error('设置失败：' + (e?.response?.data?.detail || e?.message || e)) }
}

function openCreate() {
  if (saving.value || !canDiscard()) return
  isEdit.value = false
  form.value = { name: '', base_url: '', model: '', api_key: '' }
  formBaseline.value = JSON.stringify(form.value)
  showForm.value = true
}

function openEdit(p: ProviderRow) {
  if (saving.value || !canDiscard()) return
  isEdit.value = true
  form.value = { name: p.name, base_url: p.base_url, model: p.model, api_key: '' }
  formBaseline.value = JSON.stringify(form.value)
  showForm.value = true
}

async function save() {
  if (saving.value) return
  const captured = { ...form.value }
  saving.value = true
  try {
    requireSuccess(await agentConfigService.putProvider({
      ...captured, api_key: captured.api_key || undefined,
      enabled: isEdit.value ? (providers.value.find(p => p.name === captured.name)?.enabled ?? true) : true,
    }))
    ElMessage.success('供应商已保存，需重启加载')
    const unchanged = JSON.stringify(form.value) === JSON.stringify(captured)
    if (form.value.api_key === captured.api_key) form.value.api_key = ''
    formBaseline.value = JSON.stringify({ ...captured, api_key: '' })
    if (unchanged) showForm.value = false
    await load()
  } catch (e: any) { ElMessage.error('保存失败：' + (e?.message || e)) }
  finally { saving.value = false }
}

async function toggleEnabled(p: ProviderRow) {
  try {
  requireSuccess(await agentConfigService.putProvider({
    name: p.name, base_url: p.base_url, api_key: undefined, model: p.model, enabled: !p.enabled,
  }))
  ElMessage.success('启停配置已保存，需重启加载')
  await load()
  } catch (e: any) { ElMessage.error('保存失败：' + (e?.message || e)) }
}

async function del(name: string) {
  try {
    await ElMessageBox.confirm(`删除供应商 ${name}？${name === currentDefault.value ? ' 它是当前默认，删除后 agent 走 env 兜底！' : ''}`, '删除', { type: 'warning' })
    requireSuccess(await agentConfigService.deleteProvider(name))
    ElMessage.success('删除已保存，需重启加载')
    await load()
  } catch (e: any) { if (e !== 'cancel') ElMessage.error('删除失败：' + (e?.message || e)) }
}
</script>

<style scoped>
.pv { max-width: 880px }
.pv-t { font-size: 15px; font-weight: 700; display: flex; align-items: center; gap: 10px }
.pv-sub { font-size: 11.5px; color: #047857; background: #ecfdf5; padding: 3px 9px; border-radius: 6px; font-weight: 400 }
.pv-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 10px; margin-top: 14px }
.pv-card { border: 1px solid var(--brd); border-radius: 11px; padding: 13px; background: #fff }
.pv-card.off { opacity: .65; background: #f8fafc }
.pv-card.def { border-color: var(--primary); box-shadow: 0 0 0 1px var(--primary) }
.pv-name { font-size: 13.5px; font-weight: 700; display: flex; align-items: center; gap: 6px; flex-wrap: wrap }
.pv-badge { font-size: 10px; padding: 2px 7px; border-radius: 5px; font-weight: 600 }
.pv-badge.ok { background: #ecfdf5; color: #047857 }
.pv-badge.bad { background: #fef2f2; color: #dc2626 }
.pv-badge.off { background: #f1f5f9; color: var(--text-muted) }
.pv-badge.def { background: #eef2ff; color: var(--primary) }
.pv-meta { font-size: 11.5px; color: var(--text-secondary); margin-top: 6px; font-family: ui-monospace, monospace }
.pv-key { font-size: 11px; color: var(--text-muted); margin-top: 3px; font-family: ui-monospace, monospace }
.pv-acts { display: flex; gap: 6px; margin-top: 9px; flex-wrap: wrap }
.pv-test { font-size: 11.5px; margin-top: 7px }
.pv-test.ok { color: #047857 }
.pv-test.bad { color: #dc2626 }
.pv-foot { display: flex; gap: 9px; margin-top: 14px }
.pv-mask { position: fixed; inset: 0; background: rgba(15,23,42,.35); display: grid; place-items: center; z-index: 50 }
.pv-modal { background: #fff; border-radius: 13px; padding: 18px; width: min(460px, 90vw) }
.pv-mh { font-weight: 700; font-size: 14px; margin-bottom: 14px }
.pv-mrow { display: flex; flex-direction: column; gap: 5px; margin-bottom: 11px }
.pv-mrow label { font-size: 11.5px; color: var(--text-muted) }
.pv-in { font-size: 12.5px; padding: 7px 10px; border: 1px solid var(--brd); border-radius: 7px;
  font-family: ui-monospace, monospace; outline: none }
.pv-in:disabled { background: #f8fafc }
.pv-mf { display: flex; justify-content: flex-end; gap: 9px; margin-top: 14px }
.btn { font-size: 12px; padding: 5px 13px; border-radius: 7px; border: 1px solid var(--brd);
  background: #fff; cursor: pointer; color: var(--text-secondary) }
.btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary) }
.btn.primary { background: var(--primary); color: #fff; border-color: var(--primary) }
.btn.xs { font-size: 11px; padding: 3px 9px }
.btn.danger:hover { border-color: #dc2626; color: #dc2626 }
.btn:disabled { opacity: .5; cursor: not-allowed }
</style>
