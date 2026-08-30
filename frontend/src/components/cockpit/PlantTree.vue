<template>
  <div class="ptree">
    <div v-if="store.treeLoading" class="hint">加载厂目录…</div>
    <div v-else-if="store.treeError" class="hint err">⚠ {{ store.treeError }}</div>
    <template v-else>
      <div v-for="city in store.tree?.cities" :key="city.name" class="city">
        <button class="lvl1" @click="toggleCity(city.name)">
          <span class="tri" :class="{ open: store.openCity === city.name }">▶</span>{{ city.name }}
        </button>
        <div v-show="store.openCity === city.name">
          <div v-for="dist in city.districts" :key="dist.name" class="dist">
            <button class="lvl2" @click="toggleDist(dist.name)">
              <span class="tri" :class="{ open: store.openDist === dist.name }">▶</span>{{ dist.name }}
            </button>
            <div v-show="store.openDist === dist.name">
              <button v-for="p in dist.plants" :key="p.plant_id" class="plant"
                :class="{ active: store.activePlant === p.plant_id }"
                @click="pick(p.plant_id, city.name, dist.name)">
                <span class="dot" :class="p.status" />{{ shortName(p.plant_id) }}
                <span class="time">{{ p.latest_time.slice(5, 16) }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
      <div v-if="store.tree?.ungrouped?.length" class="city">
        <button class="lvl1" @click="toggleCity('__ungrouped__')">
          <span class="tri" :class="{ open: store.openCity === '__ungrouped__' }">▶</span>未分组
        </button>
        <div v-show="store.openCity === '__ungrouped__'">
          <button v-for="p in store.tree.ungrouped" :key="p.plant_id" class="plant"
            :class="{ active: store.activePlant === p.plant_id }"
            @click="pick(p.plant_id, '__ungrouped__')">
            <span class="dot" :class="p.status" />{{ p.plant_id }}
          </button>
        </div>
      </div>
      <div v-if="!store.tree?.cities?.length && !store.tree?.ungrouped?.length" class="hint">
        暂无厂数据（导入报表后自动出现）
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { usePlantsStore } from '@/stores/plants'

const props = defineProps<{ activeId?: string }>()
const emit = defineEmits<{ (e: 'select', plantId: string): void }>()

const store = usePlantsStore()

function toggleCity(name: string) {
  store.openCity = store.openCity === name ? '' : name
}
function toggleDist(name: string) {
  store.openDist = store.openDist === name ? '' : name
}
function pick(pid: string, city: string, dist?: string) {
  store.selectPlant(pid, city, dist)
  emit('select', pid)
}

function shortName(id: string) {
  return id.replace(/^当阳市/, '').replace(/污水处理厂/, '')
}

onMounted(() => store.fetchTree())
// activeId（URL 传入）变化时同步选中+展开父级链
watch(() => store.tree, (t) => {
  const pid = props.activeId
  if (t && pid && store.activePlant !== pid) {
    store.selectPlant(pid)
    store.expandTo(pid)
  }
}, { immediate: true })
watch(() => props.activeId, (pid) => {
  if (pid && store.tree && store.activePlant !== pid) {
    store.selectPlant(pid)
    store.expandTo(pid)
  }
})
</script>

<style scoped>
.ptree { font-size: 13px }
.lvl1 { all: unset; cursor: pointer; display: flex; align-items: center; gap: 6px;
  font-weight: 600; font-size: 13.5px; padding: 6px 4px; color: var(--text-primary, #1e293b) }
.lvl2 { all: unset; cursor: pointer; display: flex; align-items: center; gap: 6px;
  padding: 4px 4px 4px 18px; color: var(--text-secondary, #475569) }
.plant { all: unset; cursor: pointer; display: flex; align-items: center; gap: 7px; width: 100%;
  box-sizing: border-box; padding: 5px 8px 5px 32px; color: var(--text-secondary, #475569);
  border-radius: 7px }
.plant:hover { background: rgba(99, 102, 241, .07) }
.plant.active { background: rgba(99, 102, 241, .13); color: var(--primary, #4f46e5); font-weight: 600 }
.tri { font-size: 9px; color: #94a3b8; transition: transform .15s }
.tri.open { transform: rotate(90deg) }
.dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0 }
.dot.online { background: #10b981 }
.dot.offline { background: #cbd5e1 }
.time { margin-left: auto; font-size: 10.5px; color: #94a3b8 }
.hint { padding: 10px; color: var(--text-muted, #94a3b8); font-size: 12.5px }
.hint.err { color: #ef4444 }
</style>
