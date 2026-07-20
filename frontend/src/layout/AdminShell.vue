<template>
  <div class="admin">
    <AppSidebar/>
    <div class="main">
      <AppHeader/>
      <main class="content"><router-view/></main>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppHeader from '@/components/layout/AppHeader.vue'
</script>

<style scoped>
.admin{display:flex;height:100vh;overflow:hidden;background:var(--content-bg)}
.main{flex:1;display:flex;flex-direction:column;min-width:0}
.content{flex:1;overflow:auto;padding:20px}
</style>
