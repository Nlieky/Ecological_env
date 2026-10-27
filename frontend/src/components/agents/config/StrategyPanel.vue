<!-- frontend/src/components/agents/config/StrategyPanel.vue -->
<template>
  <div class="sp">
    <p class="sp-desc">保存的配置不等于正在运行的配置；需重启项在明确重启后加载。</p>
    <div v-if="assistantDiff.length" class="sp-hint" role="status">
      <div><b>助手建议草稿（尚未应用或保存）</b><div v-for="row in assistantDiff" :key="row.key">{{ row.key }}：{{ row.before }} → {{ row.after }}</div></div>
      <button class="btn primary" @click="applyAssistantDraft">应用到编辑表单</button>
      <button class="btn" @click="assistantDiff = []">取消</button>
    </div>
    <div v-if="restartHint" class="sp-hint">
      ⚠ 有「需重启」配置已保存。<button class="btn primary" @click="$emit('restart')">一键重启 agent</button>
    </div>
    <template v-for="(items, g) in groups" :key="g">
      <div class="sp-sec-t">{{ GROUP_LABELS[g] || g }}</div>
      <div class="sp-grid">
        <div v-for="it in items" :key="it.key" class="sp-row">
          <div class="sp-k">
            <div class="sp-key">{{ it.key }}</div>
            <div class="sp-desc">{{ it.desc }} · {{ it.read_timing }}</div>
          </div>
          <div class="sp-v">
            <el-switch v-if="it.type === 'bool'" v-model="draft[it.key] as boolean" />
            <el-select v-else-if="it.type === 'enum'" v-model="draft[it.key] as string" style="width: 200px">
              <el-option v-for="c in it.choices" :key="c" :label="c" :value="c" />
            </el-select>
            <el-input-number v-else-if="it.type === 'int'" v-model="draft[it.key] as number" />
            <el-input v-else-if="it.type === 'ref'" v-model="draft[it.key] as string"
                      placeholder="在供应商 tab 测试通过后选择" style="width: 220px" />
            <el-input v-else v-model="draft[it.key] as string" type="textarea" :rows="3"
                      :placeholder="`默认：${String(it.default).slice(0, 40)}…`" />
          </div>
          <span class="sp-eff" :class="it.effect">{{ it.effect === 'restart' ? '需重启' : '下一次适用读取' }}</span>
        </div>
      </div>
    </template>

    <div class="sp-sec-t">运行参数</div>
    <div class="sp-grid">
      <div v-for="p in params" :key="p.key" class="sp-row">
        <div class="sp-k">
          <div class="sp-key">{{ p.key }}</div>
          <div class="sp-desc">{{ p.desc }} · {{ p.read_timing }}</div>
        </div>
        <div class="sp-v">
          <el-input v-if="p.type === 'secret'" v-model="paramDraft[p.key] as string" type="password" show-password
                    style="width: 220px" :placeholder="`当前 ${p.value}`" />
          <el-input-number v-else-if="p.type === 'int'" v-model="paramDraft[p.key] as number" />
          <el-input v-else v-model="paramDraft[p.key] as string" style="width: 220px" />
        </div>
        <span class="sp-eff" :class="p.effect">{{ p.effect === 'restart' ? '需重启' : '下一次适用读取' }}</span>
      </div>
    </div>
    <div class="sp-foot">
      <button class="btn primary" @click="saveStrategy" :disabled="saving">保存策略</button>
      <button class="btn" @click="saveParams" :disabled="savingParams">保存参数</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { agentConfigService, type StrategyItem, type ParamItem } from '@/api/modules/agentConfig'
import { useConfigDraft, requireSuccess } from '@/composables/useConfigDraft'
import { validateAssistantAction } from '@/assistant/capabilities'

defineEmits<{ (e: 'restart'): void }>()

const GROUP_LABELS: Record<string, string> = {
  orchestration: '编排深度', guard: '守卫与自愈', style: '回答风格',
  action: '动作通道', provider: '默认模型供应商',
}
const groups = ref<Record<string, StrategyItem[]>>({})
const params = ref<ParamItem[]>([])
const strategyState = useConfigDraft()
const paramState = useConfigDraft()
const draft = strategyState.draft
const paramDraft = paramState.draft
const assistantDiff = ref<{ key: string; before: unknown; after: unknown }[]>([])
const dirty = computed(() => strategyState.dirty.value || paramState.dirty.value || assistantDiff.value.length > 0)
let initialLoad: Promise<void> | null = null
async function prepareAssistantDraft(values: Record<string, unknown>) {
  if (initialLoad) await initialLoad
  if (dirty.value) return { success: false, code: 'draft_conflict', message: '已有未保存编辑或未应用的助手草稿，请先保存、应用或取消，不会覆盖现有内容' }
  const valid = validateAssistantAction({ capability: 'strategy.draft', parameters: values })
  if (!valid.success) return valid
  const fields = Object.values(groups.value).flat()
  if (Object.keys(values).some(key => !fields.some(field => field.key === key))) return { success: false, message: '策略字段schema尚未加载，无法生成草稿' }
  assistantDiff.value = Object.entries(values).map(([key, after]) => ({ key, before: draft.value[key], after }))
  return { success: true, message: '已生成非敏感策略差异，请在配置页应用到表单后使用原保存按钮' }
}
function applyAssistantDraft() {
  if (strategyState.dirty.value || paramState.dirty.value) { ElMessage.warning('表单已有未保存修改，请先处理这些修改，助手草稿仍保留'); return }
  if (assistantDiff.value.some(row => draft.value[row.key] !== row.before)) { ElMessage.warning('原字段已修改，请重新准备草稿'); return }
  for (const row of assistantDiff.value) draft.value[row.key] = row.after as string | number | boolean
  assistantDiff.value = []
}
defineExpose({ dirty, prepareAssistantDraft })
const saving = ref(false)
const savingParams = ref(false)
const restartHint = computed(() => strategyState.restartHint.value || paramState.restartHint.value)

onMounted(() => { initialLoad = loadStrategy() })
async function loadStrategy() {
  try {
  const r: any = await agentConfigService.getStrategy()
  requireSuccess(r)
  const d = r.data ?? r
  groups.value = d.groups
  params.value = d.params
  strategyState.initialize(Object.values(d.groups as Record<string, StrategyItem[]>).flat())
  paramState.initialize(d.params)
  } catch (e: any) { ElMessage.error('配置读取失败：' + (e?.message || e)) }
}

async function saveStrategy() {
  saving.value = true
  try {
    const payload = strategyState.payload()
    if (!Object.keys(payload).length) { ElMessage.info('策略无改动'); return }
    const r: any = await agentConfigService.saveStrategy(payload)
    strategyState.acknowledge(payload, r)
    ElMessage.success(r.restart_needed ? '已保存——部分策略需重启生效' : '已保存，下一次适用读取时使用；未保存项仍保留')
  } catch (e: any) {
    const errs = e?.response?.data?.detail?.errors
    ElMessage.error('保存失败：' + (errs?.join('；') || e?.message || e))
  } finally { saving.value = false }
}

async function saveParams() {
  savingParams.value = true
  try {
    const payload = paramState.payload() as Record<string, string | number>
    if (!Object.keys(payload).length) { ElMessage.info('参数无改动'); return }
    const r: any = await agentConfigService.saveParams(payload)
    paramState.acknowledge(payload, r)
    ElMessage.success(r.restart_needed ? '已保存——部分参数需重启生效' : '已保存，下一次适用读取时使用；未保存项仍保留')
  } catch (e: any) { ElMessage.error('保存失败：' + (e?.message || e)) }
  finally { savingParams.value = false }
}
</script>

<style scoped>
.sp { max-width: 860px }
.sp-hint { background: #fffbeb; border: 1px solid #fde68a; color: #92400e; border-radius: 10px;
  padding: 10px 14px; font-size: 12.5px; margin-bottom: 16px; display: flex; align-items: center; gap: 12px }
.sp-sec-t { font-size: 13px; font-weight: 700; margin: 18px 0 10px; display: flex; align-items: center; gap: 8px }
.sp-sec-t::before { content: ''; width: 3px; height: 14px; background: var(--primary); border-radius: 2px }
.sp-grid { border: 1px solid var(--brd); border-radius: 11px; overflow: hidden }
.sp-row { display: flex; align-items: center; gap: 14px; padding: 10px 14px; border-bottom: 1px solid var(--brd) }
.sp-row:last-child { border-bottom: none }
.sp-k { flex: 1; min-width: 0 }
.sp-key { font-family: ui-monospace, monospace; font-size: 12.5px; font-weight: 600 }
.sp-desc { font-size: 11px; color: var(--text-muted); margin-top: 2px }
.sp-v { flex-shrink: 0 }
.sp-eff { font-size: 10.5px; padding: 2px 9px; border-radius: 6px; flex-shrink: 0 }
.sp-eff.immediate { color: #047857; background: #ecfdf5 }
.sp-eff.restart { color: #92400e; background: #fffbeb }
.sp-foot { padding: 14px 2px; display: flex; gap: 10px }
.btn { font-size: 12.5px; padding: 6px 15px; border-radius: 7px; border: 1px solid var(--brd);
  background: #fff; cursor: pointer; color: var(--text-secondary) }
.btn.primary { background: var(--primary); color: #fff; border-color: var(--primary) }
.btn:disabled { opacity: .5; cursor: not-allowed }
</style>
