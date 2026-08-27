<template>
  <div class="pc">
    <div class="pc-h">
      <div class="pc-t">厂区配置</div>
      <div class="pc-a">
        <button class="btn" @click="validate" :disabled="saving">校验</button>
        <button class="btn primary" @click="save" :disabled="saving || !loaded">{{ saving ? '保存中…' : '保存' }}</button>
      </div>
    </div>
    <div v-if="errors.length" class="pc-errs">
      <div v-for="(e, i) in errors" :key="i" class="pc-err">⚠ {{ e }}</div>
    </div>

    <!-- 层级：市→厂区→厂 -->
    <div class="pc-sec">
      <div class="pc-st">层级（市 → 厂区 → 厂）</div>
      <div v-for="(zones, city) in cfg.hierarchy" :key="city" class="pc-city">
        <div class="pc-cityh">
          <span class="pc-cn">{{ city }}</span>
          <button class="btn xs danger" @click="delCity(city)">删市</button>
        </div>
        <div v-for="(plants, zone) in zones" :key="zone" class="pc-zone">
          <div class="pc-zoneh">
            <span class="pc-zn">{{ zone }}</span>
            <button class="btn xs" @click="addPlant(city, zone)">+ 厂</button>
            <button class="btn xs danger" @click="delZone(city, zone)">删区</button>
          </div>
          <div class="pc-plants">
            <span v-for="(p, i) in plants" :key="p + i" class="pc-plant">
              {{ p }}
              <button class="pc-x" @click="delPlant(city, zone, i)">×</button>
            </span>
          </div>
        </div>
        <button class="btn xs" @click="addZone(city)">+ 厂区</button>
      </div>
      <button class="btn" @click="addCity">+ 市</button>
    </div>

    <!-- 别名表 -->
    <div class="pc-sec">
      <div class="pc-st">厂名别名（用户口语 → plant_id）</div>
      <div class="pc-kv">
        <template v-for="k in Object.keys(cfg.plant_aliases)" :key="k">
          <input class="pc-in k" :value="k"
                 @change="renameAlias(k, ($event.target as HTMLInputElement).value)" />
          <span class="pc-arrow">→</span>
          <input class="pc-in v" :value="cfg.plant_aliases[k]"
                 @input="cfg.plant_aliases[k] = ($event.target as HTMLInputElement).value" />
          <button class="pc-x" @click="delAlias(k)">×</button>
        </template>
      </div>
      <button class="btn xs" @click="addAlias">+ 别名</button>
    </div>

    <!-- 报表映射 -->
    <div class="pc-sec">
      <div class="pc-st">报表文件名映射（report_name_map）</div>
      <div class="pc-kv">
        <template v-for="k in Object.keys(cfg.report_name_map)" :key="k">
          <input class="pc-in k" :value="k" disabled title="改名请删除重加" />
          <span class="pc-arrow">→</span>
          <input class="pc-in v" :value="cfg.report_name_map[k]"
                 @input="cfg.report_name_map[k] = ($event.target as HTMLInputElement).value" />
          <button class="pc-x" @click="delReport(k)">×</button>
        </template>
      </div>
      <button class="btn xs" @click="addReport">+ 映射</button>
    </div>

    <!-- per-plant 配置 -->
    <div class="pc-sec">
      <div class="pc-st">单厂配置（display_name / type）</div>
      <div v-for="pid in Object.keys(cfg.plant_configs)" :key="pid" class="pc-pconf">
        <div class="pc-pid">{{ pid }}</div>
        <div class="pc-pf">
          <label>显示名
            <input class="pc-in" :value="pcGet(pid, 'display_name')"
                   @input="pcSet(pid, 'display_name', ($event.target as HTMLInputElement).value)" /></label>
          <label>类型
            <input class="pc-in" :value="pcGet(pid, 'type')"
                   @input="pcSet(pid, 'type', ($event.target as HTMLInputElement).value)" /></label>
        </div>
      </div>
      <div class="pc-pick">
        <select v-model="addPid" class="pc-sel"><option value="">选择厂添加配置…</option>
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
.pc { max-width: 860px }
.pc-h { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px }
.pc-t { font-size: 15px; font-weight: 700 }
.pc-a { display: flex; gap: 8px }
.pc-errs { background: #fef2f2; border: 1px solid #fecaca; border-radius: 10px; padding: 10px 14px; margin-bottom: 14px }
.pc-err { font-size: 12px; color: #dc2626 }
.pc-sec { border: 1px solid var(--brd); border-radius: 12px; padding: 14px 16px; margin-bottom: 14px }
.pc-st { font-size: 12.5px; font-weight: 700; color: var(--text-secondary); margin-bottom: 12px }
.pc-city { margin-bottom: 12px; padding: 10px; border: 1px dashed var(--brd); border-radius: 10px }
.pc-cityh { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px }
.pc-cn { font-weight: 700; font-size: 13.5px }
.pc-zone { margin: 8px 0 8px 10px; padding: 8px 10px; background: #f8fafc; border-radius: 8px }
.pc-zoneh { display: flex; align-items: center; gap: 8px; margin-bottom: 6px }
.pc-zn { font-weight: 600; font-size: 12.5px }
.pc-plants { display: flex; flex-wrap: wrap; gap: 6px; margin: 6px 0 }
.pc-plant { font-size: 12px; background: #fff; border: 1px solid var(--brd); border-radius: 7px;
  padding: 3px 9px; display: inline-flex; align-items: center; gap: 5px; font-family: ui-monospace, monospace }
.pc-kv { display: grid; grid-template-columns: 1fr 20px 1fr 24px; gap: 7px; align-items: center; margin-bottom: 8px }
.pc-in { width: 100%; font-size: 12px; padding: 5px 9px; border: 1px solid var(--brd); border-radius: 6px;
  font-family: ui-monospace, monospace; box-sizing: border-box; outline: none }
.pc-in:focus { border-color: var(--primary) }
.pc-in.k { background: #f8fafc }
.pc-in.k:disabled { color: var(--text-muted); cursor: not-allowed }
.pc-arrow { text-align: center; color: var(--text-muted); font-size: 12px }
.pc-x { border: none; background: none; color: #dc2626; cursor: pointer; font-size: 14px; padding: 0 4px }
.btn { font-size: 12px; padding: 5px 13px; border-radius: 7px; border: 1px solid var(--brd);
  background: #fff; cursor: pointer; color: var(--text-secondary) }
.btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary) }
.btn.primary { background: var(--primary); color: #fff; border-color: var(--primary) }
.btn.xs { font-size: 11px; padding: 3px 9px }
.btn.danger:hover { border-color: #dc2626; color: #dc2626 }
.btn:disabled { opacity: .5; cursor: not-allowed }
.pc-pconf { border-bottom: 1px dashed var(--brd); padding: 10px 0 }
.pc-pid { font-family: ui-monospace, monospace; font-size: 12px; color: var(--text-secondary); margin-bottom: 6px }
.pc-pf { display: flex; gap: 14px; flex-wrap: wrap }
.pc-pf label { font-size: 11.5px; color: var(--text-muted); display: flex; align-items: center; gap: 7px }
.pc-pick { display: flex; gap: 8px; margin-top: 10px }
.pc-sel { font-size: 12px; padding: 5px 9px; border: 1px solid var(--brd); border-radius: 6px; min-width: 260px }
</style>
