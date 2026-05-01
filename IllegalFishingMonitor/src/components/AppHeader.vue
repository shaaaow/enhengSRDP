<script setup lang="ts"></script>

<template>
  <header class="bg-white shadow-sm px-6 py-3 flex items-center justify-between shrink-0">
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
        <i class="fas fa-wave-square text-white text-lg"></i>
      </div>
      <div>
        <h1 class="text-lg font-bold text-gray-800 leading-tight">
          水声定位与语音识别仿真系统 <span class="text-blue-600 font-semibold">v0.1</span>
        </h1>
        <p class="text-xs text-gray-400">基于 GCC-PHAT 的声源定位，可自定义传感器布局</p>
      </div>
    </div>

    <div class="flex items-center gap-2">
      <button
        class="w-9 h-9 rounded-full bg-gray-100 hover:bg-gray-200 flex items-center justify-center transition-colors cursor-pointer"
        title="设置"
      >
        <i class="fas fa-gear text-gray-500 text-sm"></i>
      </button>
      <button
        class="w-9 h-9 rounded-full bg-gray-100 hover:bg-gray-200 flex items-center justify-center transition-colors cursor-pointer"
        title="帮助"
      >
        <i class="fas fa-circle-question text-gray-500 text-sm"></i>
      </button>
    </div>
  </header>
</template>
