<script setup lang="ts">
import { useSimulationStore } from '@/stores/simulation'

const store = useSimulationStore()
</script>

<template>
  <div class="grid grid-cols-3 gap-3">
    <!-- 卡片 A：传感器与声源状态（坐标来自 store，随拖拽实时更新）-->
    <div class="bg-white rounded-xl shadow-sm p-4">
      <h3 class="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
        <span class="w-6 h-6 bg-blue-100 rounded flex items-center justify-center">
          <i class="fas fa-location-dot text-blue-600 text-xs"></i>
        </span>
        传感器与声源状态
      </h3>
      <ul class="space-y-2 text-[13px] text-gray-600">
        <li v-for="s in store.sensors" :key="s.id" class="flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-blue-500 shrink-0"></span>
          <span class="font-medium text-gray-700">{{ s.label }}:</span>
          <span class="font-mono">({{ s.x.toFixed(2) }}, {{ s.y.toFixed(2) }}) m</span>
        </li>
        <li class="flex items-center gap-2 pt-1.5 border-t border-gray-100">
          <span class="w-2 h-2 rounded-full bg-red-500 shrink-0"></span>
          <span class="font-medium text-red-600">Boat:</span>
          <span class="font-mono"
            >({{ store.boat.x.toFixed(2) }}, {{ store.boat.y.toFixed(2) }}) m</span
          >
        </li>
      </ul>
    </div>

    <!-- 卡片 B：算法中间结果 -->
    <div class="bg-white rounded-xl shadow-sm p-4">
      <h3 class="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
        <span class="w-6 h-6 bg-amber-100 rounded flex items-center justify-center">
          <i class="fas fa-clock text-amber-600 text-xs"></i>
        </span>
        算法中间结果
      </h3>
      <ul class="space-y-2 text-[13px] text-gray-600">
        <li class="flex justify-between">
          <span class="font-medium text-gray-700">Δt<sub>12</sub>:</span>
          <span class="font-mono">{{
            store.tdoaResult ? store.tdoaResult.dt12.toFixed(6) + ' 秒' : '--'
          }}</span>
        </li>
        <li class="flex justify-between">
          <span class="font-medium text-gray-700">Δt<sub>13</sub>:</span>
          <span class="font-mono">{{
            store.tdoaResult ? store.tdoaResult.dt13.toFixed(6) + ' 秒' : '--'
          }}</span>
        </li>
        <li class="flex justify-between">
          <span class="font-medium text-gray-700">Δt<sub>23</sub>:</span>
          <span class="font-mono">{{
            store.tdoaResult ? store.tdoaResult.dt23.toFixed(6) + ' 秒' : '--'
          }}</span>
        </li>
        <li class="flex justify-between pt-1.5 border-t border-gray-100">
          <span class="font-medium text-gray-500">GCC 峰值:</span>
          <span class="font-mono text-blue-600">{{
            store.tdoaResult ? store.tdoaResult.gcc_peak_12.toFixed(4) : '--'
          }}</span>
        </li>
      </ul>
    </div>

    <!-- 卡片 C：定位解算结果 -->
    <div class="bg-white rounded-xl shadow-sm p-4">
      <h3 class="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
        <span class="w-6 h-6 bg-green-100 rounded flex items-center justify-center">
          <i class="fas fa-star text-green-600 text-xs"></i>
        </span>
        定位解算结果
      </h3>
      <div class="space-y-2 text-[13px] text-gray-600">
        <div>
          <span class="text-gray-500">估计坐标:</span>
          <p class="font-mono text-lg font-semibold text-gray-800 mt-0.5">
            {{
              store.localizationResult
                ? `(${store.localizationResult.x.toFixed(2)}, ${store.localizationResult.y.toFixed(2)}) m`
                : '--'
            }}
          </p>
        </div>
        <div class="flex items-center justify-between pt-1.5 border-t border-gray-100">
          <span class="text-gray-500">GDOP:</span>
          <span v-if="store.localizationResult" class="inline-flex items-center gap-1">
            <span class="font-mono font-semibold text-green-600">{{
              store.localizationResult.gdop.toFixed(2)
            }}</span>
            <span
              class="text-[11px] px-1.5 py-0.5 rounded-full font-medium"
              :class="
                store.localizationResult.gdop < 2
                  ? 'bg-green-100 text-green-700'
                  : store.localizationResult.gdop < 5
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-red-100 text-red-700'
              "
            >
              {{ store.localizationResult.gdop_quality }}
            </span>
          </span>
          <span v-else class="font-mono">--</span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-gray-500">定位误差:</span>
          <span class="font-mono text-amber-600">{{
            store.localizationResult
              ? '~' + store.localizationResult.error_estimate_m.toFixed(4) + ' m'
              : '--'
          }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
