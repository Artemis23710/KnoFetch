import React, { useRef } from 'react';
import { motion } from 'framer-motion';
import { formatDistanceToNow } from 'date-fns';
import {
  MessageSquare,
  Plus,
  Search,
  Settings,
  PanelLeftClose,
  PanelLeftOpen,
  Database,
  UploadCloud,
  Download,
  FileSpreadsheet
} from 'lucide-react';
import { cn } from '../lib/utils';
import type { ChatSession } from '../types';
interface SidebarProps {
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
  sessions: ChatSession[];
  activeSessionId: string;
  documents?: string[];
  onResetDatabase?: () => void;
  isResetting?: boolean;
  runRagas: boolean;
  setRunRagas: (val: boolean) => void;
  onFileUpload: (files: FileList) => void;
  isUploading: boolean;
  onDownloadHistory: () => void;
  onDownloadRagas: () => void;
  hasRagasHistory: boolean;
  onNewChat?: () => void;
}
export function Sidebar({
  isOpen,
  setIsOpen,
  sessions,
  activeSessionId,
  documents = [],
  onResetDatabase,
  isResetting = false,
  runRagas,
  setRunRagas,
  onFileUpload,
  isUploading,
  onDownloadHistory,
  onDownloadRagas,
  hasRagasHistory,
  onNewChat
}: SidebarProps) {
  const sidebarFileInputRef = useRef<HTMLInputElement>(null);
  return (
    <motion.div
      initial={false}
      animate={{
        width: isOpen ? 280 : 72
      }}
      className="relative z-20 flex h-full shrink-0 flex-col border-r border-zinc-800 bg-zinc-950 transition-colors">
      
      {/* Header */}
      <div className="flex h-16 shrink-0 items-center justify-between px-4">
        <div
          className={cn(
            'flex items-center gap-2 overflow-hidden transition-opacity',
            !isOpen && 'opacity-0 w-0'
          )}>
          
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-500/20 text-indigo-400">
            <Database className="h-5 w-5" />
          </div>
          <span className="whitespace-nowrap font-semibold text-zinc-100">
            KnoFetch
          </span>
        </div>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100 transition-colors"
          aria-label={isOpen ? 'Collapse Sidebar' : 'Expand Sidebar'}>
          
          {isOpen ?
          <PanelLeftClose className="h-5 w-5" /> :

          <PanelLeftOpen className="h-5 w-5" />
          }
        </button>
      </div>

      {/* New Chat Button */}
      <div className="px-3 py-2">
        <button
          onClick={onNewChat}
          className={cn(
            'flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-3 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-500',
            !isOpen && 'px-0'
          )}>
          
          <Plus className="h-5 w-5 shrink-0" />
          {isOpen && <span className="whitespace-nowrap">New Chat</span>}
        </button>
      </div>

      {/* Search (Only when open) */}
      {isOpen &&
      <div className="px-3 py-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
            <input
            type="text"
            placeholder="Search history..."
            className="w-full rounded-md border border-zinc-800 bg-zinc-900 py-1.5 pl-9 pr-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all" />
          
          </div>
        </div>
      }

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto px-3 py-2 scrollbar-thin scrollbar-track-transparent scrollbar-thumb-zinc-800">
        {/* Configuration panel */}
        {isOpen && (
          <div className="mb-5 rounded-xl border border-zinc-800 bg-zinc-900/30 p-3 flex flex-col gap-3.5">
            <div>
              <span className="text-[10px] font-semibold text-indigo-400 uppercase tracking-wider block mb-2">
                ⚙️ RAG Settings
              </span>

              {/* RAGAS Switch */}
              <div className="flex items-center justify-between">
                <label className="text-xs text-zinc-400 font-medium select-none cursor-pointer" htmlFor="ragas-switch">
                  Enable RAGAS evaluation
                </label>
                <input
                  type="checkbox"
                  id="ragas-switch"
                  checked={runRagas}
                  onChange={(e) => setRunRagas(e.target.checked)}
                  className="h-3.5 w-3.5 rounded border-zinc-800 bg-zinc-900 text-indigo-600 focus:ring-indigo-500 accent-indigo-600 cursor-pointer"
                />
              </div>
            </div>

            {/* Drag/Click Uploader */}
            <div className="border-t border-zinc-800/60 pt-3">
              <label className="text-[10px] font-medium text-zinc-500 uppercase tracking-wider block mb-1.5">
                Submit & Process PDF
              </label>
              <div
                onClick={() => sidebarFileInputRef.current?.click()}
                className={cn(
                  "border border-dashed border-zinc-800 hover:border-zinc-700/60 hover:bg-zinc-900/40 rounded-lg p-3 text-center cursor-pointer transition-all",
                  isUploading && "pointer-events-none opacity-50 border-indigo-500/20"
                )}
              >
                <UploadCloud className="h-4 w-4 mx-auto text-zinc-500 mb-1" />
                <span className="text-[11px] text-zinc-300 font-medium block">
                  {isUploading ? "Uploading..." : "Submit PDF Files"}
                </span>
              </div>
              <input
                type="file"
                ref={sidebarFileInputRef}
                onChange={(e) => {
                  if (e.target.files && e.target.files.length > 0) {
                    onFileUpload(e.target.files);
                  }
                  e.target.value = '';
                }}
                multiple
                accept=".pdf"
                className="hidden"
              />
            </div>
          </div>
        )}

        {/* Documents Section */}
        {isOpen && (
          <div className="mt-6 border-t border-zinc-800/60 pt-4">
            <div className="mb-2 px-2 flex items-center justify-between">
              <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
                Documents
              </span>
              {onResetDatabase && documents.length > 0 && (
                <button
                  onClick={onResetDatabase}
                  disabled={isResetting}
                  className="text-xs text-red-400 hover:text-red-300 transition-colors disabled:opacity-50 font-medium"
                  title="Clear database"
                >
                  {isResetting ? 'Clearing...' : 'Clear DB'}
                </button>
              )}
            </div>
            <div className="space-y-1">
              {documents.length > 0 ? (
                documents.map((doc) => (
                  <div
                    key={doc}
                    className="flex items-center gap-2 rounded-md px-3 py-2 text-xs text-zinc-400 bg-zinc-900/40 border border-zinc-800/50"
                  >
                    <Database className="h-3.5 w-3.5 shrink-0 text-indigo-400" />
                    <span className="truncate flex-1" title={doc}>
                      {doc}
                    </span>
                  </div>
                ))
              ) : (
                <div className="px-2 py-2 text-xs text-zinc-500 italic">
                  No documents indexed yet.
                </div>
              )}
            </div>
          </div>
        )}

        {/* Export Data Section */}
        {isOpen && (
          <div className="mt-6 border-t border-zinc-800/60 pt-4">
            <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider block mb-2 px-2">
              Export History
            </span>
            <div className="space-y-1.5 px-1">
              <button
                onClick={onDownloadHistory}
                className="flex w-full items-center gap-2 rounded-md bg-zinc-900/40 hover:bg-zinc-800/60 border border-zinc-850 px-2.5 py-1.5 text-xs text-zinc-300 transition-colors"
              >
                <Download className="h-3.5 w-3.5 text-indigo-400" />
                Download Chat History
              </button>
              {hasRagasHistory && (
                <button
                  onClick={onDownloadRagas}
                  className="flex w-full items-center gap-2 rounded-md bg-zinc-900/40 hover:bg-zinc-800/60 border border-zinc-850 px-2.5 py-1.5 text-xs text-zinc-300 transition-colors"
                >
                  <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-400" />
                  Download RAGAS Scores
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* User Profile */}
      <div className="mt-auto border-t border-zinc-800 p-3">
        <div
          className={cn(
            'flex items-center gap-3 rounded-md p-2 transition-colors hover:bg-zinc-800/50 cursor-pointer',
            !isOpen && 'justify-center'
          )}>
          
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-sm font-bold text-white">
            JD
          </div>
          {isOpen &&
          <>
              <div className="flex flex-1 flex-col overflow-hidden">
                <span className="truncate text-sm font-medium text-zinc-100">
                  Jane Doe
                </span>
                <span className="truncate text-xs text-zinc-500">Pro Plan</span>
              </div>
              <Settings className="h-4 w-4 shrink-0 text-zinc-400" />
            </>
          }
        </div>
      </div>
    </motion.div>);

}