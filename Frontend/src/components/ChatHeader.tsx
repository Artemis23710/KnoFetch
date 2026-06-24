import React, { useState } from 'react';
import { SlidersHorizontal, Info } from 'lucide-react';
interface ChatHeaderProps {
  title: string;
}
export function ChatHeader({ title }: ChatHeaderProps) {
  const [temperature, setTemperature] = useState(0.7);
  const [topK, setTopK] = useState(50);
  const [showSettings, setShowSettings] = useState(false);
  return (
    <div className="relative z-10 flex h-16 shrink-0 items-center justify-between border-b border-zinc-800 bg-zinc-950/80 px-4 backdrop-blur-md md:px-6">
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-semibold text-zinc-100 truncate max-w-[200px] sm:max-w-md">
          {title}
        </h1>
        <div className="hidden sm:flex items-center gap-1.5 rounded-full border border-emerald-900/30 bg-emerald-900/10 px-2.5 py-1 text-xs font-medium text-emerald-400">
        </div>
      </div>
    </div>);

}