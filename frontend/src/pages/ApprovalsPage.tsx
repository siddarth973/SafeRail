import React, { useEffect, useState } from 'react';
import { Clock, Hash, CheckCircle, RefreshCw } from 'lucide-react';
import { fetchPendingApprovals, submitApprovalDecision } from '../../src/api/client';
import { PendingApprovalItem, PendingAction } from '../types';
import { ApprovalReviewModal } from '../components/dashboard/ApprovalReviewModal';

export const ApprovalsPage: React.FC = () => {
  const [approvals, setApprovals] = useState<PendingApprovalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAction, setSelectedAction] = useState<PendingAction | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [bannerNotice, setBannerNotice] = useState<string | null>(null);

  const loadApprovals = async () => {
    setLoading(true);
    try {
      const items = await fetchPendingApprovals();
      setApprovals(items);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApprovals();
    const timer = setInterval(loadApprovals, 8000);
    return () => clearInterval(timer);
  }, []);

  const handleInspect = (item: PendingApprovalItem) => {
    setSelectedAction({
      id: item.action_id,
      action_type: item.action_type,
      description: item.reason,
      agent_name: item.agent_name,
      target: item.target,
      risk_level: item.risk_level,
      status: 'PENDING',
      timestamp: item.created_at,
      risk_tier: item.risk_tier,
      required_confirmation_phrase: item.required_confirmation_phrase
    });
    setIsModalOpen(true);
  };

  const handleDirectReject = async (actionId: number) => {
    try {
      await submitApprovalDecision({
        action_id: actionId,
        decision: 'REJECTED',
        reviewer_id: 'reviewer-kavya',
        reason: 'Direct block from Approvals Queue'
      });
      setBannerNotice(`Action #${actionId} rejected and prevented from execution.`);
      loadApprovals();
      setTimeout(() => setBannerNotice(null), 4000);
    } catch (err: any) {
      alert(`Reject failed: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Review Modal */}
      <ApprovalReviewModal
        action={selectedAction}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onDecisionSubmitted={loadApprovals}
      />

      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-[#141f33]">
        <div>
          <h2 className="text-xl font-bold text-white">Action Approvals Queue</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Exact-action human authorization with SHA-256 fingerprint verification (Feature A4)
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-semibold">
            {approvals.length} Actions Pending
          </span>
          <button
            onClick={loadApprovals}
            disabled={loading}
            className="p-1.5 rounded-lg border border-[#19253d] bg-[#0d1527] text-slate-400 hover:text-cyan-400 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Banner Notice */}
      {bannerNotice && (
        <div className="p-3 rounded-lg bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle className="w-4 h-4 shrink-0" />
          <span>{bannerNotice}</span>
        </div>
      )}

      {/* Security Info Card */}
      <div className="p-4 rounded-xl bg-blue-950/20 border border-blue-500/30 text-xs text-blue-200 flex items-start gap-3">
        <Clock className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <div className="font-semibold text-white">Single-Use, Time-Bounded Exact Action Approvals</div>
          <p className="text-slate-300">
            Each action is cryptographically bound to its exact parameters, requesting agent, and session via SHA-256 canonical hashing. Approvals automatically expire after 10 minutes and can never be reused.
          </p>
        </div>
      </div>

      {/* Approvals Table */}
      <div className="bg-[#0d1527] border border-[#19253d] rounded-xl overflow-hidden shadow-card">
        <div className="p-4 border-b border-[#19253d] font-semibold text-white text-sm flex items-center justify-between">
          <span>Active Pending Approvals</span>
          <span className="text-xs text-slate-400">Total: {approvals.length}</span>
        </div>

        {approvals.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">
            No actions currently awaiting review. All agent requests are cleared!
          </div>
        ) : (
          <div className="divide-y divide-[#19253d]">
            {approvals.map((item) => (
              <div
                key={item.action_id}
                className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-[#121c32]/50 transition-colors"
              >
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-white">
                      #{item.action_id} • {item.action_type}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                        item.risk_level === 'HIGH'
                          ? 'bg-rose-950/60 text-rose-400 border-rose-800/40'
                          : 'bg-amber-950/60 text-amber-400 border-amber-800/40'
                      }`}
                    >
                      {item.risk_tier} ({item.risk_level})
                    </span>
                    <span className="text-xs text-slate-400 font-mono">
                      (Created: {item.created_at})
                    </span>
                  </div>

                  <div className="text-xs text-slate-300">
                    <strong>Reason:</strong> {item.reason}
                  </div>

                  <div className="text-xs text-slate-400 flex flex-wrap items-center gap-3">
                    <span>
                      Agent: <strong className="text-cyan-400">{item.agent_name}</strong>
                    </span>
                    <span>
                      Target: <code className="bg-[#090e1a] px-1.5 py-0.5 rounded text-slate-300 border border-[#19253d]">{item.target}</code>
                    </span>
                    <span className="text-amber-400 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      <span>Expires: {item.expires_at}</span>
                    </span>
                  </div>

                  <div className="text-[10px] text-slate-500 font-mono flex items-center gap-1 truncate max-w-lg">
                    <Hash className="w-3 h-3 text-cyan-500 shrink-0" />
                    <span className="text-slate-400 shrink-0">SHA-256:</span>
                    <span className="truncate">{item.fingerprint}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => handleInspect(item)}
                    className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-semibold shadow-sm transition-colors"
                  >
                    Inspect & Approve
                  </button>
                  <button
                    onClick={() => handleDirectReject(item.action_id)}
                    className="px-3.5 py-1.5 bg-[#141e34] hover:bg-rose-950/40 border border-[#233354] hover:border-rose-500/40 text-rose-300 rounded text-xs font-semibold transition-colors"
                  >
                    Block Action
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
