<script setup lang="ts">
import { ref, computed } from 'vue'
import { useSimulationStore } from '@/stores/simulation'

const store = useSimulationStore()

const canvasWidth = 30
const canvasHeight = 20

const canvasRef = ref<HTMLElement | null>(null)
const dragTarget = ref<string | null>(null)
const dragOffset = ref({ x: 0, y: 0 })

function toStyle(x: number, y: number) {
  return {
    left: `${(x / canvasWidth) * 100}%`,
    bottom: `${(y / canvasHeight) * 100}%`,
  }
}

function getPosition(id: string) {
  if (id === 'Boat') return { x: store.boat.x, y: store.boat.y }
  const s = store.sensors.find((s) => s.id === id)
  return s ? { x: s.x, y: s.y } : { x: 0, y: 0 }
}

function toCanvasCoords(event: PointerEvent) {
  const rect = canvasRef.value!.getBoundingClientRect()
  return {
    x: ((event.clientX - rect.left) / rect.width) * canvasWidth,
    y: ((rect.bottom - event.clientY) / rect.height) * canvasHeight,
  }
}

function onPointerDown(id: string, event: PointerEvent) {
  event.preventDefault()
  dragTarget.value = id

  if (canvasRef.value) {
    const mouse = toCanvasCoords(event)
    const pos = getPosition(id)
    dragOffset.value = { x: mouse.x - pos.x, y: mouse.y - pos.y }
  }

  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
}

function onPointerMove(event: PointerEvent) {
  if (!dragTarget.value || !canvasRef.value) return

  const mouse = toCanvasCoords(event)
  const x = mouse.x - dragOffset.value.x
  const y = mouse.y - dragOffset.value.y

  const clampedX = Math.max(0, Math.min(canvasWidth, x))
  const clampedY = Math.max(0, Math.min(canvasHeight, y))

  store.updatePosition(dragTarget.value, clampedX, clampedY)
}

function onPointerUp() {
  dragTarget.value = null
}

// ===== 定位结果可视化计算 =====
const locResult = computed(() => store.localizationResult)

const estimatedStyle = computed(() => {
  if (!locResult.value) return null
  return toStyle(locResult.value.x, locResult.value.y)
})

// 误差圆半径：将米转换为画布百分比
const errorCircleStyle = computed(() => {
  if (!locResult.value || !canvasRef.value) return null
  const r = locResult.value.error_estimate_m
  const widthPct = (r / canvasWidth) * 100
  const heightPct = (r / canvasHeight) * 100
  return {
    width: `${widthPct * 2}%`,
    height: `${heightPct * 2}%`,
    left: `${(locResult.value.x / canvasWidth) * 100}%`,
    bottom: `${(locResult.value.y / canvasHeight) * 100}%`,
  }
})

// GDOP 圈颜色
const gdopColor = computed(() => {
  if (!locResult.value) return ''
  const g = locResult.value.gdop
  if (g < 2) return 'border-green-400 bg-green-400/10'
  if (g < 5) return 'border-amber-400 bg-amber-400/10'
  return 'border-red-400 bg-red-400/10'
})

const gdopTextColor = computed(() => {
  if (!locResult.value) return ''
  const g = locResult.value.gdop
  if (g < 2) return 'text-green-600'
  if (g < 5) return 'text-amber-600'
  return 'text-red-600'
})

// GDOP 可视化圆：半径 = GDOP 值本身（米为单位，放大一些以便可见）
const gdopCircleStyle = computed(() => {
  if (!locResult.value) return null
  const r = locResult.value.gdop * 1.5
  const widthPct = (r / canvasWidth) * 100
  const heightPct = (r / canvasHeight) * 100
  return {
    width: `${widthPct * 2}%`,
    height: `${heightPct * 2}%`,
    left: `${(locResult.value.x / canvasWidth) * 100}%`,
    bottom: `${(locResult.value.y / canvasHeight) * 100}%`,
  }
})

// 误差连线：从估计位置到真实位置（船只）
const errorLinePoints = computed(() => {
  if (!locResult.value) return null
  return {
    x1: `${(locResult.value.x / canvasWidth) * 100}%`,
    y1: `${100 - (locResult.value.y / canvasHeight) * 100}%`,
    x2: `${(store.boat.x / canvasWidth) * 100}%`,
    y2: `${100 - (store.boat.y / canvasHeight) * 100}%`,
  }
})
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm p-5">
    <h2 class="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
      <i class="fas fa-map text-blue-600"></i>2D 水域可视化画布
    </h2>

    <div
      ref="canvasRef"
      class="relative rounded-lg border border-sky-200 overflow-hidden canvas-area select-none"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointerleave="onPointerUp"
    >
      <!-- 坐标轴标签 -->
      <div class="absolute bottom-1.5 right-3 text-xs text-sky-400 font-mono z-10">X (m) →</div>
      <div
        class="absolute top-3 left-1 text-xs text-sky-400 font-mono z-10"
        style="writing-mode: vertical-lr; transform: rotate(180deg)"
      >
        Y (m) →
      </div>

      <!-- X 轴刻度 -->
      <div
        v-for="tick in [0, 5, 10, 15, 20, 25, 30]"
        :key="'xt' + tick"
        class="absolute bottom-0 text-[10px] text-sky-300 font-mono -translate-x-1/2"
        :style="{ left: `${(tick / canvasWidth) * 100}%` }"
      >
        {{ tick }}
      </div>
      <!-- Y 轴刻度 -->
      <div
        v-for="tick in [0, 5, 10, 15, 20]"
        :key="'yt' + tick"
        class="absolute left-0.5 text-[10px] text-sky-300 font-mono translate-y-1/2"
        :style="{ bottom: `${(tick / canvasHeight) * 100}%` }"
      >
        {{ tick }}
      </div>

      <!-- ===== GDOP 可视化圆圈 ===== -->
      <div
        v-if="gdopCircleStyle"
        class="absolute rounded-full border-2 border-dashed -translate-x-1/2 translate-y-1/2 z-5 pointer-events-none"
        :class="gdopColor"
        :style="gdopCircleStyle"
      >
        <!-- GDOP 标签 -->
        <div
          class="absolute -top-5 left-1/2 -translate-x-1/2 whitespace-nowrap text-[10px] font-mono font-bold"
          :class="gdopTextColor"
        >
          GDOP {{ locResult?.gdop.toFixed(2) }}
        </div>
      </div>

      <!-- ===== 误差连线 (SVG) ===== -->
      <svg
        v-if="errorLinePoints"
        class="absolute inset-0 w-full h-full z-8 pointer-events-none"
      >
        <line
          :x1="errorLinePoints.x1"
          :y1="errorLinePoints.y1"
          :x2="errorLinePoints.x2"
          :y2="errorLinePoints.y2"
          stroke="#f59e0b"
          stroke-width="1.5"
          stroke-dasharray="4 3"
          opacity="0.7"
        />
      </svg>

      <!-- ===== 误差圆圈 ===== -->
      <div
        v-if="errorCircleStyle"
        class="absolute rounded-full border-2 border-dashed border-amber-400 -translate-x-1/2 translate-y-1/2 z-9 pointer-events-none"
        :style="errorCircleStyle"
      ></div>

      <!-- ===== 定位估计结果标记 — 外层尺寸锁定为准星大小 ===== -->
      <div
        v-if="estimatedStyle"
        class="absolute -translate-x-1/2 translate-y-1/2 w-7 h-7 z-15 pointer-events-none"
        :style="estimatedStyle"
      >
        <!-- 十字准星标记 -->
        <div class="relative w-full h-full flex items-center justify-center">
          <div class="absolute w-7 h-0.5 bg-emerald-500 rounded-full"></div>
          <div class="absolute h-7 w-0.5 bg-emerald-500 rounded-full"></div>
          <div
            class="w-3 h-3 rounded-full bg-emerald-500 border-2 border-white shadow-sm"
          ></div>
        </div>
        <div class="absolute top-full left-1/2 -translate-x-1/2 mt-0.5 text-center whitespace-nowrap">
          <span class="text-[10px] font-bold text-emerald-600 bg-white/80 px-1 rounded"
            >估计 ({{ locResult?.x.toFixed(2) }}, {{ locResult?.y.toFixed(2) }})</span
          >
        </div>
      </div>

      <!-- 麦克风节点（可拖拽）— 外层尺寸锁定为图标大小，标签绝对定位 -->
      <div
        v-for="s in store.sensors"
        :key="s.id"
        class="absolute -translate-x-1/2 translate-y-1/2 w-9 h-9 group"
        :class="[dragTarget === s.id ? 'z-30 cursor-grabbing' : 'z-20 cursor-grab']"
        :style="toStyle(s.x, s.y)"
        @pointerdown="onPointerDown(s.id, $event)"
      >
        <div
          class="w-full h-full bg-blue-600 rounded-full flex items-center justify-center shadow-md ring-2 ring-blue-200 group-hover:ring-blue-400 transition-all"
          :class="dragTarget === s.id ? 'scale-115 shadow-lg ring-blue-400' : 'group-hover:scale-110'"
        >
          <i class="fas fa-microphone text-white text-sm"></i>
        </div>
        <div class="absolute top-full left-1/2 -translate-x-1/2 mt-1 text-center whitespace-nowrap">
          <span class="text-xs font-bold text-blue-700">{{ s.label }}</span>
          <span class="text-[11px] text-gray-500 ml-0.5"
            >({{ s.x.toFixed(2) }}, {{ s.y.toFixed(2) }})m</span
          >
        </div>
      </div>

      <!-- 船只节点（可拖拽）— 外层尺寸锁定为图标大小 -->
      <div
        class="absolute -translate-x-1/2 translate-y-1/2 w-9 h-9 group"
        :class="[dragTarget === 'Boat' ? 'z-30 cursor-grabbing' : 'z-20 cursor-grab']"
        :style="toStyle(store.boat.x, store.boat.y)"
        @pointerdown="onPointerDown('Boat', $event)"
      >
        <!-- 脉冲动画环 -->
        <div class="absolute inset-0">
          <div class="absolute inset-0 rounded-full bg-red-400 opacity-30 animate-ping"></div>
        </div>
        <div
          class="relative w-full h-full bg-red-500 rounded-full flex items-center justify-center shadow-md ring-2 ring-red-200 group-hover:ring-red-400 transition-all"
          :class="dragTarget === 'Boat' ? 'scale-115 shadow-lg ring-red-400' : 'group-hover:scale-110'"
        >
          <i class="fas fa-ship text-white text-sm"></i>
        </div>
        <div class="absolute top-full left-1/2 -translate-x-1/2 mt-1 text-center whitespace-nowrap">
          <span class="text-xs font-bold text-red-600">Boat</span>
          <span class="text-[11px] text-gray-500 ml-0.5"
            >({{ store.boat.x.toFixed(2) }}, {{ store.boat.y.toFixed(2) }})m</span
          >
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.canvas-area {
  height: 400px;
  background-color: #f0f9ff;
  background-image:
    linear-gradient(rgba(56, 189, 248, 0.1) 1px, transparent 1px),
    linear-gradient(90deg, rgba(56, 189, 248, 0.1) 1px, transparent 1px);
  background-size: 40px 40px;
  touch-action: none;
}
</style>
