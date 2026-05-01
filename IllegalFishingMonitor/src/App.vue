<script setup lang="ts">
import AppHeader from './components/AppHeader.vue'
import SimulationControl from './components/SimulationControl.vue'
import SimulationCanvas from './components/SimulationCanvas.vue'
import DataStatusCards from './components/DataStatusCards.vue'
import DetectionTimeline from './components/DetectionTimeline.vue'
import ExplosionTest from './components/ExplosionTest.vue'
</script>

<template>
  <div class="min-h-screen bg-slate-50 flex flex-col">
    <!-- 顶部导航栏 -->
    <AppHeader />

    <!-- 主体三栏布局：左 1 : 中 2.5 : 右 1 -->
    <main class="flex-1 p-4 grid grid-cols-[1fr_2.5fr_1fr] gap-4 items-start">
      <!-- 左侧列：仿真控制 -->
      <aside>
        <SimulationControl />
      </aside>

      <!-- 中间列：画布 + 数据卡片 -->
      <section class="flex flex-col gap-4">
        <SimulationCanvas />
        <DataStatusCards />
      </section>

      <!-- 右侧列：时间线 + 播放测试 -->
      <aside class="flex flex-col gap-4">
        <DetectionTimeline />
        <ExplosionTest />
      </aside>
    </main>
  </div>
</template>

<style>
html {
  overflow: -moz-scrollbars-none; /* Firefox旧版本 */
  scrollbar-width: none; /* Firefox新版本 */
  -ms-overflow-style: none; /* IE和Edge */
}

html::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera和Edge(基于Chromium) */
}
body {
  margin: 0;
  font-family:
    -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', 'PingFang SC',
    'Noto Sans SC', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  scrollbar-width: none;
  overflow: -moz-scrollbars-none;
  -ms-overflow-style: none;
}
body::-webkit-scrollbar {
  display: none;
}
</style>
