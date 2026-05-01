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

    <!-- 噪声控制 -->
    <div class="mb-5">
      <div class="flex items-center justify-between mb-2">
        <label class="text-[11px] text-gray-500 font-medium flex items-center gap-1.5">
          <i class="fas fa-wave-square text-blue-500 text-[10px]"></i>
          环境噪声 (AWGN)
        </label>
        <label class="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            v-model="store.snrEnabled"
            class="sr-only peer"
          />
          <div class="w-8 h-4 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:border-gray-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-blue-600"></div>
        </label>
      </div>
      <div v-if="store.snrEnabled" class="space-y-2">
        <div class="flex items-center gap-3">
          <input
            type="range"
            v-model.number="store.snrDb"
            min="-10"
            max="40"
            step="1"
            class="flex-1 h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
          />
          <span class="text-xs font-mono text-blue-600 font-semibold w-14 text-right">{{ store.snrDb }} dB</span>
        </div>
        <div class="flex justify-between text-[10px] text-gray-400 px-0.5">
          <span>-10 dB</span>
          <span>强噪声 ← → 弱噪声</span>
          <span>40 dB</span>
        </div>
      </div>
      <p v-else class="text-[10px] text-gray-400 mt-1">
        开启后可通过滑块控制信噪比
      </p>
    </div>

    <!-- 其他参数（预留） -->
    <div class="grid grid-cols-1 gap-3 mb-5">
      <div>
        <label class="text-[11px] text-gray-500 mb-1 block font-medium">模拟水温 (&deg;C)</label>
        <input
          type="number"
          value="15"
          disabled
          class="w-full border border-gray-200 rounded-lg px-3 py-2 text-xs bg-gray-50 text-gray-400 cursor-not-allowed"
        />
      </div>
    </div>
    <p class="text-[11px] text-amber-500 mb-4 flex items-center gap-1">
      <i class="fas fa-lock text-[10px]"></i> 水温参数暂未启用，后续开放配置功能
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
