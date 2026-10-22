import React, { useState } from 'react';
import {
  ShieldAlert,
  CheckCircle,
  XCircle,
  Hash,
  X
} from 'lucide-react';
import { submitApprovalDecision } from '../../api/client';
import { PendingAction } from '../../types';

interface ApprovalReviewModalProps {
  action: PendingAction | null;
  isOpen: boolean;
  onClose: () => void;
  onDecisionSubmitted: () => void;
}

export const ApprovalReviewModal: React.FC<ApprovalReviewModalProps> = ({
  action,
  isOpen,
  onClose,
  onDecisionSubmitted
}) => {
  const [reviewerReason, setReviewerReason] = useState('');
  const [confirmationPhrase, setConfirmationPhrase] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  if (!isOpen || !action) return null;

  const handleDecision = async (decision: 'APPROVED' | 'REJECTED') => {
    setIsSubmitting(true);
    setFeedback(null);
    try {
      const res = await submitApprovalDecision({
        action_id: action.id,
        decision,
        reviewer_id: "reviewer-kavya",
        reason: reviewerReason || `Action ${decision.toLowerCase()} via Review Console`,
        confirmation_phrase: action.required_confirmation_phrase ? confirmationPhrase : undefined
      });

      setFeedback({
        type: 'success',
        message: `${res.message} ${res.executed ? 'Mock tool executed successfully.' : 'Action blocked.'}`
      });

      setTimeout(() => {
        onDecisionSubmitted();
        onClose();
      }, 1500);
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.message || 'Failed to submit approval decision.'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
      <div className="bg-[#0d1527] border border-[#19253d] rounded-2xl max-w-lg w-full p-6 shadow-2xl overflow-hidden flex flex-col space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between pb-3 border-b border-[#19253d]">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-wide">
                Exact-Action Approval Review
              </h2>
              <p className="text-xs text-slate-400">Action #{action.id} • {action.action_type}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-[#152038] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Action Details Grid */}
        <div className="space-y-3 text-xs">
          <div className="grid grid-cols-2 gap-2 bg-[#090e1a] p-3 rounded-xl border border-[#19253d]">
            <div>
              <span className="text-slate-400 block text-[11px]">Requesting Agent:</span>
              <strong className="text-white font-medium">{action.agent_name}</strong>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Risk Classification:</span>
              <span className={`inline-block font-bold px-2 py-0.5 rounded text-[10px] mt-0.5 ${
                action.risk_level === 'HIGH' ? 'bg-rose-950/70 text-rose-400 border border-rose-800/40' :
                action.risk_level === 'MEDIUM' ? 'bg-amber-950/70 text-amber-400 border border-amber-800/40' :
                'bg-emerald-950/70 text-emerald-400 border border-emerald-800/40'
              }`}>
                {action.risk_level} RISK
              </span>
            </div>
            <div className="col-span-2 mt-1">
              <span className="text-slate-400 block text-[11px]">Target Destination:</span>
              <code className="text-cyan-400 font-mono bg-[#050811] px-2 py-1 rounded block mt-0.5 border border-[#19253d]">
                {action.target}
              </code>
            </div>
          </div>

          <div>
            <span className="text-slate-400 block text-[11px] mb-1">Action Description & Context:</span>
            <div className="p-2.5 rounded-lg bg-[#090e1a] border border-[#19253d] text-slate-200">
              {action.description || 'No additional parameters provided.'}
            </div>
          </div>

          {/* Canonical Fingerprint Notice */}
          <div className="p-2.5 rounded-lg bg-blue-950/30 border border-blue-500/30 flex items-start gap-2 text-[11px] text-blue-200">
            <Hash className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
            <div>
              <strong>Cryptographic Fingerprint Bound:</strong> Any modification to target, agent, or payload will cause instant SHA-256 rejection. Valid for 10 minutes (single-use).
            </div>
          </div>

          {/* Tier 3 Risk-Matched Confirmation Friction */}
          {action.required_confirmation_phrase && (
            <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-500/40 space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-rose-300">
                <ShieldAlert className="w-4 h-4 text-rose-400" />
                <span>Tier 3 Friction: Confirmation Phrase Required</span>
              </div>
              <p className="text-[11px] text-slate-300">
                To approve this critical high-risk operation, you must type the exact confirmation phrase below:
              </p>
              <div className="bg-[#090e1a] px-2 py-1 rounded font-mono text-xs text-rose-300 border border-rose-900/60 select-all">
                {action.required_confirmation_phrase}
              </div>
              <input
                type="text"
                value={confirmationPhrase}
                onChange={(e) => setConfirmationPhrase(e.target.value)}
                placeholder={`Type "${action.required_confirmation_phrase}"`}
                className="w-full bg-[#090e1a] border border-rose-500/50 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-rose-400 font-mono"
              />
            </div>
          )}

          {/* Reviewer Note Input */}
          <div>
            <label className="block text-slate-400 text-[11px] mb-1">
              Reviewer Justification Note (Optional):
            </label>
            <input
              type="text"
              value={reviewerReason}
              onChange={(e) => setReviewerReason(e.target.value)}
              placeholder="e.g. Verified customer authorization ticket #982"
              className="w-full bg-[#090e1a] border border-[#19253d] rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>

        {/* Feedback message */}
        {feedback && (
          <div className={`p-2.5 rounded-lg text-xs flex items-center gap-2 ${
            feedback.type === 'success' ? 'bg-emerald-950/60 border border-emerald-500/40 text-emerald-300' :
            'bg-rose-950/60 border border-rose-500/40 text-rose-300'
          }`}>
            {feedback.type === 'success' ? <CheckCircle className="w-4 h-4 shrink-0" /> : <XCircle className="w-4 h-4 shrink-0" />}
            <span>{feedback.message}</span>
          </div>
        )}

        {/* Decision Buttons */}
        <div className="flex items-center justify-end gap-3 pt-2 border-t border-[#19253d]">
          <button
            type="button"
            onClick={onClose}
            className="px-3.5 py-1.5 rounded-lg border border-[#233354] hover:bg-[#141e34] text-slate-300 text-xs transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => handleDecision('REJECTED')}
            className="px-4 py-1.5 rounded-lg bg-rose-900/60 hover:bg-rose-800/80 border border-rose-700/50 text-rose-200 text-xs font-semibold transition-colors disabled:opacity-50"
          >
            Reject & Block
          </button>
          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => handleDecision('APPROVED')}
            className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md transition-colors disabled:opacity-50"
          >
            {isSubmitting ? 'Verifying...' : 'Approve & Execute'}
          </button>
        </div>
      </div>
    </div>
  );
};
