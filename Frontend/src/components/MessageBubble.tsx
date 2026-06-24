import React from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { User, Bot } from 'lucide-react';
import { cn } from '../lib/utils';
import type { Message } from '../types';
import { RagasPanel } from './RagasPanel';
interface MessageBubbleProps {
  message: Message;
}
type Block =
{
  type: 'code';
  lang: string;
  code: string;
} |
{
  type: 'text';
  content: string;
};
// Split content into fenced code blocks and surrounding text.
function parseBlocks(content: string): Block[] {
  const blocks: Block[] = [];
  const fenceRegex = /```(\w*)\n?([\s\S]*?)```/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = fenceRegex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      blocks.push({
        type: 'text',
        content: content.slice(lastIndex, match.index)
      });
    }
    blocks.push({
      type: 'code',
      lang: match[1] || 'text',
      code: match[2].replace(/\n$/, '')
    });
    lastIndex = fenceRegex.lastIndex;
  }
  if (lastIndex < content.length) {
    blocks.push({
      type: 'text',
      content: content.slice(lastIndex)
    });
  }
  return blocks;
}
// Tokenize inline markdown: **bold** and `code`.
function renderInline(
text: string,
keyPrefix: string)
: React.ReactNode[] {
  const tokenRegex = /(\*\*[^*]+\*\*)|(`[^`]+`)/g;
  const nodes: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let i = 0;
  while ((match = tokenRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }
    const token = match[0];
    const key = `${keyPrefix}-${i++}`;
    if (token.startsWith('**')) {
      nodes.push(
        <strong key={key} className="font-semibold text-zinc-100">
          {token.slice(2, -2)}
        </strong>
      );
    } else {
      nodes.push(
        <code
          key={key}
          className="rounded bg-zinc-800 px-1.5 py-0.5 text-indigo-300 text-[0.85em]">
          {token.slice(1, -1)}
        </code>
      );
    }
    lastIndex = tokenRegex.lastIndex;
  }
  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }
  return nodes;
}
function TextBlock({
  content,
  blockKey
}: {content: string; blockKey: string;}) {
  const paragraphs = content.split(/\n{2,}/).filter((p) => p.trim().length > 0);
  return (
    <>
      {paragraphs.map((para, idx) =>
      <p
        key={`${blockKey}-p${idx}`}
        className="leading-relaxed mb-3 last:mb-0">
        
          {renderInline(para.trim(), `${blockKey}-p${idx}`)}
        </p>
      )}
    </>);

}
export function MessageBubble({
  message
}: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const blocks = parseBlocks(message.content);
  return (
    <div
      className={cn(
        'flex w-full gap-4 px-4 py-6 md:px-6',
        isUser ? 'bg-zinc-950/50' : 'bg-zinc-900/20'
      )}>
      
      <div className="mx-auto flex w-full max-w-4xl gap-4">
        <div
          className={cn(
            'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg',
            isUser ?
            'bg-indigo-600 text-white' :
            'bg-zinc-800 text-emerald-400 border border-zinc-700'
          )}>
          
          {isUser ? <User className="h-5 w-5" /> : <Bot className="h-5 w-5" />}
        </div>

        <div className="flex w-full flex-col gap-2 overflow-hidden pt-1">
          <div className="font-medium text-zinc-300 text-sm">
            {isUser ? 'You' : 'KnoFetch AI'}
          </div>

          <div className="max-w-none text-zinc-300 text-sm md:text-base">
            {blocks.map((block, idx) => {
              if (block.type === 'code') {
                return (
                  <div
                    key={`block-${idx}`}
                    className="my-4 overflow-hidden rounded-lg border border-zinc-800 bg-[#1E1E1E]">
                    
                    <div className="flex items-center justify-between bg-zinc-900 px-4 py-2 text-xs text-zinc-400">
                      <span>{block.lang}</span>
                    </div>
                    <SyntaxHighlighter
                      style={vscDarkPlus}
                      language={block.lang}
                      PreTag="div"
                      customStyle={{
                        margin: 0,
                        padding: '1rem',
                        background: 'transparent',
                        fontSize: '0.85em'
                      }}>
                      
                      {block.code}
                    </SyntaxHighlighter>
                  </div>);

              }
              return (
                <TextBlock
                  key={`block-${idx}`}
                  content={block.content}
                  blockKey={`block-${idx}`} />);


            })}
          </div>
          {!isUser && message.ragas && (
            <RagasPanel evalResult={message.ragas} />
          )}
        </div>
      </div>
    </div>);

}