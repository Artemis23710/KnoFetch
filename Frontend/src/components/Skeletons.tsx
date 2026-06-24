import React from 'react';
export function MessageSkeleton() {
  return (
    <div className="flex w-full gap-4 p-4 md:p-6">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-zinc-800">
        <div className="h-4 w-4 animate-pulse rounded-full bg-zinc-700" />
      </div>
      <div className="flex w-full flex-col gap-2 pt-1">
        <div className="h-4 w-24 animate-pulse rounded bg-zinc-800" />
        <div className="space-y-2">
          <div className="h-4 w-[85%] animate-pulse rounded bg-zinc-800/80" />
          <div className="h-4 w-[95%] animate-pulse rounded bg-zinc-800/60" />
          <div className="h-4 w-[60%] animate-pulse rounded bg-zinc-800/40" />
        </div>
      </div>
    </div>);

}