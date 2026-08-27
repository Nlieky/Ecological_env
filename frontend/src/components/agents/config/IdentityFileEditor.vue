<template>
  <div class="placeholder">身份文件编辑器（Task 7 实现）</div>
</template>

<script setup lang="ts">
// 占位：Task 7 整文件替换。暴露 dirty/openFile 供父组件骨架先行接线。
const props = defineProps<{ entity: any }>()
defineExpose({
  dirty: false,
  openFile: (_f: string) => {},
})
// 避免 unused 警告（占位期）
void props
</script>

<style scoped>
.placeholder { color: var(--text-muted); padding: 40px; text-align: center; font-size: 13px }
</style>
