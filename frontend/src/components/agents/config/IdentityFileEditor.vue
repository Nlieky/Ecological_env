<template>
  <div class="ed">
    <!-- 左栏：文件列表 + 历史版本 -->
    <div class="ed-list">
      <div class="ed-lh">身份文件</div>
      <div v-for="f in entity.identity_files" :key="f" class="ed-fi"
           :class="{ active: file === f, dirty: dirty && file === f }" @click="openFile(f)">
        {{ f }}<span v-if="dirty && file === f" class="dot">●</span>
      </div>
      <div class="ed-lh hist">历史版本（点击回滚）</div>
      <div v-if="!history.length" class="ed-empty">暂无 git 历史</div>
      <div v-for="h in history" :key="h.commit + h.date" class="ed-hi" @click="revert(h)">
        <div class="ed-hc">{{ h.commit }}</div>
        <div class="ed-hm" :title="h.message">{{ h.message }}</div>
        <div class="ed-hd">{{ h.date.slice(0, 16).replace('T', ' ') }}</div>
      </div>
    </div>
    <!-- 编辑区 -->
    <div class="ed-main" v-if="file">
      <div class="ed-bar">
        <span class="ed-path">{{ file }} <span class="ed-meta">{{ sizeLabel }}</span>
          <span v-if="loading" class="ed-meta">读取中…</span></span>
        <div class="ed-acts">
          <button class="btn" @click="showDiff = true" :disabled="!dirty">diff 预览</button>
          <button class="btn primary" @click="save" :disabled="!dirty || saving">
            {{ saving ? '保存中…' : '保存（git 快照）' }}
          </button>
        </div>
      </div>
      <textarea v-model="content" class="ed-ta" spellcheck="false"
                :readonly="loading"></textarea>
    </div>
    <div v-else class="ed-none">← 选择一个身份文件</div>
    <!-- diff 弹窗 -->
    <div v-if="showDiff" class="ed-mask" @click.self="showDiff = false">
      <div class="ed-diff">
        <div class="ed-dh">变更预览（保存前确认）</div>
        <div class="ed-dp">
          <div v-for="(l, i) in diffLines" :key="i" class="dl"
               :class="lineCls(l)">{{ l }}</div>
        </div>
        <div class="ed-df">
          <button class="btn" @click="showDiff = false">继续编辑</button>
          <button class="btn primary" @click="confirmSave" :disabled="saving">确认保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 身份文件编辑器：左栏文件列表+git 历史版本，右栏编辑区。
// 保存流程：diff 预览 → 确认 → 快照说明(prompt) → PUT saveFile（后端原子写+git 快照）；
// 回滚流程：点历史条目 → 确认 → POST revertFile（git checkout <commit> -- <file>）。
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentConfigService } from '@/api/modules/agentConfig'
import type { AgentEntity, FileHistoryItem } from '@/api/modules/agentConfig'

const props = defineProps<{ entity: AgentEntity }>()

const file = ref('')
const content = ref('')
const original = ref('')
const loading = ref(false)
const saving = ref(false)
const history = ref<FileHistoryItem[]>([])
const showDiff = ref(false)

// 切实体时暂存未保存草稿（见底部 watch），重开同一文件时恢复
const drafts = new Map<string, string>()

const dirty = computed(() => content.value !== original.value)
defineExpose({ dirty, openFile }) // 父组件（AgentConfigView）骨架契约

const sizeLabel = computed(() =>
  `${(content.value.length / 1024).toFixed(1)} KB · ${content.value.split('\n').length} 行`)

// ── 简易行级 diff：同下标对齐比对（LCS 太重，md 场景够用）。
// 展示只保留变更行 ±2 行上下文，避免整份文件在弹窗里刷屏。
const diffLines = computed(() => {
  const oldL = original.value.split('\n')
  const newL = content.value.split('\n')
  const marks: string[] = []
  let changed = 0
  const n = Math.max(oldL.length, newL.length)
  for (let i = 0; i < n; i++) {
    if (oldL[i] === newL[i]) {
      marks.push('  ' + (oldL[i] ?? ''))
    } else {
      if (oldL[i] !== undefined) { marks.push('- ' + oldL[i]); changed++ }
      if (newL[i] !== undefined) { marks.push('+ ' + newL[i]); changed++ }
    }
  }
  const isChg = (s: string) => s[0] === '-' || s[0] === '+'
  const keep = new Array(marks.length).fill(false) as boolean[]
  marks.forEach((m, i) => {
    if (isChg(m)) {
      for (let j = Math.max(0, i - 2); j <= Math.min(marks.length - 1, i + 2); j++) keep[j] = true
    }
  })
  const out = [`@@ 变更 ${changed} 行 · ${oldL.length} → ${newL.length} 行 @@`]
  let prevKept = false
  marks.forEach((m, i) => {
    if (keep[i]) { out.push(m); prevKept = true }
    else if (prevKept) { out.push('  ⋯'); prevKept = false }
  })
  return out
})

function lineCls(l: string) {
  if (l[0] === '+') return 'add'
  if (l[0] === '-') return 'del'
  if (l[0] === '@') return 'hdr'
  return ''
}

async function openFile(f: string) {
  if (dirty.value && !await confirmLeave()) return
  file.value = f
  loading.value = true
  try {
    const r: any = await agentConfigService.readFile(props.entity.name, f)
    const d = (r as any).data ?? r
    // 切实体时暂存的草稿优先恢复（服务器内容作为 diff 基准）
    const key = `${props.entity.name}/${f}`
    const draft = drafts.get(key)
    drafts.delete(key)
    if (draft !== undefined && draft !== d.content) {
      original.value = d.content
      content.value = draft
      ElMessage.info('已恢复上次未保存的编辑')
    } else {
      content.value = d.content
      original.value = d.content
    }
    await loadHistory()
  } catch {
    // 拦截器已弹错；回到空态，避免旧内容挂在新文件名下
    file.value = ''
    content.value = ''
    original.value = ''
  } finally {
    loading.value = false
  }
}

async function loadHistory() {
  try {
    const r: any = await agentConfigService.fileHistory(props.entity.name, file.value)
    history.value = ((r as any).data ?? r) as FileHistoryItem[]
  } catch {
    history.value = []
  }
}

async function confirmLeave(): Promise<boolean> {
  try {
    await ElMessageBox.confirm('有未保存的编辑，离开将丢失。', '未保存', { type: 'warning' })
    return true
  } catch { return false }
}

function save() { showDiff.value = true }

async function confirmSave() {
  if (!file.value) return
  // 快照说明：ElMessageBox.prompt（取消≠中断——按空说明继续保存）
  let message = ''
  try {
    const { value } = await ElMessageBox.prompt('快照说明（可留空）', '保存', {
      inputPlaceholder: '可选，如：调严异常告警语气',
    })
    message = (value ?? '').trim()
  } catch { /* 用户取消：空说明继续 */ }
  saving.value = true
  try {
    const r: any = await agentConfigService.saveFile({
      entity: props.entity.name, file: file.value, content: content.value, message,
    })
    const d = (r as any).data ?? r
    original.value = content.value
    if (d.no_change) {
      ElMessage.info('内容未变化，未产生新快照')
    } else if (d.degraded) {
      ElMessage.warning(`已保存，但 git 快照降级为 .bak（${d.detail || 'git 不可用'}）`)
    } else {
      ElMessage.success(`已保存，快照 ${d.commit}`)
    }
    showDiff.value = false
    await loadHistory()
  } catch {
    /* 拦截器已弹错；diff 弹窗保留，可重试 */
  } finally {
    saving.value = false
  }
}

async function revert(h: FileHistoryItem) {
  if (!file.value) return
  const tip = h.message.length > 30 ? h.message.slice(0, 30) + '…' : h.message
  const extra = dirty.value ? '（当前未保存的修改将被覆盖）' : ''
  try {
    await ElMessageBox.confirm(`回滚到 ${h.commit}（${tip}）？${extra}`, '回滚', { type: 'warning' })
  } catch { return }
  try {
    const r: any = await agentConfigService.revertFile({
      entity: props.entity.name, file: file.value, commit: h.commit,
    })
    const d = (r as any).data ?? r
    content.value = d.content
    original.value = d.content
    ElMessage.success(`已回滚到 ${h.commit}`)
    await loadHistory()
  } catch {
    /* 拦截器已弹错 */
  }
}

// 切实体：编辑器实例被复用（父级无 :key），dirty 内容先存草稿再清空——
// 实体树切换发生在父组件、无法被本组件拦截，草稿保证切回后重开同一文件不丢内容。
watch(() => props.entity.name, (_nv, ov) => {
  if (dirty.value && file.value) drafts.set(`${ov}/${file.value}`, content.value)
  file.value = ''
  content.value = ''
  original.value = ''
  history.value = []
})
</script>

<style scoped>
.ed { display: flex; height: 100%; gap: 0 }
.ed-list { width: 230px; flex-shrink: 0; border-right: 1px solid var(--brd); overflow: auto; padding: 12px }
.ed-lh { font-size: 11px; color: var(--text-muted); letter-spacing: .5px; margin: 4px 0 8px }
.ed-lh.hist { margin-top: 12px }
.ed-fi { font-size: 12.5px; font-family: ui-monospace, monospace; padding: 7px 10px; border-radius: 7px;
  cursor: pointer; color: var(--text-secondary); position: relative }
.ed-fi:hover { background: #f1f5f9 }
.ed-fi.active { background: var(--primary-soft, #eef2ff); color: var(--primary); font-weight: 600 }
.ed-fi.dirty { color: #b45309 }
.ed-fi .dot { position: absolute; right: 9px; color: #f59e0b }
.ed-empty { font-size: 11.5px; color: var(--text-muted); padding: 6px 4px }
.ed-hi { padding: 7px 10px; border-radius: 7px; cursor: pointer; border: 1px solid transparent }
.ed-hi:hover { background: #f8fafc; border-color: var(--brd) }
.ed-hc { font-family: ui-monospace, monospace; font-size: 11px; color: var(--primary); font-weight: 600 }
.ed-hm { font-size: 11px; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 190px }
.ed-hd { font-size: 10px; color: var(--text-muted) }
.ed-main { flex: 1; min-width: 0; display: flex; flex-direction: column }
.ed-bar { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; border-bottom: 1px solid var(--brd) }
.ed-path { font-family: ui-monospace, monospace; font-size: 12.5px; font-weight: 600; color: var(--text-primary) }
.ed-meta { font-weight: 400; font-size: 11px; color: var(--text-muted); margin-left: 8px }
.ed-acts { display: flex; gap: 8px }
.btn { font-size: 12px; padding: 5px 13px; border-radius: 7px; border: 1px solid var(--brd);
  background: #fff; cursor: pointer; color: var(--text-secondary) }
.btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary) }
.btn.primary { background: var(--primary); color: #fff; border-color: var(--primary) }
.btn.primary:hover:not(:disabled) { color: #fff; opacity: .9 }
.btn:disabled { opacity: .5; cursor: not-allowed }
.ed-ta { flex: 1; width: 100%; border: none; outline: none; resize: none; padding: 14px 16px;
  font-family: ui-monospace, Consolas, monospace; font-size: 12.5px; line-height: 1.65; color: var(--text-primary) }
.ed-none { flex: 1; display: grid; place-items: center; color: var(--text-muted); font-size: 13px }
.ed-mask { position: fixed; inset: 0; background: rgba(15,23,42,.35); display: grid; place-items: center; z-index: 50 }
.ed-diff { background: #fff; border-radius: 13px; width: min(760px, 90vw); max-height: 80vh;
  display: flex; flex-direction: column; box-shadow: 0 20px 60px rgba(0,0,0,.2) }
.ed-dh { padding: 13px 18px; font-weight: 700; font-size: 14px; border-bottom: 1px solid var(--brd) }
.ed-dp { flex: 1; overflow: auto; margin: 0; padding: 12px 18px; font-size: 12px; line-height: 1.6;
  font-family: ui-monospace, monospace }
.dl { white-space: pre-wrap; word-break: break-word; border-radius: 3px; padding: 0 4px }
.dl.add { color: #15803d; background: #f0fdf4 }
.dl.del { color: #b91c1c; background: #fef2f2 }
.dl.hdr { color: var(--text-muted); margin: 6px 0 2px }
.ed-df { padding: 12px 18px; display: flex; justify-content: flex-end; gap: 9px; border-top: 1px solid var(--brd) }
</style>
