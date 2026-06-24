import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Info, Gauge } from 'lucide-react';

interface RagasPanelProps {
  evalResult: {
    faithfulness: number;
    answer_relevance: number;
    context_precision: number;
    overall_score: number;
    details?: {
      faithfulness_reason?: string;
      answer_relevance_reason?: string;
      context_precision_reason?: string;
    };
    error?: string;
  };
}

export function RagasPanel({ evalResult }: RagasPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!evalResult) return null;

  if (evalResult.error) {
    return (
      <div className="mt-4 rounded-xl border border-red-900/30 bg-red-950/20 p-4 text-sm text-red-400">
        ⚠️ <strong>RAGAS Evaluation Error:</strong> {evalResult.error}
      </div>
    );
  }

  const getBadgeColor = (score: number) => {
    if (score >= 0.75) return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
    if (score >= 0.5) return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
    return 'text-rose-400 bg-rose-500/10 border-rose-500/20';
  };

  const getBadgeIcon = (score: number) => {
    if (score >= 0.75) return '🟢';
    if (score >= 0.5) return '🟡';
    return '🔴';
  };

  const getLabel = (score: number) => {
    if (score >= 0.75) return 'Good';
    if (score >= 0.5) return 'Moderate';
    return 'Poor';
  };

  const metrics = [
    {
      name: 'Faithfulness',
      score: evalResult.faithfulness,
      help: '1.0 = no hallucination. Measures if claims are supported by context.',
      reason: evalResult.details?.faithfulness_reason
    },
    {
      name: 'Answer Relevance',
      score: evalResult.answer_relevance,
      help: '1.0 = perfectly on-topic. Measures if answer directly addresses query.',
      reason: evalResult.details?.answer_relevance_reason
    },
    {
      name: 'Context Precision',
      score: evalResult.context_precision,
      help: '1.0 = perfect retrieval. Measures if the right context chunks were found.',
      reason: evalResult.details?.context_precision_reason
    },
    {
      name: 'Overall Score',
      score: evalResult.overall_score,
      help: 'Average of the three key RAGAS metrics.',
      reason: null
    }
  ];

  return (
    <div className="mt-4 rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 shadow-sm backdrop-blur-sm">
      <div className="flex items-center justify-between border-b border-zinc-800/60 pb-3">
        <div className="flex items-center gap-2">
          <Gauge className="h-4 w-4 text-indigo-400" />
          <span className="text-sm font-semibold text-zinc-200">📊 RAGAS Evaluation Metrics</span>
        </div>
        <span className="text-xs text-zinc-500">LLM-as-judge (0 = worst, 1 = best)</span>
      </div>

      {/* Grid Metrics */}
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {metrics.map((m) => (
          <div
            key={m.name}
            className={`flex flex-col gap-1 rounded-lg border p-3 transition-colors bg-zinc-900/60 border-zinc-800/80`}
            title={m.help}
          >
            <span className="text-xs text-zinc-400 font-medium">{m.name}</span>
            <div className="flex items-baseline gap-2">
              <span className="text-lg font-bold text-zinc-100">{m.score.toFixed(2)}</span>
              <span className={`inline-flex items-center rounded-full border px-1.5 py-0.2 text-[10px] font-semibold uppercase tracking-wider ${getBadgeColor(m.score)}`}>
                {getBadgeIcon(m.score)} {getLabel(m.score)}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Collapsible reasoning section */}
      {evalResult.details && (
        <div className="mt-3">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex w-full items-center justify-between rounded-lg bg-zinc-900/30 px-3 py-2 text-xs font-medium text-zinc-400 hover:bg-zinc-900/60 hover:text-zinc-300 transition-colors"
          >
            <span className="flex items-center gap-1">
              <Info className="h-3.5 w-3.5" />
              Detailed Judge Reasonings
            </span>
            {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>

          {isExpanded && (
            <div className="mt-2 space-y-2 rounded-lg border border-zinc-800/40 bg-zinc-950/20 p-3 text-xs text-zinc-400 leading-relaxed">
              {metrics.filter(m => m.reason).map(m => (
                <div key={m.name} className="border-b border-zinc-800/40 pb-2 last:border-b-0 last:pb-0">
                  <span className="font-semibold text-zinc-300">{m.name}:</span>{' '}
                  <span>{m.reason}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
