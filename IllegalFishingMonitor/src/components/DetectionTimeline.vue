<script setup lang="ts">
import { useSimulationStore } from '@/stores/simulation'

const store = useSimulationStore()
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm p-5">
    <h2 class="text-sm font-semibold text-gray-800 mb-1 flex items-center gap-2">
      <i class="fas fa-timeline text-blue-600"></i>
      时间线
    </h2>
    <p class="text-xs text-blue-500 mb-4 flex items-center gap-1.5">
      <i class="fas fa-circle-dot text-[10px] animate-pulse"></i>
      持续侦测中...
    </p>

    <!-- 时间线（固定高度，可滚动） -->
    <div class="timeline-scroll relative pl-7 max-h-52 overflow-y-auto pr-1">
      <div
        v-for="(entry, idx) in store.timelineEvents"
        :key="idx"
        class="relative pb-5 last:pb-0"
      >
        <!-- 图标节点 + 连接线 -->
        <div class="absolute -left-7 flex flex-col items-center">
          <div
            class="w-6 h-6 rounded-full flex items-center justify-center shrink-0"
            :class="entry.iconBg"
          >
            <i class="fas text-[10px]" :class="[entry.icon, entry.iconColor]"></i>
          </div>
          <!-- 竖线：最后一个事件不绘制 -->
          <div
            v-if="idx < store.timelineEvents.length - 1"
            class="w-0.5 bg-gray-200 grow mt-0.5"
          ></div>
        </div>

        <!-- 内容 -->
        <div>
          <span class="text-[11px] font-mono text-gray-400">[{{ entry.time }}]</span>
          <p class="text-[13px] text-gray-700 mt-0.5 leading-relaxed">{{ entry.text }}</p>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="store.timelineEvents.length === 0" class="text-xs text-gray-400 py-4">
        暂无事件
      </div>
    </div>
  </div>
</template>

<style scoped>
.timeline-scroll {
  scrollbar-width: thin;
  scrollbar-color: #d1d5db transparent;
}
.timeline-scroll::-webkit-scrollbar {
  width: 4px;
}
.timeline-scroll::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 2px;
}
</style>
