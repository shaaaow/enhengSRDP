import { defineStore } from 'pinia'
import { reactive, ref } from 'vue'

export interface Position {
  id: string
  label: string
  x: number
  y: number
}

export interface TDOAResult {
  dt12: number
  dt13: number
  dt23: number
  gcc_peak_12: number
  gcc_peak_13: number
  gcc_peak_23: number
}

export interface LocalizationResult {
  x: number
  y: number
  gdop: number
  gdop_quality: string
  error_estimate_m: number
}

export interface TimelineEvent {
  time: string
  text: string
  icon: string
  iconBg: string
  iconColor: string
}

function nowTimeStr(): string {
  return new Date().toLocaleTimeString('zh-CN', { hour12: false })
}

export const useSimulationStore = defineStore('simulation', () => {
  // ===== 传感器与船只坐标 =====
  const sensors = reactive<Position[]>([
    { id: 'M1', label: 'M1', x: 2, y: 2 },
    { id: 'M2', label: 'M2', x: 28, y: 2 },
    { id: 'M3', label: 'M3', x: 15, y: 18 },
  ])

  const boat = reactive<Position>({
    id: 'Boat',
    label: 'Boat',
    x: 12.34,
    y: 8.56,
  })

  function updatePosition(id: string, x: number, y: number) {
    const rounded_x = Math.round(x * 100) / 100
    const rounded_y = Math.round(y * 100) / 100
    if (id === 'Boat') {
      boat.x = rounded_x
      boat.y = rounded_y
    } else {
      const sensor = sensors.find((s) => s.id === id)
      if (sensor) {
        sensor.x = rounded_x
        sensor.y = rounded_y
      }
    }
  }

  // ===== 音频文件 =====
  const engineAudio = ref<string | null>(null)
  const explosionAudio = ref<string | null>(null)

  // ===== 算法结果 =====
  const tdoaResult = ref<TDOAResult | null>(null)
  const localizationResult = ref<LocalizationResult | null>(null)

  // ===== 噪声控制 =====
  const snrEnabled = ref(false)
  const snrDb = ref(20)

  // ===== 计算状态 =====
  const isComputing = ref(false)
  const computeError = ref<string | null>(null)

  // ===== 时间线 =====
  const timelineEvents = reactive<TimelineEvent[]>([
    {
      time: nowTimeStr(),
      text: '系统启动',
      icon: 'fa-play',
      iconBg: 'bg-green-100',
      iconColor: 'text-green-600',
    },
  ])

  function addTimelineEvent(text: string, type: 'info' | 'warning' | 'success' = 'info') {
    const configs = {
      info: { icon: 'fa-tower-broadcast', iconBg: 'bg-blue-100', iconColor: 'text-blue-600' },
      warning: {
        icon: 'fa-triangle-exclamation',
        iconBg: 'bg-red-100',
        iconColor: 'text-red-600',
      },
      success: { icon: 'fa-check', iconBg: 'bg-green-100', iconColor: 'text-green-600' },
    }
    const cfg = configs[type]
    timelineEvents.push({
      time: nowTimeStr(),
      text,
      ...cfg,
    })
  }

  // ===== 炸鱼声触发状态 =====
  const triggerStatus = ref<'idle' | 'triggered'>('idle')
  const lastTriggerTime = ref<string | null>(null)

  // ===== API 调用 =====
  async function uploadAudio(file: File, type: 'engine' | 'explosion') {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('type', type)

    const resp = await fetch('/api/audio/upload', { method: 'POST', body: formData })
    if (!resp.ok) {
      const err = await resp.json()
      throw new Error(err.detail || '上传失败')
    }

    const data = await resp.json()
    if (type === 'engine') {
      engineAudio.value = data.filename
    } else {
      explosionAudio.value = data.filename
    }

    addTimelineEvent(`上传音频: ${data.filename}`, 'info')
    return data
  }

  async function runSimulation() {
    if (!explosionAudio.value) {
      throw new Error('请先上传爆炸声音频')
    }

    isComputing.value = true
    computeError.value = null

    try {
      const body = {
        sensors: sensors.map((s) => ({ id: s.id, x: s.x, y: s.y })),
        source: { x: boat.x, y: boat.y },
        audio_file: explosionAudio.value,
        sound_speed: 1500.0,
        snr_db: snrEnabled.value ? snrDb.value : null,
      }

      const resp = await fetch('/api/simulation/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!resp.ok) {
        const err = await resp.json()
        throw new Error(err.detail || '仿真失败')
      }

      const data = await resp.json()
      tdoaResult.value = data.tdoa
      localizationResult.value = data.localization

      addTimelineEvent(
        `仿真完成，估计坐标 (${data.localization.x.toFixed(2)}, ${data.localization.y.toFixed(2)})`,
        'success',
      )
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '未知错误'
      computeError.value = msg
      addTimelineEvent(`仿真失败: ${msg}`, 'warning')
      throw e
    } finally {
      isComputing.value = false
    }
  }

  function triggerExplosion() {
    triggerStatus.value = 'triggered'
    lastTriggerTime.value = nowTimeStr()
    addTimelineEvent('监测到疑似炸鱼活动（爆炸声，置信度98%）', 'warning')
  }

  function resetTrigger() {
    triggerStatus.value = 'idle'
  }

  return {
    sensors,
    boat,
    updatePosition,
    engineAudio,
    explosionAudio,
    snrEnabled,
    snrDb,
    tdoaResult,
    localizationResult,
    isComputing,
    computeError,
    timelineEvents,
    addTimelineEvent,
    triggerStatus,
    lastTriggerTime,
    uploadAudio,
    runSimulation,
    triggerExplosion,
    resetTrigger,
  }
})
