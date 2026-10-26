<script setup lang="ts">
withDefaults(defineProps<{ scroll?: 'auto' | 'contained' }>(), { scroll: 'auto' })
</script>
<template><div class="page-content" :class="`page-content--${scroll}`"><slot /></div></template>
<style scoped>
.page-content{flex:1;min-width:0;min-height:0;background:var(--card-bg,#fff);border:1px solid var(--border-color,#e2e8f0);border-radius:var(--card-radius,12px);padding:20px}.page-content--auto{overflow:auto}.page-content--contained{overflow:hidden;display:flex;flex-direction:column}
</style>
