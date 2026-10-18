interface Props {
  series: number[]
  color: string
  width?: number
  height?: number
}

export default function Sparkline({ series, color, width = 88, height = 30 }: Props) {
  const min = Math.min(...series)
  const max = Math.max(...series)
  const span = max - min || 1
  const step = width / (series.length - 1)
  const pts = series.map((v, i) => [i * step, height - 3 - ((v - min) / span) * (height - 8)] as const)
  const d = pts.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  const [lx, ly] = pts[pts.length - 1]

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden className="overflow-visible">
      <path d={d} fill="none" stroke={color} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" opacity="0.85" />
      <circle cx={lx} cy={ly} r="2.4" fill={color} />
    </svg>
  )
}
