<script setup lang="ts">
withDefaults(defineProps<{ title: string; subtitle?: string; scroll?: 'auto' | 'contained' }>(), { scroll: 'auto' })
</script>
<template>
  <section class="page-shell" :class="`page-shell--${scroll}`">
    <header class="page-shell__header"><div><h1>{{ title }}</h1><p v-if="subtitle">{{ subtitle }}</p></div><div v-if="$slots.actions" class="page-shell__actions"><slot name="actions" /></div></header>
    <div v-if="$slots.context" class="page-shell__context"><slot name="context" /></div>
    <div v-if="$slots.toolbar"><slot name="toolbar" /></div>
    <main class="page-shell__body"><slot /></main>
    <footer v-if="$slots.footer"><slot name="footer" /></footer>
  </section>
</template>
<style scoped>
.page-shell{height:100%;min-height:0;min-width:0;display:flex;flex-direction:column;gap:16px;color:var(--text-primary,#1e293b)}
.page-shell__header{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap;flex-shrink:0}.page-shell h1{margin:0;font-size:24px;line-height:1.4}.page-shell p{margin:6px 0 0;color:var(--text-secondary,#64748b);font-size:14px}.page-shell__actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.page-shell__context{color:var(--text-secondary,#64748b);font-size:13px}.page-shell__body{flex:1;min-height:0;min-width:0}.page-shell--auto .page-shell__body{overflow:auto}.page-shell--contained .page-shell__body{overflow:hidden;display:flex;flex-direction:column}footer{flex-shrink:0}
</style>
