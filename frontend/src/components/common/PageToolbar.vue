<template><div class="page-toolbar"><div class="page-toolbar__filters"><slot /></div><div v-if="$slots.actions" class="page-toolbar__actions"><slot name="actions" /></div></div></template>
<style scoped>
.page-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}.page-toolbar__filters,.page-toolbar__actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap;min-width:0}
</style>
