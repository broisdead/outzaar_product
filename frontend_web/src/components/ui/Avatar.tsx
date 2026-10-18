import { cn } from '../../lib/cn'

const gradients = [
  'from-[#4B67E8] to-[#7B5CE6]',
  'from-[#2F8F9D] to-[#4B67E8]',
  'from-[#7B5CE6] to-[#B2569B]',
  'from-[#3B7BD9] to-[#3DB6A0]',
  'from-[#6B6FF5] to-[#3A4A9E]',
]

function hash(text: string): number {
  let h = 0
  for (let i = 0; i < text.length; i++) h = (h * 31 + text.charCodeAt(i)) >>> 0
  return h
}

export function initials(name: string): string {
  return name
    .replace(/^Dr\.?\s+/i, '')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0])
    .join('')
    .toUpperCase()
}

interface AvatarProps {
  name: string
  size?: 'sm' | 'md' | 'lg'
  shape?: 'round' | 'square'
  statusClass?: string
  className?: string
}

const sizes = { sm: 'h-8 w-8 text-[11px]', md: 'h-10 w-10 text-xs', lg: 'h-12 w-12 text-sm' }

export default function Avatar({ name, size = 'md', shape = 'round', statusClass, className }: AvatarProps) {
  return (
    <span className={cn('relative inline-flex shrink-0', className)}>
      <span
        className={cn(
          'inline-flex items-center justify-center bg-gradient-to-br font-medium text-white/95',
          gradients[hash(name) % gradients.length],
          sizes[size],
          shape === 'round' ? 'rounded-full' : 'rounded-xl',
        )}
        aria-hidden
      >
        {initials(name)}
      </span>
      {statusClass && (
        <span
          className={cn(
            'absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-ink-900',
            statusClass,
          )}
        />
      )}
    </span>
  )
}
