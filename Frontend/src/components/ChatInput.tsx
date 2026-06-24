import React, { useEffect, useRef } from 'react';
import { Paperclip, Send, RefreshCw } from 'lucide-react';
import { cn } from '../lib/utils';
interface ChatInputProps {
  input: string;
  setInput: (value: string) => void;
  onSubmit: () => void;
  isLoading: boolean;
  onFileUpload?: (files: FileList) => void;
  isUploading?: boolean;
}
export function ChatInput({
  input,
  setInput,
  onSubmit,
  isLoading,
  onFileUpload,
  isUploading
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [input]);
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !isLoading) {
        onSubmit();
      }
    }
  };
  return (
    <div className="relative mx-auto w-full max-w-4xl px-4 pb-6 pt-2 md:px-6 md:pb-8">
      <div className="relative flex w-full flex-col rounded-2xl border border-zinc-800 bg-zinc-900/80 p-2 shadow-sm backdrop-blur-sm transition-all focus-within:border-indigo-500/50 focus-within:ring-1 focus-within:ring-indigo-500/50">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything about your knowledge base..."
          className="max-h-[120px] min-h-[44px] w-full resize-none bg-transparent px-3 py-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none scrollbar-thin scrollbar-track-transparent scrollbar-thumb-zinc-700"
          rows={1}
          disabled={isLoading || isUploading} />
        

        <div className="flex items-center justify-between px-2 pb-1 pt-2">
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoading || isUploading}
              className="flex h-8 w-8 items-center justify-center rounded-md text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-100 disabled:opacity-50"
              aria-label="Attach file">
              
              <Paperclip className="h-4 w-4" />
            </button>
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => {
                if (e.target.files && e.target.files.length > 0 && onFileUpload) {
                  onFileUpload(e.target.files);
                }
                // Clear input value to allow uploading same file again
                e.target.value = '';
              }}
              multiple
              accept=".pdf"
              style={{ display: 'none' }}
            />
            <button
              type="button"
              className="flex h-8 w-8 items-center justify-center rounded-md text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-100"
              aria-label="Regenerate response">
              
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>

          <button
            onClick={onSubmit}
            disabled={!input.trim() || isLoading || isUploading}
            className={cn(
              'flex h-8 w-8 items-center justify-center rounded-md transition-all',
              input.trim() && !isLoading && !isUploading ?
              'bg-indigo-600 text-white hover:bg-indigo-500 shadow-sm' :
              'bg-zinc-800 text-zinc-500 cursor-not-allowed'
            )}
            aria-label="Send message">
            
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
      <div className="mt-2 text-center text-xs text-zinc-500">
        AI can make mistakes. Verify important information with cited sources.
      </div>
    </div>);

}