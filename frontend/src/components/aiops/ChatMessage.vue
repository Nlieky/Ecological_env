<template>
  <div class="msg" :class="msg.role">
    <div class="role">{{ msg.role === 'user' ? '👤 运维员' : '🤖 主智能体' }}</div>
    <div v-if="msg.role === 'user'" class="bubble user">{{ msg.content }}</div>
    <div v-else class="bubble assistant">
      <MarkdownRenderer :content="msg.content" />
      <div v-if="msg.trace" class="cards">
        <DecisionFlow :trace="msg.trace" />
        <SubAgentChips :trace="msg.trace" />
        <EvidenceChain :trace="msg.trace" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import MarkdownRenderer from '@/components/markdown/MarkdownRenderer.vue'
import DecisionFlow from './DecisionFlow.vue'
import SubAgentChips from './SubAgentChips.vue'
import EvidenceChain from './EvidenceChain.vue'
import type { ChatMessage } from '@/stores/chat'
defineProps<{ msg: ChatMessage }>()
</script>

<style scoped>
.msg { margin-bottom: 18px; max-width: 820px }
.role { font-size: 11px; color: var(--text-muted); margin-bottom: 5px }
.bubble { padding: 13px 16px; border-radius: 12px; font-size: 13.5px; line-height: 1.7 }
.user { background: var(--primary); color: #fff; border-radius: 12px 12px 4px 12px }
.assistant { background: #fff; border: 1px solid var(--brd); border-radius: 12px 12px 12px 4px; box-shadow: 0 1px 3px rgba(0,0,0,.04) }
.cards { margin-top: 12px; border-left: 3px solid var(--primary); padding-left: 12px; display: flex; flex-direction: column; gap: 8px }
</style>
