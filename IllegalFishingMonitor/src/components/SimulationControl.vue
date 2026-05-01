<script setup lang="ts">
import { ref } from 'vue'
import { useSimulationStore } from '@/stores/simulation'

const store = useSimulationStore()

const engineInputRef = ref<HTMLInputElement | null>(null)
const explosionInputRef = ref<HTMLInputElement | null>(null)
const uploadError = ref<string | null>(null)

async function handleFileSelect(event: Event, type: 'engine' | 'explosion') {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  uploadError.value = null
  try {
    await store.uploadAudio(file, type)
  } catch (e: unknown) {
    uploadError.value = e instanceof Error ? e.message : '上传失败'
  }
  input.value = ''
}

async function handleSimulate() {
  uploadError.value = null
  try {
    await store.runSimulation()
  } catch (e: unknown) {
    uploadError.value = e instanceof Error ? e.message : '计算失败'
  }
}
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm p-5">
    <h2 class="text-sm font-semibold text-gray-800 mb-4 flex items-center gap-2">
      <i class="fas fa-sliders text-blue-600"></i>仿真控制
    </h2>

    <!-- 上传区域 -->
    <div class="space-y-3 mb-5">
      <!-- 引擎噪声上传 -->
      <div>
        <input
          ref="engineInputRef"
          type="file"
          accept=".wav"
          class="hidden"
          @change="handleFileSelect($event, 'engine')"
        />
        <button
          class="w-full border-2 border-dashed border-gray-300 rounded-lg py-2.5 px-4 text-xs text-gray-500 hover:border-blue-400 hover:text-blue-600 hover:bg-blue-50 transition-all cursor-pointer flex items-center justify-center gap-2"
          @click="engineInputRef?.click()"
        >
          <i class="fas fa-upload"></i>
          上传船舶引擎噪声 (.wav)
        </button>
        <p class="text-xs text-gray-400 mt-1.5 ml-1">
          <i class="fas fa-file-audio mr-1"></i>当前素材:
          {{ store.engineAudio ?? '未上传' }}
        </p>
      </div>

      <!-- 爆炸声上传 -->
      <div>
        <input
          ref="explosionInputRef"
          type="file"
          accept=".wav"
          class="hidden"
          @change="handleFileSelect($event, 'explosion')"
        />
        <button
          class="w-full border-2 border-dashed border-gray-300 rounded-lg py-2.5 px-4 text-xs text-gray-500 hover:border-blue-400 hover:text-blue-600 hover:bg-blue-50 transition-all cursor-pointer flex items-center justify-center gap-2"
          @click="explosionInputRef?.click()"
        >
          <i class="fas fa-upload"></i>
          上传爆炸/炸鱼声 (.wav)
        </button>
        <p class="text-xs text-gray-400 mt-1.5 ml-1">
          <i class="fas fa-file-audio mr-1"></i>当前素材:
          {{ store.explosionAudio ?? '未上传' }}
        </p>
      </div>
    </div>

    <!-- 分割线 -->
    <div class="border-t border-gray-100 my-4"></div>

    <!-- 参数设置 -->
    <div class="grid grid-cols-2 gap-3 mb-5">
      <div>
        <label class="text-[11px] text-gray-500 mb-1 block font-medium">FFT 窗口大小</label>
        <input
          type="text"
          value="8192"
          disabled
          class="w-full border border-gray-200 rounded-lg px-3 py-2 text-xs bg-gray-50 text-gray-400 cursor-not-allowed"
        />
      </div>
      <div>
        <label class="text-[11px] text-gray-500 mb-1 block font-medium"
          >模拟水温 (&deg;C)</label
        >
        <input
          type="number"
          value="15"
          disabled
          class="w-full border border-gray-200 rounded-lg px-3 py-2 text-xs bg-gray-50 text-gray-400 cursor-not-allowed"
        />
      </div>
    </div>
    <p class="text-[11px] text-amber-500 mb-4 flex items-center gap-1">
      <i class="fas fa-lock text-[10px]"></i> 以上参数暂未启用，后续开放配置功能
    </p>

    <!-- 错误提示 -->
    <p v-if="uploadError" class="text-xs text-red-500 mb-3 flex items-center gap-1">
      <i class="fas fa-circle-exclamation text-[10px]"></i>
      {{ uploadError }}
    </p>

    <!-- 开始按钮 -->
    <button
      :disabled="!store.explosionAudio || store.isComputing"
      :class="[
        'w-full font-medium py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2 text-sm shadow-sm',
        !store.explosionAudio || store.isComputing
          ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
          : 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white cursor-pointer',
      ]"
      @click="handleSimulate"
    >
      <i v-if="store.isComputing" class="fas fa-spinner fa-spin text-xs"></i>
      <i v-else class="fas fa-play text-xs"></i>
      {{ store.isComputing ? '计算中...' : '开始模拟计算' }}
    </button>
  </div>
</template>
