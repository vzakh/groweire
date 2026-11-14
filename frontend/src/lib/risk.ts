import type { Component } from 'vue'
import {
  CircleAlertIcon,
  CircleCheckIcon,
  CloudRainIcon,
  SnowflakeIcon,
  SunIcon,
  ThermometerSunIcon,
  TriangleAlertIcon,
} from '@lucide/vue'
import { copy } from '@/copy/en'

/**
 * One risk ramp for the whole app: map cells, month tiles, legends and charts.
 * Colour never stands alone: every level and weather type also has an icon and a word.
 * The hex values mirror the `--color-risk-*` tokens in style.css (the map needs raw colours).
 */
export type RiskLevel = 'low' | 'medium' | 'high'
export type StressType = 'drought' | 'waterlogging' | 'heat' | 'frost'

interface LevelStyle {
  word: string
  icon: Component
  /** Background colour, for map layers. */
  fill: string
  /** Text colour that reads on `fill`. */
  ink: string
  /** Tailwind classes for the same pair. */
  class: string
}

export const RISK_LEVELS: Record<RiskLevel, LevelStyle> = {
  low: {
    word: copy.risk.levels.low,
    icon: CircleCheckIcon,
    fill: '#f1f5d8',
    ink: '#33401a',
    class: 'bg-risk-low text-risk-low-ink',
  },
  medium: {
    word: copy.risk.levels.medium,
    icon: CircleAlertIcon,
    fill: '#f5c04a',
    ink: '#3d2a00',
    class: 'bg-risk-medium text-risk-medium-ink',
  },
  high: {
    word: copy.risk.levels.high,
    icon: TriangleAlertIcon,
    fill: '#9a3412',
    ink: '#ffffff',
    class: 'bg-risk-high text-risk-high-ink',
  },
}

export const STRESS_TYPES: Record<StressType, { word: string; icon: Component }> = {
  drought: { word: copy.risk.types.drought, icon: SunIcon },
  waterlogging: { word: copy.risk.types.waterlogging, icon: CloudRainIcon },
  heat: { word: copy.risk.types.heat, icon: ThermometerSunIcon },
  frost: { word: copy.risk.types.frost, icon: SnowflakeIcon },
}
