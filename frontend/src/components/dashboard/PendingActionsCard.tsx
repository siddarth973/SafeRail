import React, { useState } from 'react';
import { ClipboardList, ArrowRight, ChevronLeft, ChevronRight, CheckCircle } from 'lucide-react';
import { PendingAction, RiskLevel } from '../../types';
import { ApprovalReviewModal } from './ApprovalReviewModal';
import { submitApprovalDecision } from '../../api/client';

interface PendingActionsCardProps {
  actions: PendingAction[];
  onViewAll?: () => void;
  onRefresh?: () => void;
}

export const PendingActionsCard: React.FC<PendingActionsCardProps> = ({
  actions,
  onViewAll,
  onRefresh
}) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [activeNotice, setActiveNotice] = useState<string | null>(null);
  const [selectedAction, setSelectedAction] = useState<PendingAction | null>(null);
  const [isReviewOpen, setIsReviewOpen] = useState(false);

  const getRiskBadge = (risk: RiskLevel) => {
    switch (risk) {
      case 'HIGH':
      case 'CRITICAL':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider bg-rose-950/60 text-rose-400 border border-rose-800/40">
            HIGH
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider bg-amber-950/60 text-amber-400 border border-amber-800/40">
            MEDIUM
          </span>
        );
      case 'LOW':
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
            LOW
          </span>
        );
    }
  };

  const handleReviewClick = (action: PendingAction) => {
    setSelectedAction(action);
    setIsReviewOpen(true);
  };

  const handleQuickBlock = async (action: PendingAction) => {
    try {
      await submitApprovalDecision({
        action_id: action.id,
        decision: 'REJECTED',
        reviewer_id: "reviewer-kavya",
        reason: "Quick block from dashboard table"
      });
      setActiveNotice(`Action #${action.id} (${action.action_type}) blocked by security reviewer.`);
      if (onRefresh) onRefresh();
      setTimeout(() => setActiveNotice(null), 4000);
    } catch (err: any) {
      setActiveNotice(`Block failed: ${err.message}`);
      setTimeout(() => setActiveNotice(null), 4000);
    }
  };

  return (
    <div className="bg-[#0d1527] border border-[#19253d] rounded-xl p-5 flex flex-col justify-between shadow-card h-full min-h-[380px]">
      {/* Review Modal */}
      <ApprovalReviewModal
        action={selectedAction}
        isOpen={isReviewOpen}
        onClose={() => setIsReviewOpen(false)}
        onDecisionSubmitted={() => {
          if (onRefresh) onRefresh();
        }}
      />

      {/* Notice Banner */}
      {activeNotice && (
        <div className="mb-3 px-3 py-2 rounded-lg bg-blue-950/70 border border-blue-500/40 text-blue-200 text-xs flex items-center gap-2 animate-fadeIn">
          <CheckCircle className="w-4 h-4 text-cyan-400 shrink-0" />
          <span>{activeNotice}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <ClipboardList className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-white tracking-wide">Pending Actions</h2>
            <p className="text-xs text-slate-400">Requires human review and approval</p>
          </div>
        </div>

        <button
          onClick={onViewAll}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#141e34] border border-[#233354] text-xs text-slate-300 hover:text-white hover:bg-[#1b2844] transition-colors"
        >
          <span>View All</span>
          <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto flex-1">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#19253d] text-[11px] text-slate-400 font-medium">
              <th className="pb-2.5 font-normal">#</th>
              <th className="pb-2.5 font-normal">Action</th>
              <th className="pb-2.5 font-normal">Agent</th>
              <th className="pb-2.5 font-normal">Target</th>
              <th className="pb-2.5 font-normal">Risk</th>
              <th className="pb-2.5 font-normal">Time</th>
              <th className="pb-2.5 font-normal text-right">Decision</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#162238] text-xs">
            {actions.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-400">
                  No pending actions awaiting approval. Queue is clear!
                </td>
              </tr>
            ) : (
              actions.slice((currentPage - 1) * 5, currentPage * 5).map((item) => (
                <tr key={item.id} className="hover:bg-[#121c32]/60 transition-colors">
                  <td className="py-2.5 text-slate-400 font-mono text-[11px]">{item.id}</td>
                  <td className="py-2.5 pr-2">
                    <div className="font-medium text-white">{item.action_type}</div>
                    <div className="text-[10px] text-slate-400 line-clamp-1">{item.description}</div>
                  </td>
                  <td className="py-2.5 text-slate-300 font-normal pr-2 whitespace-nowrap">
                    {item.agent_name}
                  </td>
                  <td className="py-2.5 pr-2">
                    <span className="font-mono text-[11px] text-slate-300 bg-[#090e1a] px-1.5 py-0.5 rounded border border-[#19253d]">
                      {item.target}
                    </span>
                  </td>
                  <td className="py-2.5 pr-2">{getRiskBadge(item.risk_level)}</td>
                  <td className="py-2.5 text-slate-400 text-[11px] whitespace-nowrap pr-2">
                    {item.timestamp}
                  </td>
                  <td className="py-2.5 text-right whitespace-nowrap">
                    <div className="inline-flex items-center gap-1.5 justify-end">
                      <button
                        onClick={() => handleReviewClick(item)}
                        className="px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-[11px] font-medium transition-colors shadow-sm"
                      >
                        Review
                      </button>
                      <button
                        onClick={() => handleQuickBlock(item)}
                        className="px-2.5 py-1 bg-[#141e34] hover:bg-rose-950/40 hover:border-rose-500/40 hover:text-rose-300 border border-[#233354] text-slate-300 rounded text-[11px] font-medium transition-colors"
                      >
                        Block
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Footer / Pagination */}
      <div className="pt-3 border-t border-[#19253d]/80 flex items-center justify-between text-xs text-slate-400">
        <span>Showing {actions.length === 0 ? 0 : 1}-{Math.min(5, actions.length)} of {actions.length} pending actions</span>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setCurrentPage(1)}
            disabled={currentPage === 1}
            className="p-1 rounded hover:bg-[#141e34] disabled:opacity-30 disabled:hover:bg-transparent text-slate-400"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={() => setCurrentPage(1)}
            className={`w-6 h-6 rounded flex items-center justify-center text-xs font-semibold ${
              currentPage === 1 ? 'bg-blue-600 text-white' : 'text-slate-400 hover:bg-[#141e34]'
            }`}
          >
            1
          </button>
          <button
            onClick={() => setCurrentPage(2)}
            disabled={actions.length <= 5}
            className={`w-6 h-6 rounded flex items-center justify-center text-xs font-semibold ${
              currentPage === 2 ? 'bg-blue-600 text-white' : 'text-slate-400 hover:bg-[#141e34]'
            }`}
          >
            2
          </button>
          <button
            onClick={() => setCurrentPage(2)}
            disabled={currentPage === 2 || actions.length <= 5}
            className="p-1 rounded hover:bg-[#141e34] disabled:opacity-30 disabled:hover:bg-transparent text-slate-400"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
