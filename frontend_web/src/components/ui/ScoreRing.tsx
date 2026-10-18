import { motion } from 'framer-motion'

export function scoreColor(score: number): string {
  if (score >= 85) return '#3DD6A0'
  if (score >= 70) return '#7C93FF'
  return '#F2B84B'
}

interface ScoreRingProps {
  score: number
  size?: number
  label?: boolean
}

export default function ScoreRing({ score, size = 56, label = false }: ScoreRingProps) {
  const color = scoreColor(score)
  return (
    <div className="flex flex-col items-center gap-1" aria-label={`AI fit score ${score} out of 100`}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg viewBox="0 0 100 100" width={size} height={size} className="-rotate-90">
          <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="7" />
          <motion.circle
            cx="50"
            cy="50"
            r="42"
            fill="none"
            stroke={color}
            strokeWidth="7"
            strokeLinecap="round"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: score / 100 }}
            transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
          />
        </svg>
        <span
          className="absolute inset-0 flex items-center justify-center font-medium tabular-nums text-fg"
          style={{ fontSize: size * 0.32 }}
        >
          {score}
        </span>
      </div>
      {label && <span className="text-xs text-fg-subtle">AI fit score</span>}
    </div>
  )
}
