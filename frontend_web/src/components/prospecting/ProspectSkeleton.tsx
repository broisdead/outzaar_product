import Skeleton from '../ui/Skeleton'

export default function ProspectSkeleton() {
  return (
    <div className="glass rounded-[20px] p-5" aria-hidden>
      <div className="flex items-start gap-3.5">
        <Skeleton className="h-12 w-12 rounded-xl" />
        <div className="flex-1 space-y-2.5 pt-1">
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-3 w-36" />
        </div>
        <Skeleton className="h-[52px] w-[52px] rounded-full" />
      </div>
      <Skeleton className="mt-5 h-3 w-3/4" />
      <Skeleton className="mt-3.5 h-3 w-full" />
      <Skeleton className="mt-2 h-3 w-5/6" />
      <div className="mt-4 flex gap-2">
        <Skeleton className="h-6 w-28" />
        <Skeleton className="h-6 w-24" />
      </div>
      <Skeleton className="mt-6 h-8 w-44" />
    </div>
  )
}
