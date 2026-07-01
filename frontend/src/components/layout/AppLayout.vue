<template>
  <el-container class="app-layout">
    <el-aside width="200px">
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#1a1a2e"
        text-color="#eaeaea"
        active-text-color="#409eff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Monitor /></el-icon>
          <span>Dashboard</span>
        </el-menu-item>
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>AI Assistant</span>
        </el-menu-item>
        <el-menu-item index="/events">
          <el-icon><Bell /></el-icon>
          <span>Event Center</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Monitor, ChatDotRound, Bell } from '@element-plus/icons-vue'

const route = useRoute()
const activeMenu = computed(() => route.path)
</script>

<style scoped>
.app-layout {
  height: 100vh;
}
.el-aside {
  background-color: #1a1a2e;
}
.el-main {
  padding: 20px;
  overflow: auto;
}
</style>
