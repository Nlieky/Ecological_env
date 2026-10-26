<script setup lang="ts">
withDefaults(defineProps<{ label: string; tone?: 'neutral' | 'info' | 'success' | 'warning' | 'danger' }>(), { tone: 'neutral' })
</script>
<template><span class="status-badge" :class="`status-badge--${tone}`">{{ label }}</span></template>
<style scoped>
.status-badge{display:inline-flex;align-items:center;padding:3px 9px;border-radius:6px;font-size:12px;line-height:1.5;background:#f1f5f9;color:var(--text-secondary,#64748b);white-space:nowrap}.status-badge--info{background:#eff6ff;color:#1d4ed8}.status-badge--success{background:#ecfdf5;color:#047857}.status-badge--warning{background:#fffbeb;color:#92400e}.status-badge--danger{background:#fef2f2;color:#b91c1c}
</style>
