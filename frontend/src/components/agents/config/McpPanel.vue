<!-- frontend/src/components/agents/config/McpPanel.vue -->
<template>
  <div class="mp">
    <div class="mp-t">外部 MCP 接入 <span class="mp-sub">改动需重启 agent 生效</span></div>

    <!-- 市场：npm 搜索（MCP server 事实上的分发中心） -->
    <div class="mp-sec-t">市场 <span class="mp-market-hint">搜索 npm 上的 MCP server</span></div>
    <div class="mp-market">
      <input v-model="marketQuery" class="mp-in mk" placeholder="搜 MCP，如：地图 / chart / playwright / hotnews"
             @keyup.enter="searchMarket" />
      <button class="btn primary xs" @click="searchMarket" :disabled="mkSearching">
        {{ mkSearching ? '搜索中…' : '搜索' }}
      </button>
    </div>
    <div v-if="mkError" class="mp-mkerr">{{ mkError }}</div>
    <div v-if="marketResults.length" class="mp-mklist">
      <div v-for="m in marketResults" :key="m.name" class="mp-mkrow">
        <div class="mp-mkk">
          <div class="mp-mkname">{{ m.name }} <span class="mp-mkver">v{{ m.version }}</span></div>
          <div class="mp-mkdesc" :title="m.description">{{ m.description }}</div>
        </div>
        <button class="btn xs primary" @click="installFromMarket(m)"
                :disabled="mkInstalling === m.name || installedPkgs.has(m.name)">
          {{ mkInstalling === m.name ? '安装中…' : installedPkgs.has(m.name) ? '已安装' : '安装' }}
        </button>
      </div>
    </div>
    <div v-else-if="mkSearched && !mkSearching" class="mp-empty">没有匹配的 MCP 包，换个关键词试试</div>

    <div class="mp-sec-t">预置（一键安装）</div>
    <div class="mp-grid">
      <div v-for="p in presets" :key="p.name" class="mp-card">
        <div class="mp-name">{{ p.title }} <span class="mp-badge">{{ p.transport }}</span></div>
        <div class="mp-desc">{{ p.desc }}</div>
        <div class="mp-acts">
          <button class="btn primary xs" @click="installPreset(p.name)"
                  :disabled="servers[p.name] !== undefined">已安装·管理见下</button>
          <button class="btn xs" @click="testCfg(p.config, p.name)">测试连接</button>
        </div>
      </div>
    </div>

    <div class="mp-sec-t">已接入</div>
    <div v-if="!Object.keys(servers).length" class="mp-empty">暂无接入（上方预置一键安装，或点「新增接入」）</div>
    <div v-for="(cfg, name) in servers" :key="name" class="mp-row">
      <div class="mp-rk">
        <div class="mp-rname">{{ name }}
          <span class="mp-badge" :class="{ off: cfg.enabled === false }">{{ cfg.enabled === false ? '已停用' : '启用' }}</span>
        </div>
        <div class="mp-rmeta">{{ cfg.command || cfg.url }} {{ (cfg.args || []).join(' ') }}</div>
      </div>
      <div class="mp-racts">
        <span v-if="lastTest[name]" class="mp-test" :class="lastTest[name].ok ? 'ok' : 'bad'">
          {{ lastTest[name].ok ? `✓ ${lastTest[name].tools_seen} 工具` : `✗ ${lastTest[name].error}` }}
        </span>
        <button class="btn xs" @click="testCfg(cfg, name)" :disabled="testing === name">{{ testing === name ? '测试中…' : '测试连接' }}</button>
        <button class="btn xs" @click="toggleEnabled(name, cfg)">{{ cfg.enabled === false ? '启用' : '停用' }}</button>
        <button class="btn xs danger" @click="del(name)">删除</button>
      </div>
    </div>
    <div class="mp-foot">
      <button class="btn" @click="showAdd = true">+ 新增接入</button>
      <button class="btn primary" @click="$emit('restart')">一键重启 agent</button>
    </div>

    <div v-if="showAdd" class="mp-mask" @click.self="closeAdd">
      <div class="mp-modal">
        <div class="mp-mh">新增 MCP 接入</div>
        <div class="mp-mrow"><label>名称</label><input v-model="addForm.name" class="mp-in" placeholder="my-server" /></div>
        <div class="mp-mrow"><label>传输方式</label>
          <select v-model="addForm.transport" class="mp-sel">
            <option value="stdio">stdio（command + args）</option>
            <option value="http">HTTP（url）</option>
            <option value="sse">SSE（url）</option>
          </select>
        </div>
        <template v-if="addForm.transport === 'stdio'">
          <div class="mp-mrow"><label>command</label><input v-model="addForm.command" class="mp-in" placeholder="npx" /></div>
          <div class="mp-mrow"><label>args（空格分隔）</label><input v-model="addForm.argsStr" class="mp-in" placeholder="-y @modelcontextprotocol/server-xxx" /></div>
        </template>
        <template v-else>
          <div class="mp-mrow"><label>url</label><input v-model="addForm.url" class="mp-in" placeholder="https://…/mcp" /></div>
        </template>
        <div class="mp-mrow"><label>超时(秒)</label><input v-model.number="addForm.timeout" type="number" class="mp-in" /></div>
        <div class="mp-mf">
          <button class="btn" @click="testAdd">测试连接</button>
          <button class="btn" @click="closeAdd">取消</button>
          <button class="btn primary" @click="add" :disabled="adding || !addForm.name || testedAdd !== true">保存（需测试通过）</button>
        </div>
        <div v-if="lastAddTest" class="mp-test" :class="lastAddTest.ok ? 'ok' : 'bad'">
          {{ lastAddTest.ok ? `✓ 握手成功，发现 ${lastAddTest.tools_seen} 工具` : `✗ ${lastAddTest.error}` }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentConfigService, type McpServerCfg, type McpPreset, type McpMarketItem } from '@/api/modules/agentConfig'
import { requireSuccess } from '@/composables/useConfigDraft'

defineEmits<{ (e: 'restart'): void }>()

const servers = ref<Record<string, McpServerCfg>>({})
const presets = ref<McpPreset[]>([])
const testing = ref('')
const lastTest = ref<Record<string, { ok: boolean; tools_seen?: number; error?: string | null }>>({})
const showAdd = ref(false)
const addForm = ref({ name: '', transport: 'stdio', command: 'npx', argsStr: '', url: '', timeout: 60 })
const testedAdd = ref<null | boolean>(null)
const lastAddTest = ref<{ ok: boolean; tools_seen?: number; error?: string | null } | null>(null)
const addBaseline = ref(JSON.stringify(addForm.value))
const adding = ref(false)
const dirty = computed(() => adding.value || (showAdd.value && JSON.stringify(addForm.value) !== addBaseline.value))
defineExpose({ dirty })
watch(addForm, () => { testedAdd.value = null; lastAddTest.value = null }, { deep: true, flush: 'sync' })
function closeAdd() {
  if (adding.value || (dirty.value && !window.confirm('有未保存的 MCP 编辑，确定丢弃？'))) return
  showAdd.value = false
  addForm.value = { name: '', transport: 'stdio', command: 'npx', argsStr: '', url: '', timeout: 60 }
  addBaseline.value = JSON.stringify(addForm.value)
}

// ── 市场 ──
const marketQuery = ref('')
const marketResults = ref<McpMarketItem[]>([])
const mkSearching = ref(false)
const mkSearched = ref(false)
const mkError = ref('')
const mkInstalling = ref('')
const installedPkgs = ref(new Set<string>())

async function reloadServers() {
  const r: any = await agentConfigService.getMcp()
  requireSuccess(r)
  const d = r.data ?? r
  servers.value = d.servers
  // 已安装包名集合（args 里含该包名的即视为已装）
  const pkgs = new Set<string>()
  Object.values(d.servers as Record<string, McpServerCfg>).forEach((c) => {
    (c.args || []).forEach(a => { if (typeof a === 'string' && !a.startsWith('-')) pkgs.add(a) })
  })
  installedPkgs.value = pkgs
}

async function searchMarket() {
  if (!marketQuery.value.trim()) return
  mkSearching.value = true; mkError.value = ''; marketResults.value = []
  try {
    const r: any = await agentConfigService.mcpMarketSearch(marketQuery.value.trim())
    marketResults.value = (r.data ?? r) as McpMarketItem[]
    mkSearched.value = true
  } catch (e: any) {
    mkError.value = '搜索失败：' + (e?.message || e)
  } finally { mkSearching.value = false }
}

async function installFromMarket(m: McpMarketItem) {
  mkInstalling.value = m.name
  try {
    await agentConfigService.mcpMarketInstall(m.name)
    ElMessage.success(`已安装 ${m.name}（需测试连接 + 重启生效）`)
    await reloadServers()
  } catch (e: any) {
    ElMessage.error('安装失败：' + (e?.response?.data?.detail || e?.message || e))
  } finally { mkInstalling.value = '' }
}

onMounted(() => reloadServers().catch(e => ElMessage.error('MCP 读取失败：' + e.message)))

function buildCfg(): McpServerCfg {
  const f = addForm.value
  const cfg: McpServerCfg = { timeout: f.timeout }
  if (f.transport === 'stdio') {
    cfg.command = f.command
    cfg.args = f.argsStr.split(/\s+/).filter(Boolean)
  } else {
    cfg.url = f.url
    cfg.transport = f.transport
  }
  return cfg
}

async function testCfg(cfg: McpServerCfg, name: string) {
  testing.value = name
  try {
    const r: any = await agentConfigService.testMcp(cfg)
    lastTest.value[name] = r
    ElMessage[r.ok ? 'success' : 'warning'](r.ok ? `握手成功，发现 ${r.tools_seen} 工具` : `失败：${r.error}`)
  } catch (e: any) { ElMessage.error('测试请求失败：' + (e?.message || e)) }
  finally { testing.value = '' }
}

async function installPreset(name: string) {
  try {
    requireSuccess(await agentConfigService.installMcpPreset(name))
    ElMessage.success(`已安装 ${name}（需重启生效）`)
    const r: any = await agentConfigService.getMcp()
    servers.value = (r.data ?? r).servers
  } catch (e: any) { ElMessage.error('安装失败：' + (e?.message || e)) }
}

async function toggleEnabled(name: string, cfg: McpServerCfg) {
  const next = { ...cfg, enabled: cfg.enabled === false }
  try {
    requireSuccess(await agentConfigService.putMcp({ name, config: next }))
    servers.value[name] = next
    ElMessage.success('启停配置已保存，需重启加载')
  } catch (e: any) { ElMessage.error('操作失败：' + (e?.message || e)) }
}

async function del(name: string) {
  try {
    await ElMessageBox.confirm(`删除 MCP 接入 ${name}？`, '删除', { type: 'warning' })
    requireSuccess(await agentConfigService.deleteMcp(name))
    delete servers.value[name]
    ElMessage.success('已删除（需重启生效）')
  } catch (e: any) { if (e !== 'cancel') ElMessage.error('删除失败：' + (e?.message || e)) }
}

async function testAdd() {
  const captured = JSON.stringify(addForm.value)
  lastAddTest.value = null; testedAdd.value = null
  try {
    const r: any = await agentConfigService.testMcp(buildCfg())
    if (captured !== JSON.stringify(addForm.value)) return
    lastAddTest.value = r
    testedAdd.value = r.ok
  } catch (e: any) { lastAddTest.value = { ok: false, error: e?.message || String(e) } }
}

async function add() {
  if (adding.value || testedAdd.value !== true) return
  const captured = JSON.stringify(addForm.value)
  adding.value = true
  try {
    requireSuccess(await agentConfigService.putMcp({ name: addForm.value.name, config: buildCfg() }))
    ElMessage.success('已保存（需重启生效）')
    addBaseline.value = captured
    if (JSON.stringify(addForm.value) === captured) showAdd.value = false
    testedAdd.value = null; lastAddTest.value = null
    const r: any = await agentConfigService.getMcp()
    servers.value = (r.data ?? r).servers
  } catch (e: any) {
    const errs = e?.response?.data?.detail?.errors
    ElMessage.error('保存失败：' + (errs?.join('；') || e?.message || e))
  } finally { adding.value = false }
}
</script>

<style scoped>
.mp { max-width: 880px }
.mp-t { font-size: 15px; font-weight: 700 }
.mp-sub { font-size: 11.5px; color: #92400e; background: #fffbeb; padding: 3px 9px; border-radius: 6px; margin-left: 8px; font-weight: 400 }
.mp-sec-t { font-size: 13px; font-weight: 700; margin: 18px 0 10px; display: flex; align-items: center; gap: 8px }
.mp-sec-t::before { content: ''; width: 3px; height: 14px; background: var(--primary); border-radius: 2px }
.mp-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 10px }
/* 市场 */
.mp-market-hint { font-size: 11px; color: var(--text-muted); font-weight: 400; margin-left: 8px }
.mp-market { display: flex; gap: 8px; margin-bottom: 10px }
.mp-market .mk { flex: 1; max-width: 460px }
.mp-mkerr { font-size: 12px; color: #dc2626; margin-bottom: 8px }
.mp-mklist { border: 1px solid var(--brd); border-radius: 10px; margin-bottom: 6px }
.mp-mkrow { display: flex; align-items: center; gap: 12px; padding: 9px 13px; border-bottom: 1px solid var(--brd) }
.mp-mkrow:last-child { border-bottom: none }
.mp-mkk { flex: 1; min-width: 0 }
.mp-mkname { font-family: ui-monospace, monospace; font-size: 12.5px; font-weight: 600 }
.mp-mkver { font-size: 10px; color: var(--text-muted); font-weight: 400; margin-left: 5px }
.mp-mkdesc { font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
.mp-card { border: 1px solid var(--brd); border-radius: 11px; padding: 13px; background: #fff }
.mp-name { font-size: 13.5px; font-weight: 700 }
.mp-badge { font-size: 10px; background: #eef2ff; color: var(--primary); padding: 2px 7px; border-radius: 5px; margin-left: 6px; font-weight: 600 }
.mp-badge.off { background: #f1f5f9; color: var(--text-muted) }
.mp-desc { font-size: 11.5px; color: var(--text-secondary); margin-top: 4px }
.mp-acts { display: flex; gap: 6px; margin-top: 9px }
.mp-empty { font-size: 12.5px; color: var(--text-muted); padding: 14px 0 }
.mp-row { display: flex; align-items: center; gap: 14px; padding: 11px 14px; border: 1px solid var(--brd); border-radius: 10px; margin-bottom: 8px }
.mp-rk { flex: 1; min-width: 0 }
.mp-rname { font-family: ui-monospace, monospace; font-size: 13px; font-weight: 600 }
.mp-rmeta { font-size: 11px; color: var(--text-muted); margin-top: 3px; font-family: ui-monospace, monospace;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
.mp-racts { display: flex; align-items: center; gap: 7px; flex-shrink: 0 }
.mp-test { font-size: 11.5px; max-width: 240px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
.mp-test.ok { color: #047857 }
.mp-test.bad { color: #dc2626 }
.mp-foot { display: flex; gap: 9px; margin-top: 14px }
.mp-mask { position: fixed; inset: 0; background: rgba(15,23,42,.35); display: grid; place-items: center; z-index: 50 }
.mp-modal { background: #fff; border-radius: 13px; padding: 18px; width: min(480px, 90vw) }
.mp-mh { font-weight: 700; font-size: 14px; margin-bottom: 14px }
.mp-mrow { display: flex; flex-direction: column; gap: 5px; margin-bottom: 11px }
.mp-mrow label { font-size: 11.5px; color: var(--text-muted) }
.mp-in { font-size: 12.5px; padding: 7px 10px; border: 1px solid var(--brd); border-radius: 7px;
  font-family: ui-monospace, monospace; outline: none }
.mp-sel { font-size: 12.5px; padding: 7px 10px; border: 1px solid var(--brd); border-radius: 7px }
.mp-mf { display: flex; justify-content: flex-end; gap: 9px; margin-top: 14px }
.btn { font-size: 12px; padding: 5px 13px; border-radius: 7px; border: 1px solid var(--brd);
  background: #fff; cursor: pointer; color: var(--text-secondary) }
.btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary) }
.btn.primary { background: var(--primary); color: #fff; border-color: var(--primary) }
.btn.xs { font-size: 11px; padding: 3px 9px }
.btn.danger:hover { border-color: #dc2626; color: #dc2626 }
.btn:disabled { opacity: .5; cursor: not-allowed }
</style>
