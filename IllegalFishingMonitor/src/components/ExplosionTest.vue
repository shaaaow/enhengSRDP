<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue'
import { useSimulationStore } from '@/stores/simulation'

const store = useSimulationStore()

const autoPlay = ref(false)
const isPlaying = ref(false)
let autoTimer: ReturnType<typeof setTimeout> | null = null
let currentAudio: HTMLAudioElement | null = null

function playExplosion() {
  if (!store.explosionAudio || isPlaying.value) return

  isPlaying.value = true
  store.triggerExplosion()

  currentAudio = new Audio(`/api/audio/file/${encodeURIComponent(store.explosionAudio)}`)
  currentAudio.play().catch(() => {})
  currentAudio.onended = () => {
    isPlaying.value = false
    currentAudio = null
  }
  currentAudio.onerror = () => {
    isPlaying.value = false
    currentAudio = null
  }

  setTimeout(() => {
    store.resetTrigger()
  }, 3000)
}

function scheduleAutoPlay() {
  if (!autoPlay.value) return
  const delay = (Math.random() * 25 + 5) * 1000
  autoTimer = setTimeout(() => {
    playExplosion()
    scheduleAutoPlay()
  }, delay)
}

watch(autoPlay, (on) => {
  if (on) {
    scheduleAutoPlay()
  } else {
    if (autoTimer) {
      clearTimeout(autoTimer)
      autoTimer = null
    }
  }
})

onUnmounted(() => {
  if (autoTimer) clearTimeout(autoTimer)
  if (currentAudio) {
    currentAudio.pause()
    currentAudio = null
  }
})
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm p-5">
    <h2 class="text-sm font-semibold text-gray-800 mb-2 flex items-center gap-2">
      <i class="fas fa-bomb text-red-500"></i>
      炸鱼声播放测试
    </h2>
    <p class="text-xs text-gray-400 mb-4">
      <i class="fas fa-file-audio mr-1"></i>当前素材:
      {{ store.explosionAudio ?? '未上传' }}
    </p>

    <!-- 控制项 -->
    <div class="space-y-3">
      <!-- 手动播放 -->
      <div class="flex items-center justify-between">
        <span class="text-[13px] text-gray-600">手动播放爆炸音频</span>
        <button
          :class="[
            'px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer',
            autoPlay || !store.explosionAudio || isPlaying
              ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800 shadow-sm',
          ]"
          :disabled="autoPlay || !store.explosionAudio || isPlaying"
          @click="playExplosion"
        >
          <i
            class="mr-1 text-[11px]"
            :class="isPlaying ? 'fas fa-spinner fa-spin' : 'fas fa-play'"
          ></i>
          {{ isPlaying ? '播放中' : '播放' }}
        </button>
      </div>

      <!-- 随机播放开关 -->
      <div class="flex items-center justify-between">
        <span class="text-[13px] text-gray-600">随机时刻播放炸鱼声</span>
        <!-- Switch 开关 -->
        <button
          class="relative w-11 h-6 rounded-full transition-colors cursor-pointer shrink-0"
          :class="autoPlay ? 'bg-blue-600' : 'bg-gray-300'"
          :disabled="!store.explosionAudio"
          @click="store.explosionAudio && (autoPlay = !autoPlay)"
        >
          <span
            class="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow-sm transition-transform"
            :class="autoPlay ? 'translate-x-5' : 'translate-x-0'"
          ></span>
        </button>
      </div>
    </div>

    <!-- 状态文字 -->
    <div class="mt-4 pt-3 border-t border-gray-100">
      <p
        v-if="store.triggerStatus === 'triggered'"
        class="text-xs flex items-center gap-1.5 text-red-600"
      >
        <i class="fas fa-circle-dot text-[10px] animate-pulse"></i>
        触发成功！({{ store.lastTriggerTime }})
      </p>
      <p
        v-else
        class="text-xs flex items-center gap-1.5"
        :class="autoPlay ? 'text-blue-600' : 'text-gray-400'"
      >
        <i
          class="fas text-[10px]"
          :class="autoPlay ? 'fa-circle-dot animate-pulse' : 'fa-circle'"
        ></i>
        {{ autoPlay ? '自动侦测模式已启用，等待随机触发...' : '等待触发...' }}
      </p>
    </div>
  </div>
</template>
