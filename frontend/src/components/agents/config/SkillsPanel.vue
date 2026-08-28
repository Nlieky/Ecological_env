<!-- frontend/src/components/agents/config/SkillsPanel.vue -->
<template>
  <div class="sk">
    <div class="sk-head">
      <div class="sk-t">技能 · {{ entityLabel }}</div>
      <div class="sk-a">
        <button class="btn" @click="showCreate = true">新建技能</button>
        <button class="btn" @click="showMarket = true">技能市场</button>
      </div>
    </div>

    <div class="sk-grid">
      <div v-for="s in skills" :key="s.name" class="sk-card" :class="{ editing: editing === s.name }">
        <div class="sk-cname">📘 {{ s.display_name }}</div>
        <div class="sk-cdesc" :title="s.description">{{ s.description || '（无描述）' }}</div>
        <div class="sk-cmeta">{{ s.scripts.length }} 个脚本 · 已启用</div>
        <div class="sk-cacts">
          <button class="btn xs" @click="openSkill(s.name)">{{ editing === s.name ? '收起' : '查看/编辑' }}</button>
          <button class="btn xs" @click="toggle(s.name, false)">禁用</button>
          <button class="btn xs danger" @click="del(s.name)">删除</button>
        </div>
      </div>
      <div v-for="s in disabledSkills" :key="s" class="sk-card disabled">
        <div class="sk-cname">📘 {{ s }}</div>
        <div class="sk-cmeta">已禁用</div>
        <div class="sk-cacts">
          <button class="btn xs" @click="toggle(s, true)">启用</button>
          <button class="btn xs danger" @click="del(s)">删除</button>
        </div>
      </div>
    </div>

    <!-- SKILL.md 编辑（复用身份文件编辑器的样式模式） -->
    <div v-if="editing" class="sk-ed">
      <div class="sk-edbar">
        <span class="sk-edpath">{{ editing }}/SKILL.md</span>
        <div>
          <button class="btn" @click="showDiff = true" :disabled="!dirty">diff 预览</button>
          <button class="btn primary" @click="save" :disabled="!dirty || saving">{{ saving ? '保存中…' : '保存(git 快照)' }}</button>
        </div>
      </div>
      <textarea v-model="content" class="sk-ta" spellcheck="false"></textarea>
      <div v-if="showDiff" class="sk-mask" @click.self="showDiff = false">
        <div class="sk-diffbox">
          <div class="sk-diffh">变更预览</div>
          <pre class="sk-diffp">{{ diffText }}</pre>
          <div class="sk-difff">
            <button class="btn" @click="showDiff = false">继续编辑</button>
            <button class="btn primary" @click="confirmSave">确认保存</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 新建向导 -->
    <div v-if="showCreate" class="sk-mask" @click.self="showCreate = false">
      <div class="sk-modal">
        <div class="sk-mh">新建技能</div>
        <div class="sk-mrow"><label>名称（[a-z0-9-]）</label><input v-model="createForm.name" class="sk-in" placeholder="my-skill" /></div>
        <div class="sk-mrow"><label>描述</label><input v-model="createForm.description" class="sk-in" placeholder="什么任务用这个技能" /></div>
        <div class="sk-mrow"><label>脚本骨架</label>
          <select v-model="createForm.skeleton" class="sk-sel">
            <option value="empty">空脚本</option>
            <option value="argparse">带参数解析模板</option>
          </select>
        </div>
        <div class="sk-mf">
          <button class="btn" @click="showCreate = false">取消</button>
          <button class="btn primary" @click="create">创建（git 快照）</button>
        </div>
      </div>
    </div>

    <!-- 市场 -->
    <div v-if="showMarket" class="sk-mask" @click.self="showMarket = false">
      <div class="sk-modal wide">
        <div class="sk-mh">技能市场（仓库内置模板库）</div>
        <div v-for="t in templates" :key="t.name" class="sk-tpl">
          <div>
            <div class="sk-tname">📦 {{ t.name }}</div>
            <div class="sk-tdesc">{{ t.description }}</div>
          </div>
          <button class="btn primary xs" @click="install(t.name)"
                  :disabled="installed.has(t.name)">{{ installed.has(t.name) ? '已安装' : '安装' }}</button>
        </div>
        <div class="sk-mf"><button class="btn" @click="showMarket = false">关闭</button></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentConfigService, type SkillItem, type TemplateItem } from '@/api/modules/agentConfig'

const props = defineProps<{ entity: string }>()

const skills = ref<SkillItem[]>([])
const templates = ref<TemplateItem[]>([])
const editing = ref('')
const content = ref('')
const original = ref('')
const saving = ref(false)
const showDiff = ref(false)
const showCreate = ref(false)
const showMarket = ref(false)
const createForm = ref({ name: '', description: '', skeleton: 'empty' })
const disabledSkills = ref<string[]>([])
const installed = computed(() => new Set(skills.value.map(s => s.name)))

const dirty = computed(() => content.value !== original.value)
const entityLabel = computed(() => props.entity === 'master' ? '主智能体' : props.entity)

const diffText = computed(() => {
  const oldL = original.value.split('\n'); const newL = content.value.split('\n')
  const out: string[] = []
  for (let i = 0; i < Math.max(oldL.length, newL.length); i++) {
    if (oldL[i] === newL[i]) out.push('  ' + (oldL[i] ?? ''))
    else {
      if (oldL[i] !== undefined) out.push('- ' + oldL[i])
      if (newL[i] !== undefined) out.push('+ ' + newL[i])
    }
  }
  return out.join('\n')
})

async function load() {
  const r: any = await agentConfigService.getSkills(props.entity)
  const d = r.data ?? r
  skills.value = d.skills
  templates.value = d.templates
}
watch(() => props.entity, () => { editing.value = ''; load() }, { immediate: true })

async function openSkill(name: string) {
  if (editing.value === name) { editing.value = ''; return }
  if (dirty.value && !await confirmLeave()) return
  const r: any = await agentConfigService.readSkillFile(props.entity, name)
  content.value = (r.data ?? r).content
  original.value = content.value
  editing.value = name
}

async function confirmLeave(): Promise<boolean> {
  try { await ElMessageBox.confirm('有未保存的编辑，离开将丢失。', '未保存', { type: 'warning' }); return true }
  catch { return false }
}

function save() { showDiff.value = true }

async function confirmSave() {
  saving.value = true
  try {
    const r: any = await agentConfigService.saveSkillFile({
      entity: props.entity, name: editing.value, content: content.value,
      message: window.prompt('快照说明（可留空）') ?? '',
    })
    const d = r.data ?? r
    original.value = content.value
    if (d.degraded) ElMessage.warning(`已保存，git 快照降级为 .bak`)
    else ElMessage.success(`已保存，快照 ${d.commit}`)
    showDiff.value = false
  } catch (e: any) { ElMessage.error('保存失败：' + (e?.message || e)) }
  finally { saving.value = false }
}

async function create() {
  try {
    await agentConfigService.createSkill({ entity: props.entity, ...createForm.value })
    ElMessage.success('技能已创建（git 快照）')
    showCreate.value = false
    createForm.value = { name: '', description: '', skeleton: 'empty' }
    await load()
    editing.value = ''
  } catch (e: any) { ElMessage.error('创建失败：' + (e?.response?.data?.detail || e?.message || e)) }
}

async function install(tpl: string) {
  try {
    await agentConfigService.installTemplate({ template: tpl, entity: props.entity })
    ElMessage.success(`已安装 ${tpl}`)
    await load()
  } catch (e: any) { ElMessage.error('安装失败：' + (e?.response?.data?.detail || e?.message || e)) }
}

async function toggle(name: string, enable: boolean) {
  try {
    if (enable) {
      await agentConfigService.enableSkill({ entity: props.entity, name })
      disabledSkills.value = disabledSkills.value.filter(n => n !== name)
    } else {
      await ElMessageBox.confirm(`禁用 ${name}？主智能体将看不到该技能。`, '禁用', { type: 'warning' })
      await agentConfigService.disableSkill({ entity: props.entity, name })
      skills.value = skills.value.filter(s => s.name !== name)
      disabledSkills.value.push(name)
      if (editing.value === name) editing.value = ''
    }
    ElMessage.success(enable ? '已启用' : '已禁用')
    await load()
  } catch (e: any) { if (e !== 'cancel') ElMessage.error('操作失败：' + (e?.message || e)) }
}

async function del(name: string) {
  try {
    await ElMessageBox.confirm(`删除技能 ${name}？可从 git 历史恢复。`, '删除', { type: 'warning' })
    await agentConfigService.deleteSkill(props.entity, name)
    skills.value = skills.value.filter(s => s.name !== name)
    disabledSkills.value = disabledSkills.value.filter(n => n !== name)
    ElMessage.success('已删除')
    await load()
  } catch (e: any) { if (e !== 'cancel') ElMessage.error('删除失败：' + (e?.message || e)) }
}
</script>

<style scoped>
.sk { max-width: 880px }
.sk-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px }
.sk-t { font-size: 15px; font-weight: 700 }
.sk-a { display: flex; gap: 8px }
.sk-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 10px }
.sk-card { border: 1px solid var(--brd); border-radius: 11px; padding: 13px; background: #fff }
.sk-card.disabled { opacity: .6; background: #f8fafc }
.sk-cname { font-size: 13.5px; font-weight: 700 }
.sk-cdesc { font-size: 11.5px; color: var(--text-secondary); margin-top: 4px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 32px }
.sk-cmeta { font-size: 10.5px; color: var(--text-muted); margin-top: 6px }
.sk-cacts { display: flex; gap: 6px; margin-top: 9px }
.sk-ed { margin-top: 16px; border: 1px solid var(--brd); border-radius: 11px; overflow: hidden }
.sk-edbar { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; border-bottom: 1px solid var(--brd) }
.sk-edpath { font-family: ui-monospace, monospace; font-size: 12.5px; font-weight: 600 }
.sk-ta { width: 100%; min-height: 320px; border: none; outline: none; resize: vertical; padding: 14px 16px;
  font-family: ui-monospace, Consolas, monospace; font-size: 12.5px; line-height: 1.65 }
.sk-mask { position: fixed; inset: 0; background: rgba(15,23,42,.35); display: grid; place-items: center; z-index: 50 }
.sk-modal { background: #fff; border-radius: 13px; padding: 18px; width: min(460px, 90vw) }
.sk-modal.wide { width: min(620px, 90vw) }
.sk-mh { font-weight: 700; font-size: 14px; margin-bottom: 14px }
.sk-mrow { display: flex; flex-direction: column; gap: 5px; margin-bottom: 11px }
.sk-mrow label { font-size: 11.5px; color: var(--text-muted) }
.sk-in { font-size: 12.5px; padding: 7px 10px; border: 1px solid var(--brd); border-radius: 7px;
  font-family: ui-monospace, monospace; outline: none }
.sk-sel { font-size: 12.5px; padding: 7px 10px; border: 1px solid var(--brd); border-radius: 7px }
.sk-mf { display: flex; justify-content: flex-end; gap: 9px; margin-top: 14px }
.sk-tpl { display: flex; justify-content: space-between; align-items: center; gap: 12px;
  padding: 11px 0; border-bottom: 1px dashed var(--brd) }
.sk-tname { font-family: ui-monospace, monospace; font-size: 12.5px; font-weight: 600 }
.sk-tdesc { font-size: 11.5px; color: var(--text-secondary); margin-top: 3px }
.sk-diffbox { background: #fff; border-radius: 13px; width: min(760px, 90vw); max-height: 80vh;
  display: flex; flex-direction: column }
.sk-diffh { padding: 13px 18px; font-weight: 700; border-bottom: 1px solid var(--brd) }
.sk-diffp { flex: 1; overflow: auto; margin: 0; padding: 14px 18px; font-size: 12px;
  font-family: ui-monospace, monospace; white-space: pre-wrap }
.sk-difff { padding: 12px 18px; display: flex; justify-content: flex-end; gap: 9px; border-top: 1px solid var(--brd) }
.btn { font-size: 12px; padding: 5px 13px; border-radius: 7px; border: 1px solid var(--brd);
  background: #fff; cursor: pointer; color: var(--text-secondary) }
.btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary) }
.btn.primary { background: var(--primary); color: #fff; border-color: var(--primary) }
.btn.xs { font-size: 11px; padding: 3px 9px }
.btn.danger:hover { border-color: #dc2626; color: #dc2626 }
.btn:disabled { opacity: .5; cursor: not-allowed }
</style>
