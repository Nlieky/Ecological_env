<template>
  <div class="pp">
    <div v-if="restartHint" class="pp-hint">
      ⚠ 有「需重启」参数已保存。<button class="btn primary" @click="$emit('restart')">一键重启 agent</button>
    </div>
    <div class="pp-sec-t">运行参数（{{ params.length }}）</div>
    <div class="pp-grid">
      <div v-for="p in params" :key="p.key" class="pp-row">
        <div class="pp-k">
          <div class="pp-key">{{ p.key }}</div>
          <div class="pp-desc">{{ p.desc }} · 读取方 {{ p.reader }}</div>
        </div>
        <div class="pp-v">
          <input v-model="draft[p.key]" :type="p.type === 'secret' ? 'password' : 'text'"
                 class="pp-in" :placeholder="`默认 ${p.default}`" />
        </div>
        <span class="pp-eff" :class="p.effect">{{ p.effect === 'restart' ? '需重启' : '立即生效' }}</span>
      </div>
    </div>
    <div class="pp-foot">
      <button class="btn primary" @click="save" :disabled="saving || loading">{{ saving ? '保存中…' : '保存参数' }}</button>
    </div>

    <div class="pp-sec-t" style="margin-top: 26px">LLM 连接测试</div>
    <div class="pp-llm">
      <div class="pp-row">
        <div class="pp-k"><div class="pp-key">测试目标</div><div class="pp-desc">留空 = 用当前生效配置直测</div></div>
        <div class="pp-v"><input v-model="llmDraft.base_url" class="pp-in" placeholder="base_url（空=当前）" /></div>
      </div>
      <div class="pp-row">
        <div class="pp-k"><div class="pp-key"></div></div>
        <div class="pp-v"><input v-model="llmDraft.model" class="pp-in" placeholder="model（空=当前）" /></div>
      </div>
      <div class="pp-row">
        <div class="pp-k"><div class="pp-key"></div></div>
        <div class="pp-v"><input v-model="llmDraft.api_key" type="password" class="pp-in" placeholder="api_key（空=当前）" /></div>
      </div>
      <div class="pp-foot">
        <button class="btn" @click="testLlm" :disabled="testing">{{ testing ? '测试中…' : '测试连接' }}</button>
        <span v-if="llmResult" class="pp-res" :class="llmResult.ok ? 'ok' : 'bad'">
          {{ llmResult.ok ? `✓ 连通 ${llmResult.latency_ms}ms` : `✗ ${llmResult.error}` }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { agentConfigService, type ParamItem } from '@/api/modules/agentConfig'

defineEmits<{ (e: 'restart'): void }>()

const params = ref<ParamItem[]>([])
const draft = ref<Record<string, string>>({})
const loading = ref(false)
const saving = ref(false)
const restartHint = ref(false)
const testing = ref(false)
const llmResult = ref<{ ok: boolean; latency_ms?: number; error?: string | null } | null>(null)
const llmDraft = ref({ base_url: '', model: '', api_key: '' })

async function load() {
  loading.value = true
  try {
    const r: any = await agentConfigService.getParams()
    params.value = (r?.data ?? r) as ParamItem[]
    params.value.forEach(p => { draft.value[p.key] = String(p.value ?? '') })
  } catch (e: any) {
    ElMessage.error('参数读取失败：' + (e?.message || e))
  } finally { loading.value = false }
}
onMounted(load)

async function save() {
  saving.value = true
  try {
    // 只提交有变化的（GET 回的 secret 已是脱敏值，用户不动即字符串相等不提交；
    // 改动了则提交明文；改回空串也不提交——后端把 secret 空值跳过，防误清库）
    const payload: Record<string, string> = {}
    params.value.forEach(p => {
      const v = draft.value[p.key] ?? ''
      if (v !== String(p.value ?? '')) payload[p.key] = v
    })
    if (!Object.keys(payload).length) { ElMessage.info('无改动'); return }
    const r: any = await agentConfigService.saveParams(payload)
    restartHint.value = !!r?.restart_needed
    ElMessage.success(r?.restart_needed ? '已保存——部分参数需重启 agent 生效' : '已保存（立即生效）')
    await load() // 重拉：重建 diff 基线（secret 换成新脱敏值）
  } catch (e: any) {
    ElMessage.error('保存失败：' + (e?.message || JSON.stringify(e?.response?.data) || e))
  } finally { saving.value = false }
}

async function testLlm() {
  testing.value = true; llmResult.value = null
  try {
    llmResult.value = await agentConfigService.llmTest({
      base_url: llmDraft.value.base_url || undefined,
      model: llmDraft.value.model || undefined,
      api_key: llmDraft.value.api_key || undefined,
    }) as any
  } catch (e: any) { llmResult.value = { ok: false, error: e?.message || String(e) } }
  finally { testing.value = false }
}
</script>

<style scoped>
.pp { max-width: 820px }
.pp-hint { background: #fffbeb; border: 1px solid #fde68a; color: #92400e; border-radius: 10px;
  padding: 10px 14px; font-size: 12.5px; margin-bottom: 16px; display: flex; align-items: center; gap: 12px }
.pp-sec-t { font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 12px;
  display: flex; align-items: center; gap: 8px }
.pp-sec-t::before { content: ''; width: 3px; height: 14px; background: var(--primary); border-radius: 2px }
.pp-grid { border: 1px solid var(--brd); border-radius: 11px; overflow: hidden }
.pp-row { display: flex; align-items: center; gap: 14px; padding: 10px 14px; border-bottom: 1px solid var(--brd) }
.pp-row:last-child { border-bottom: none }
.pp-k { flex: 1; min-width: 0 }
.pp-key { font-family: ui-monospace, monospace; font-size: 12.5px; font-weight: 600; color: var(--text-primary) }
.pp-desc { font-size: 11px; color: var(--text-muted); margin-top: 2px }
.pp-v { width: 280px }
.pp-in { width: 100%; font-size: 12.5px; padding: 6px 10px; border: 1px solid var(--brd);
  border-radius: 7px; font-family: ui-monospace, monospace; outline: none; box-sizing: border-box }
.pp-in:focus { border-color: var(--primary) }
.pp-eff { font-size: 10.5px; padding: 2px 9px; border-radius: 6px; flex-shrink: 0 }
.pp-eff.immediate { color: #047857; background: #ecfdf5 }
.pp-eff.restart { color: #92400e; background: #fffbeb }
.pp-foot { padding: 12px 2px; display: flex; align-items: center; gap: 12px }
.btn { font-size: 12px; padding: 6px 14px; border-radius: 7px; border: 1px solid var(--brd);
  background: #fff; cursor: pointer; color: var(--text-secondary) }
.btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary) }
.btn.primary { background: var(--primary); color: #fff; border-color: var(--primary) }
.btn:disabled { opacity: .5; cursor: not-allowed }
.pp-res { font-size: 12px }
.pp-res.ok { color: #047857 }
.pp-res.bad { color: #dc2626 }
.pp-llm { border: 1px solid var(--brd); border-radius: 11px; padding: 4px 0 }
</style>
