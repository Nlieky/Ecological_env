<template>
  <div class="ds">
    <div class="head">
      <div>
        <div class="ttl">链路追踪数据源</div>
        <div class="sub">管理可观测性数据源（Jaeger / Zipkin / Tempo 等）</div>
      </div>
      <el-button type="primary" @click="openCreate"><el-icon><Plus/></el-icon>&nbsp;新增数据源</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe style="width: 100%">
      <el-table-column label="名称" min-width="160">
        <template #default="{ row }">
          <span class="nm">{{ row.name }}</span>
          <span class="id">{{ row.id }}</span>
        </template>
      </el-table-column>
      <el-table-column label="类型" width="120">
        <template #default="{ row }"><el-tag size="small" effect="plain">{{ row.provider }}</el-tag></template>
      </el-table-column>
      <el-table-column label="地址" min-width="240">
        <template #default="{ row }"><span class="url">{{ row.config?.url || '—' }}</span></template>
      </el-table-column>
      <el-table-column label="启用" width="90">
        <template #default="{ row }">
          <el-switch :model-value="row.enabled" @change="(v: boolean) => toggleEnabled(row, v)" />
        </template>
      </el-table-column>
      <el-table-column label="更新时间" width="170">
        <template #default="{ row }"><span class="ts">{{ fmt(row.updated_at) }}</span></template>
      </el-table-column>
      <el-table-column label="操作" width="210" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" :loading="testingId === row.id" @click="testConn(row)">测试连接</el-button>
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑数据源' : '新增数据源'" width="480px">
      <el-form :model="form" label-width="72px" label-position="right">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="如：Jaeger 本地" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.provider" style="width: 100%">
            <el-option v-for="p in PROVIDERS" :key="p" :label="p" :value="p" />
          </el-select>
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="form.url" placeholder="http://localhost:16686" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { observabilityService } from '@/api/modules/observability'
import type { TracingDataSource, DataSourceInput } from '@/api/types/api.types'

const PROVIDERS = ['jaeger', 'zipkin', 'tempo', 'otlp', 'skywalking']

const list = ref<TracingDataSource[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingId = ref('')
const saving = ref(false)
const testingId = ref('')
const form = ref({ name: '', provider: 'jaeger', url: '', enabled: true })

function fmt(t: string) { return t ? t.replace('T', ' ').slice(0, 19) : '—' }

async function load() {
  loading.value = true
  try { list.value = await observabilityService.listDatasources() }
  catch { list.value = [] }
  finally { loading.value = false }
}

function openCreate() {
  editingId.value = ''
  form.value = { name: '', provider: 'jaeger', url: '', enabled: true }
  dialogVisible.value = true
}
function openEdit(row: TracingDataSource) {
  editingId.value = row.id
  form.value = { name: row.name, provider: row.provider, url: row.config?.url || '', enabled: row.enabled }
  dialogVisible.value = true
}

async function save() {
  if (!form.value.name.trim()) { ElMessage.warning('请填写名称'); return }
  saving.value = true
  const payload: DataSourceInput = {
    name: form.value.name.trim(),
    provider: form.value.provider,
    config: form.value.url ? { url: form.value.url.trim() } : {},
    enabled: form.value.enabled,
  }
  try {
    if (editingId.value) {
      await observabilityService.updateDatasource(editingId.value, payload)
      ElMessage.success('已更新')
    } else {
      await observabilityService.createDatasource(payload)
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    await load()
  } catch { /* 拦截器已弹错 */ } finally { saving.value = false }
}

async function toggleEnabled(row: TracingDataSource, enabled: boolean) {
  try {
    await observabilityService.updateDatasource(row.id, { enabled })
    row.enabled = enabled
    ElMessage.success(enabled ? '已启用' : '已停用')
  } catch { /* 拦截器已弹错 */ }
}

async function testConn(row: TracingDataSource) {
  testingId.value = row.id
  try {
    const r = await observabilityService.testConnection(row.id)
    ElMessage.success(`${r.message}（延迟 ${r.latency_ms}ms）`)
  } catch { /* 拦截器已弹错（如未启用） */ } finally { testingId.value = '' }
}

async function remove(row: TracingDataSource) {
  try {
    await ElMessageBox.confirm(`确定删除数据源「${row.name}」？`, '删除确认', { type: 'warning' })
  } catch { return }
  try {
    await observabilityService.deleteDatasource(row.id)
    ElMessage.success('已删除')
    await load()
  } catch { /* 拦截器已弹错 */ }
}

onMounted(load)
</script>

<style scoped>
.ds { display: flex; flex-direction: column; gap: 14px }
.head { display: flex; justify-content: space-between; align-items: flex-start }
.ttl { font-size: 16px; font-weight: 700; color: var(--text-primary) }
.sub { font-size: 12px; color: var(--text-muted); margin-top: 3px }
.nm { font-weight: 600; color: var(--text-primary) }
.id { display: block; font-size: 10.5px; color: var(--text-muted); font-family: ui-monospace, monospace; margin-top: 1px }
.url { font-size: 12.5px; color: var(--text-secondary); font-family: ui-monospace, monospace }
.ts { font-size: 12px; color: var(--text-muted) }
</style>
