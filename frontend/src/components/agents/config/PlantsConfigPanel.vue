<template>
  <div class="pc">
    <!-- 页头：标题+说明+统计徽标+操作（独立页外壳只给容器，标题在此唯一出现） -->
    <div class="pc-h">
      <div class="pc-hl">
        <div class="pc-t">🏢 厂区配置</div>
        <div class="pc-sub">层级 / 别名 / 报表映射 / 单厂参数 · 保存即 git 快照，监测大屏目录树即时生效</div>
      </div>
      <div class="pc-a">
        <span class="pc-stat" title="市/厂区/厂的数量">{{ statText }}</span>
        <button class="btn" @click="validate" :disabled="saving">校验</button>
        <button class="btn primary" @click="save" :disabled="saving || !loaded">{{ saving ? '保存中…' : '保存' }}</button>
      </div>
    </div>
    <div v-if="errors.length" class="pc-errs">
      <div v-for="(e, i) in errors" :key="i" class="pc-err">⚠ {{ e }}</div>
    </div>

    <!-- 层级：市→厂区→厂 -->
    <div class="pc-sec">
      <div class="pc-st"><span class="pc-ic">🗺️</span>多厂层级<span class="pc-sth">市 → 厂区 → 厂（厂名须与 InfluxDB plant_id 一致）</span></div>
      <div v-for="(zones, city) in cfg.hierarchy" :key="city" class="pc-city">
        <div class="pc-cityh">
          <span class="pc-cn"><span class="pc-dot city">📍</span>{{ city }}</span>
          <span class="pc-count">{{ zoneCount(city) }} 个厂区 · {{ plantCount(city) }} 家厂</span>
          <button class="btn xs danger" @click="delCity(city)">删除</button>
        </div>
        <div v-for="(plants, zone) in zones" :key="zone" class="pc-zone">
          <div class="pc-zoneh">
            <span class="pc-zn">{{ zone }}</span>
            <button class="btn xs ghost" @click="addPlant(city, zone)">+ 添加厂</button>
            <button class="btn xs danger" @click="delZone(city, zone)">删除</button>
          </div>
          <div class="pc-plants">
            <span v-for="(p, i) in plants" :key="p + i" class="pc-plant">
              <span class="pc-dot" />{{ p }}
              <button class="pc-x" @click="delPlant(city, zone, i)" title="移除">×</button>
            </span>
            <button v-if="!plants.length" class="pc-plant add" @click="addPlant(city, zone)">+ 添加厂</button>
          </div>
        </div>
        <button class="btn xs ghost" @click="addZone(city)">+ 厂区</button>
      </div>
      <button class="btn ghost" @click="addCity">+ 市</button>
    </div>

    <!-- 别名表 -->
    <div class="pc-sec">
      <div class="pc-st"><span class="pc-ic">💬</span>厂名别名<span class="pc-sth">用户口语怎么叫 → 实际 plant_id（智能体解析用户提问用）</span></div>
      <div class="pc-kv">
        <template v-for="k in Object.keys(cfg.plant_aliases)" :key="k">
          <input class="pc-in k" :value="k" placeholder="如：金桥"
                 @change="renameAlias(k, ($event.target as HTMLInputElement).value)" />
          <span class="pc-arrow">→</span>
          <input class="pc-in v" :value="cfg.plant_aliases[k]" placeholder="plant_id 全称"
                 @input="cfg.plant_aliases[k] = ($event.target as HTMLInputElement).value" />
          <button class="pc-x" @click="delAlias(k)">×</button>
        </template>
      </div>
      <div v-if="!Object.keys(cfg.plant_aliases).length" class="pc-empty">暂无别名——用户说简称时智能体会找不到厂</div>
      <button class="btn xs ghost" @click="addAlias">+ 别名</button>
    </div>

    <!-- 报表映射 -->
    <div class="pc-sec">
      <div class="pc-st"><span class="pc-ic">📄</span>报表文件名映射<span class="pc-sth">命名不规范的报表在这里登记（文件名主体 → plant_id）</span></div>
      <div class="pc-kv">
        <template v-for="k in Object.keys(cfg.report_name_map)" :key="k">
          <input class="pc-in k" :value="k" disabled title="改名请删除重加" />
          <span class="pc-arrow">→</span>
          <input class="pc-in v" :value="cfg.report_name_map[k]" placeholder="plant_id 全称"
                 @input="cfg.report_name_map[k] = ($event.target as HTMLInputElement).value" />
          <button class="pc-x" @click="delReport(k)">×</button>
        </template>
      </div>
      <div v-if="!Object.keys(cfg.report_name_map).length" class="pc-empty">暂无映射——监测点名含"排放口"等会被启发式剥残的报表在此登记</div>
      <button class="btn xs ghost" @click="addReport">+ 映射</button>
    </div>

    <!-- per-plant 配置 -->
    <div class="pc-sec">
      <div class="pc-st"><span class="pc-ic">🏷️</span>单厂参数<span class="pc-sth">显示名 / 类型（看板树与大屏展示用）</span></div>
      <div v-for="pid in Object.keys(cfg.plant_configs)" :key="pid" class="pc-pconf">
        <div class="pc-pid"><span class="pc-dot" />{{ pid }}</div>
        <div class="pc-pf">
          <label>显示名
            <input class="pc-in" :value="pcGet(pid, 'display_name')" placeholder="看板树里显示的短名"
                   @input="pcSet(pid, 'display_name', ($event.target as HTMLInputElement).value)" /></label>
          <label>类型
            <input class="pc-in" :value="pcGet(pid, 'type')" placeholder="如：市政污水处理 / 船舶洗舱废水"
                   @input="pcSet(pid, 'type', ($event.target as HTMLInputElement).value)" /></label>
        </div>
      </div>
      <div class="pc-pick">
        <select v-model="addPid" class="pc-sel"><option value="">选择厂添加参数…</option>
          <option v-for="p in allPlants" :key="p" :value="p">{{ p }}</option></select>
        <button class="btn xs" @click="addPlantConfig" :disabled="!addPid">添加</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 厂区配置面板：层级(市→厂区→厂) / 别名表 / 报表映射 / 单厂配置 四段编辑，
// 校验(POST validate, 不落盘) + 保存(PUT, 后端再校验+yaml 原子写+git 快照)。
// 错误处理惯例同 IdentityFileEditor：axios 拦截器已弹通用错误，
// 这里只把 400 校验的字段级 errors 渲染到页面错误区（不算双重提示）。
import { ref, computed, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentConfigService, type PlantConfig } from '@/api/modules/agentConfig'

const cfg = reactive<PlantConfig>({ hierarchy: {}, report_name_map: {}, plant_configs: {}, plant_aliases: {} })
const errors = ref<string[]>([])
const saving = ref(false)
const addPid = ref('')
// 加载成功才允许保存：load 失败时 cfg 是空骨架，此时保存会把空配置写盘——
// 整厂层级/别名/报表映射全被擦掉。拦截器只弹通用错误，这里补 disabled 硬闸。
const loaded = ref(false)

// 层级里出现过的所有厂（plant_configs 添加下拉的选项源）
const allPlants = computed(() => {
  const s: string[] = []
  Object.values(cfg.hierarchy).forEach(zones => Object.values(zones).forEach(ps => s.push(...ps)))
  return [...new Set(s)]
})

async function load() {
  try {
    const r: any = await agentConfigService.getPlants()
    Object.assign(cfg, (r as any).data ?? r)
    loaded.value = true
  } catch (e: any) {
    // 拦截器弹的是通用网络错误，这里明确告知"没加载到就不能保存"
    ElMessage.error('厂区配置加载失败：保存已禁用（防误擦除）— ' + (e?.message || e))
  }
}

async function validate() {
  try {
    const r: any = await agentConfigService.validatePlants({ ...cfg })
    errors.value = ((r as any).errors ?? []) as string[]
    if (errors.value.length) ElMessage.warning(`发现 ${errors.value.length} 个问题`)
    else ElMessage.success('校验通过')
  } catch { /* axios 拦截器已弹错 */ }
}

async function save() {
  saving.value = true
  try {
    const r: any = await agentConfigService.savePlants({ ...cfg })
    Object.assign(cfg, (r as any).data ?? r)
    errors.value = [] // 保存通过=校验已过，清掉旧错误
    ElMessage.success('厂区配置已保存（自动 git 快照）')
  } catch (e: any) {
    // 拦截器已弹通用错误（detail.message）；这里只把字段级校验错误展示到页面
    const errs = e?.response?.data?.detail?.errors
    if (Array.isArray(errs)) errors.value = errs as string[]
  } finally { saving.value = false }
}

/** ElMessageBox.prompt 包装：取消返回 null（调用方跳过操作）；返回 trim 后的输入 */
async function ask(title: string, dflt = ''): Promise<string | null> {
  try {
    const { value } = await ElMessageBox.prompt(title, '厂区配置', { inputValue: dflt })
    return (value ?? '').trim()
  } catch { return null }
}

async function addCity() {
  const name = await ask('市名（如 枝江市）'); if (!name) return
  if (cfg.hierarchy[name]) { ElMessage.warning(`「${name}」已存在`); return }
  cfg.hierarchy[name] = {}
}
function delCity(c: string) { delete cfg.hierarchy[c] }
async function addZone(c: string) {
  const name = await ask('厂区名'); if (!name) return
  if (cfg.hierarchy[c][name]) { ElMessage.warning(`「${name}」已存在`); return }
  cfg.hierarchy[c][name] = []
}
function delZone(c: string, z: string) { delete cfg.hierarchy[c][z] }
async function addPlant(c: string, z: string) {
  const name = await ask('厂名（必须与 InfluxDB plant_id 完全一致）'); if (!name) return
  if (cfg.hierarchy[c][z].includes(name)) { ElMessage.warning(`「${name}」已存在`); return }
  cfg.hierarchy[c][z].push(name)
}
function delPlant(c: string, z: string, i: number) { cfg.hierarchy[c][z].splice(i, 1) }
async function addAlias() {
  const k = await ask('别名（用户会怎么说，如 金桥）'); if (!k) return
  if (cfg.plant_aliases[k] !== undefined) { ElMessage.warning(`「${k}」已存在`); return }
  cfg.plant_aliases[k] = ''
}
function delAlias(k: string) { delete cfg.plant_aliases[k] }
function renameAlias(oldK: string, newK: string) {
  const k = newK.trim()
  if (!k || k === oldK) return // 空/未改名：保留原键（防误删）
  if (cfg.plant_aliases[k] !== undefined) { // 改名撞上已有键：直接覆盖会静默丢掉对方的值
    ElMessage.warning(`「${k}」已存在`); return
  }
  const v = cfg.plant_aliases[oldK]
  delete cfg.plant_aliases[oldK]
  cfg.plant_aliases[k] = v
}
async function addReport() {
  const k = await ask('报表文件名主体'); if (!k) return
  if (cfg.report_name_map[k] !== undefined) { ElMessage.warning(`「${k}」已存在`); return }
  cfg.report_name_map[k] = ''
}
function delReport(k: string) { delete cfg.report_name_map[k] }

// 统计徽标文本（市/厂区/厂数量）
const statText = computed(() => {
  const cities = Object.keys(cfg.hierarchy).length
  let zones = 0, plants = 0
  Object.values(cfg.hierarchy).forEach(z => {
    zones += Object.keys(z).length
    Object.values(z).forEach(ps => plants += ps.length)
  })
  return `${cities} 市 · ${zones} 厂区 · ${plants} 厂`
})
function zoneCount(city: string) { return Object.keys(cfg.hierarchy[city] || {}).length }
function plantCount(city: string) {
  return Object.values(cfg.hierarchy[city] || {}).reduce((n, ps) => n + (ps as string[]).length, 0)
}

// plant_configs 值是 Record<string, unknown>，模板直连 v-model 过不了类型检查——经这对 helper 存取
function pcGet(pid: string, field: string): string {
  return String(cfg.plant_configs[pid]?.[field] ?? '')
}
function pcSet(pid: string, field: string, v: string) {
  if (!cfg.plant_configs[pid]) cfg.plant_configs[pid] = { display_name: '', type: '' }
  cfg.plant_configs[pid][field] = v
}

function addPlantConfig() {
  if (!addPid.value) return
  if (!cfg.plant_configs[addPid.value]) cfg.plant_configs[addPid.value] = { display_name: '', type: '' }
  addPid.value = ''
}

onMounted(load)
</script>

<style scoped>
.pc { max-width: 960px }
/* 页头 */
.pc-h { display: flex; justify-content: space-between; align-items: center; gap: 14px;
  padding-bottom: 14px; margin-bottom: 16px; border-bottom: 1px solid var(--brd) }
.pc-hl { min-width: 0 }
.pc-t { font-size: 17px; font-weight: 700; color: var(--text-primary) }
.pc-sub { font-size: 12px; color: var(--text-muted); margin-top: 4px }
.pc-a { display: flex; align-items: center; gap: 9px; flex-shrink: 0 }
.pc-stat { font-size: 11.5px; color: var(--primary); background: var(--primary-soft, #eef2ff);
  padding: 4px 11px; border-radius: 999px; font-weight: 600; white-space: nowrap }
.pc-errs { background: #fef2f2; border: 1px solid #fecaca; border-radius: 10px; padding: 10px 14px; margin-bottom: 14px }
.pc-err { font-size: 12px; color: #dc2626 }
/* 区块 */
.pc-sec { border: 1px solid var(--brd); border-radius: 13px; padding: 16px 18px; margin-bottom: 16px; background: #fff }
.pc-st { font-size: 13.5px; font-weight: 700; color: var(--text-primary); margin-bottom: 14px;
  display: flex; align-items: center; gap: 8px }
.pc-st::after { content: ''; flex: 1 }
.pc-ic { font-size: 15px }
.pc-sth { font-size: 11px; color: var(--text-muted); font-weight: 400; margin-left: -2px; order: 9 }
/* 市卡片 */
.pc-city { margin-bottom: 12px; padding: 12px 14px; border: 1px solid var(--brd);
  border-radius: 11px; background: #fafcff }
.pc-cityh { display: flex; align-items: center; gap: 12px; margin-bottom: 10px }
.pc-cn { font-weight: 700; font-size: 14px; color: var(--text-primary); display: inline-flex; align-items: center; gap: 6px }
.pc-count { font-size: 11px; color: var(--text-muted); background: #f1f5f9; padding: 2px 9px;
  border-radius: 999px; margin-left: auto; white-space: nowrap }
/* 厂区行 */
.pc-zone { margin: 8px 0 8px 6px; padding: 9px 12px; background: #fff; border: 1px solid var(--brd); border-radius: 9px }
.pc-zoneh { display: flex; align-items: center; gap: 8px; margin-bottom: 4px }
.pc-zn { font-weight: 600; font-size: 12.5px; color: var(--text-secondary) }
.pc-plants { display: flex; flex-wrap: wrap; gap: 7px; margin: 7px 0 3px }
.pc-plant { font-size: 12px; background: var(--primary-soft, #eef2ff); border: 1px solid #dbe4ff;
  color: var(--text-secondary); border-radius: 999px; padding: 4px 12px;
  display: inline-flex; align-items: center; gap: 6px; font-family: ui-monospace, monospace }
.pc-plant:hover { border-color: var(--primary) }
.pc-plant.add { background: #fff; border-style: dashed; color: var(--primary); cursor: pointer; font-family: inherit }
.pc-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--primary); flex-shrink: 0 }
.pc-dot.city { width: auto; height: auto; background: none; font-size: 13px }
/* KV 表（别名/映射） */
.pc-kv { display: grid; grid-template-columns: 1fr 26px 1fr 26px; gap: 8px; align-items: center; margin-bottom: 8px }
.pc-in { width: 100%; font-size: 12px; padding: 6px 11px; border: 1px solid var(--brd); border-radius: 7px;
  font-family: ui-monospace, monospace; box-sizing: border-box; outline: none; transition: border-color .13s }
.pc-in:focus { border-color: var(--primary); box-shadow: 0 0 0 2px rgba(99,102,241,.1) }
.pc-in.k { background: #f8fafc }
.pc-in.k:disabled { color: var(--text-muted); cursor: not-allowed }
.pc-arrow { text-align: center; color: var(--text-muted); font-size: 13px }
.pc-x { border: none; background: none; color: #cbd5e1; cursor: pointer; font-size: 15px; padding: 2px 5px;
  border-radius: 5px; transition: all .12s }
.pc-x:hover { color: #dc2626; background: #fef2f2 }
.pc-empty { font-size: 12px; color: var(--text-muted); padding: 4px 0 10px }
/* 按钮 */
.btn { font-size: 12px; padding: 6px 14px; border-radius: 8px; border: 1px solid var(--brd);
  background: #fff; cursor: pointer; color: var(--text-secondary); transition: all .13s }
.btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary) }
.btn.primary { background: var(--primary); color: #fff; border-color: var(--primary);
  box-shadow: 0 2px 5px rgba(79,70,229,.25) }
.btn.xs { font-size: 11px; padding: 3px 10px }
.btn.ghost { background: transparent; border-style: dashed; color: var(--primary) }
.btn.danger { color: #ef4444 }
.btn.danger:hover:not(:disabled) { border-color: #dc2626; background: #fef2f2; color: #dc2626 }
.btn:disabled { opacity: .5; cursor: not-allowed }
/* 单厂参数 */
.pc-pconf { border-bottom: 1px dashed var(--brd); padding: 12px 0 }
.pc-pconf:last-of-type { border-bottom: none }
.pc-pid { font-family: ui-monospace, monospace; font-size: 12px; color: var(--text-secondary);
  margin-bottom: 8px; display: flex; align-items: center; gap: 7px }
.pc-pf { display: flex; gap: 16px; flex-wrap: wrap }
.pc-pf label { font-size: 11.5px; color: var(--text-muted); display: flex; align-items: center; gap: 8px }
.pc-pf label .pc-in { width: 220px }
.pc-pick { display: flex; gap: 8px; margin-top: 12px }
.pc-sel { font-size: 12px; padding: 6px 11px; border: 1px solid var(--brd); border-radius: 7px; min-width: 280px; outline: none }
</style>
