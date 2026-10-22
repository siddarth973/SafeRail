import React, { useEffect, useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  UserCheck,
  ShieldAlert,
  AlertTriangle,
  RefreshCw,
  Clock,
  Layers,
  Sliders,
  ShieldCheck,
  Check,
  X
} from 'lucide-react';
import { CircularHealthGauge } from '../components/dashboard/CircularHealthGauge';
import {
  fetchOversightHealth,
  fetchReviewerBudget,
  fetchAttentionDrills,
  submitAttentionDrill,
  fetchRestrictions,
  overrideRestrictions
} from '../api/client';
import {
  OversightHealthResponseStage3,
  ReviewerBudgetData,
  AttentionDrillItem,
  RestrictionStatusResponse
} from '../types';

export const OversightPage: React.FC = () => {
  const [healthData, setHealthData] = useState<OversightHealthResponseStage3 | null>(null);
  const [budgetData, setBudgetData] = useState<ReviewerBudgetData | null>(null);
  const [drills, setDrills] = useState<AttentionDrillItem[]>([]);
  const [restrictions, setRestrictions] = useState<RestrictionStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionNotice, setActionNotice] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Manual Override Modal state
  const [isOverrideOpen, setIsOverrideOpen] = useState(false);
  const [overrideLevel, setOverrideLevel] = useState<number>(0);
  const [overrideReviewer, setOverrideReviewer] = useState('reviewer-kavya');
  const [overrideReason, setOverrideReason] = useState('');
  const [submittingOverride, setSubmittingOverride] = useState(false);

  // Drill submission state
  const [submittingDrillId, setSubmittingDrillId] = useState<string | null>(null);

  const loadAllData = async () => {
    setLoading(true);
    try {
      const [h, b, d, r] = await Promise.all([
        fetchOversightHealth().catch(() => null),
        fetchReviewerBudget().catch(() => null),
        fetchAttentionDrills().catch(() => []),
        fetchRestrictions().catch(() => null)
      ]);
      if (h) setHealthData(h);
      if (b) setBudgetData(b);
      setDrills(d || []);
      if (r) {
        setRestrictions(r);
        setOverrideLevel(r.current_level);
      }
    } catch (err: any) {
      console.error('Failed to load oversight intelligence data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, []);

  const handleDrillAction = async (drillId: string, decision: 'APPROVED' | 'REJECTED') => {
    setSubmittingDrillId(drillId);
    setActionNotice(null);
    try {
      const res = await submitAttentionDrill({
        drill_id: drillId,
        decision,
        reviewer_id: 'reviewer-kavya',
        notes: decision === 'REJECTED' ? 'Vigilant rejection of synthetic security canary' : 'Simulated fatigue approval'
      });
      setActionNotice({
        type: res.is_correct ? 'success' : 'error',
        message: res.message
      });
      await loadAllData();
      setTimeout(() => setActionNotice(null), 5000);
    } catch (err: any) {
      setActionNotice({
        type: 'error',
        message: err.message || 'Drill submission failed'
      });
    } finally {
      setSubmittingDrillId(null);
    }
  };

  const handleOverrideSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!overrideReason.trim()) {
      alert('A typed justification reason is required for safety override audit logging.');
      return;
    }
    setSubmittingOverride(true);
    try {
      const updated = await overrideRestrictions({
        level: overrideLevel,
        reviewer_id: overrideReviewer,
        reason: overrideReason
      });
      setRestrictions(updated);
      setIsOverrideOpen(false);
      setOverrideReason('');
      setActionNotice({
        type: 'success',
        message: `Safety Restriction updated to Level ${updated.current_level} (${updated.level_name}) by ${overrideReviewer}.`
      });
      await loadAllData();
      setTimeout(() => setActionNotice(null), 5000);
    } catch (err: any) {
      alert(`Override failed: ${err.message}`);
    } finally {
      setSubmittingOverride(false);
    }
  };

  const getLevelBadgeClass = (lvl: number) => {
    switch (lvl) {
      case 0:
        return 'bg-emerald-950/60 border-emerald-500/40 text-emerald-300';
      case 1:
        return 'bg-amber-950/60 border-amber-500/40 text-amber-300';
      case 2:
        return 'bg-orange-950/60 border-orange-500/40 text-orange-300';
      case 3:
      default:
        return 'bg-rose-950/60 border-rose-500/40 text-rose-300';
    }
  };

  const score = healthData ? healthData.score : 82;
  const statusText = healthData ? healthData.status : 'HEALTHY';
  const isInsufficientData = healthData?.data_sufficiency === 'INSUFFICIENT_DATA';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-[#141f33] gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-xl font-bold text-white tracking-wide">
              Oversight Health & Reviewer Integrity
            </h2>
            <span className="text-[10px] font-mono uppercase bg-blue-950/60 border border-blue-500/40 text-cyan-300 px-2 py-0.5 rounded">
              Stage 3 Intelligence
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time reviewer fatigue evaluation, deterministic 4-pillar health scoring, and fail-closed automatic tightening
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          {isInsufficientData ? (
            <span className="px-3 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-300 text-xs font-semibold">
              Status: Insufficient Data (0 reviews in window)
            </span>
          ) : (
            <span
              className={`px-3 py-1 rounded-full text-xs font-semibold border ${
                statusText === 'HEALTHY'
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                  : statusText === 'DEGRADED'
                  ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                  : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
              }`}
            >
              Health Score: {score}/100 ({statusText})
            </span>
          )}
          <button
            onClick={loadAllData}
            disabled={loading}
            className="p-1.5 rounded-lg border border-[#19253d] bg-[#0d1527] text-slate-400 hover:text-cyan-400 transition-colors"
            title="Refresh oversight intelligence metrics"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Global Action / Notification Banner */}
      {actionNotice && (
        <div
          className={`p-3.5 rounded-xl border text-xs flex items-center justify-between gap-3 ${
            actionNotice.type === 'success'
              ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-200'
              : 'bg-rose-950/60 border-rose-500/40 text-rose-200'
          }`}
        >
          <div className="flex items-center gap-2">
            {actionNotice.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            )}
            <span>{actionNotice.message}</span>
          </div>
          <button
            onClick={() => setActionNotice(null)}
            className="text-slate-400 hover:text-white"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Top 3 Metric Panels */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Card 1: Reviewer Health Gauge */}
        <div className="bg-[#0d1527] border border-[#19253d] rounded-xl p-5 flex flex-col items-center justify-center shadow-card relative">
          <h3 className="text-xs uppercase font-semibold tracking-wider text-slate-400 mb-2">
            Reviewer Health Index
          </h3>
          <CircularHealthGauge
            score={score}
            total={100}
            statusText={isInsufficientData ? 'Baseline' : statusText}
            subtext={
              isInsufficientData
                ? 'Insufficient review events in window'
                : statusText === 'HEALTHY'
                ? 'High vigilance, low fatigue drift'
                : statusText === 'DEGRADED'
                ? 'Moderate fatigue or drill miss'
                : 'Severe fatigue - tightening active'
            }
          />
          <div className="mt-2 text-center">
            <span
              className={`text-[11px] font-mono px-2 py-0.5 rounded border ${
                healthData?.data_sufficiency === 'INSUFFICIENT_DATA'
                  ? 'bg-slate-800/60 border-slate-700 text-slate-400'
                  : 'bg-blue-950/40 border-blue-500/30 text-cyan-300'
              }`}
            >
              Data: {healthData?.data_sufficiency || 'SUFFICIENT'}
            </span>
          </div>
        </div>

        {/* Card 2: Attention Budget */}
        <div className="bg-[#0d1527] border border-[#19253d] rounded-xl p-5 shadow-card flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2 text-cyan-400 text-sm font-semibold">
                <UserCheck className="w-4 h-4" />
                <span>Approval Budget (24h)</span>
              </div>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                  budgetData?.is_exhausted
                    ? 'bg-rose-950/70 text-rose-300 border-rose-700/50'
                    : budgetData?.is_warning
                    ? 'bg-amber-950/70 text-amber-300 border-amber-700/50'
                    : 'bg-emerald-950/70 text-emerald-300 border-emerald-700/50'
                }`}
              >
                {budgetData?.status || 'HEALTHY'}
              </span>
            </div>

            <div className="space-y-2.5">
              <div className="flex justify-between text-xs text-slate-300">
                <span>Sliding Window Quota:</span>
                <span className="font-mono font-bold text-white">
                  {budgetData?.budget_used ?? 0} / {budgetData?.budget_total ?? 60}
                </span>
              </div>

              {/* Progress bar */}
              <div className="w-full bg-[#090e1a] h-2.5 rounded-full overflow-hidden border border-[#19253d]">
                <div
                  className={`h-full transition-all duration-500 ${
                    budgetData?.is_exhausted
                      ? 'bg-rose-500'
                      : budgetData?.is_warning
                      ? 'bg-amber-500'
                      : 'bg-cyan-500'
                  }`}
                  style={{
                    width: `${Math.min(100, Math.round(((budgetData?.budget_used ?? 0) / (budgetData?.budget_total ?? 60)) * 100))}%`
                  }}
                />
              </div>

              <div className="flex justify-between text-[11px] text-slate-400 font-mono">
                <span>Remaining: {budgetData?.budget_remaining ?? 60}</span>
                <span>Active: {budgetData?.active_reviewer ?? 'reviewer-kavya'}</span>
              </div>
            </div>

            <p className="text-[11px] text-slate-400 mt-3 leading-relaxed">
              When quota exhausts (100%), Tier 2 and Tier 3 manual approvals are held under cool-down to prevent rubber-stamping.
            </p>
          </div>

          <div className="pt-3 border-t border-[#19253d] text-[11px] text-slate-400 flex items-center justify-between">
            <span className="flex items-center gap-1 text-slate-400">
              <Clock className="w-3.5 h-3.5 text-cyan-400" />
              Sliding: 24 Hours
            </span>
            <span className="text-cyan-400 font-medium">Auto-Replenishing</span>
          </div>
        </div>

        {/* Card 3: Active Restriction Controls */}
        <div className="bg-[#0d1527] border border-[#19253d] rounded-xl p-5 shadow-card flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2 text-amber-400 text-sm font-semibold">
                <ShieldAlert className="w-4 h-4" />
                <span>Automatic Tightening</span>
              </div>
              <span
                className={`text-[10px] font-bold px-2.5 py-0.5 rounded border uppercase ${getLevelBadgeClass(
                  restrictions?.current_level ?? 0
                )}`}
              >
                Level {restrictions?.current_level ?? 0}: {restrictions?.level_name ?? 'NORMAL'}
              </span>
            </div>

            <div className="p-3 rounded-lg bg-[#090e1a] border border-[#19253d] space-y-1.5">
              <div className="text-[11px] text-slate-400">Active Enforcement Posture:</div>
              <div className="text-xs text-slate-200 font-medium leading-relaxed">
                {restrictions?.reason || 'Baseline safety rules active. Normal review throughput.'}
              </div>
            </div>

            <p className="text-[11px] text-slate-400 mt-2.5 leading-relaxed">
              Tightens automatically upon reviewer fatigue, rapid approvals, or low health score. Fail-closed posture on uncertainty.
            </p>
          </div>

          <div className="pt-3 border-t border-[#19253d] flex items-center justify-between">
            <span className="text-[11px] text-slate-400">Authorized Override</span>
            <button
              onClick={() => setIsOverrideOpen(true)}
              className="px-2.5 py-1 rounded bg-[#162238] hover:bg-[#1d2d4b] border border-[#233554] text-cyan-300 text-xs font-semibold flex items-center gap-1.5 transition-colors"
            >
              <Sliders className="w-3 h-3 text-cyan-400" />
              <span>Adjust Level</span>
            </button>
          </div>
        </div>
      </div>

      {/* 4-Pillar Oversight Health Breakdown Card */}
      <div className="bg-[#0d1527] border border-[#19253d] rounded-xl p-5 shadow-card space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[#19253d]">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-semibold text-white">
              Deterministic 4-Pillar Oversight Health Breakdown
            </h3>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            Total Score: <strong className="text-white">{score}</strong> / 100
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {healthData?.breakdown.map((item, idx) => (
            <div
              key={idx}
              className="bg-[#090e1a] border border-[#19253d] rounded-xl p-3.5 flex flex-col justify-between space-y-2"
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-300">
                    {item.metric}
                  </span>
                  <span
                    className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded ${
                      item.points_earned >= 20
                        ? 'bg-emerald-950/70 text-emerald-400'
                        : item.points_earned >= 10
                        ? 'bg-amber-950/70 text-amber-400'
                        : 'bg-rose-950/70 text-rose-400'
                    }`}
                  >
                    {item.points_earned} / {item.max_points}
                  </span>
                </div>
                <div className="text-[11px] font-mono text-cyan-400 mt-1">
                  Value: {item.measured_value}
                </div>
              </div>
              <p className="text-[11px] text-slate-400 leading-normal border-t border-[#152035] pt-2">
                {item.explanation}
              </p>
            </div>
          )) || (
            <div className="col-span-4 text-center py-4 text-xs text-slate-400">
              Loading 4-pillar calculation metrics...
            </div>
          )}
        </div>
      </div>

      {/* Synthetic Attention Drills Section */}
      <div className="bg-[#0d1527] border border-[#19253d] rounded-xl p-5 shadow-card space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#19253d] gap-2">
          <div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-semibold text-white">
                Synthetic Attention Drills Console (Feature B3)
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Unannounced simulation canaries designed to measure reviewer alertness. Drills NEVER execute mock tools.
            </p>
          </div>
          <span className="text-[11px] font-mono text-emerald-300 bg-emerald-950/60 border border-emerald-500/40 px-2.5 py-1 rounded w-fit">
            Safe Mode: Simulations Isolated
          </span>
        </div>

        <div className="space-y-3">
          {drills.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-400">
              No active attention drills loaded.
            </div>
          ) : (
            drills.map((drill) => (
              <div
                key={drill.id}
                className="p-4 rounded-xl bg-[#090e1a] border border-[#19253d] flex flex-col md:flex-row md:items-center justify-between gap-4 hover:border-[#223558] transition-colors"
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-mono font-bold text-cyan-400 bg-cyan-950/40 border border-cyan-800/40 px-1.5 py-0.5 rounded">
                      {drill.id}
                    </span>
                    <span className="text-xs font-semibold text-white">
                      {drill.title}
                    </span>
                    <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-blue-950/60 text-blue-300 border border-blue-800/40">
                      {drill.scenario_type}
                    </span>
                    <span className="text-[10px] font-mono text-slate-400 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">
                      SIMULATION ONLY
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed">
                    {drill.description}
                  </p>

                  <div className="flex items-center gap-3 text-[11px] text-slate-400 font-mono">
                    <span>Target: <code className="text-slate-300">{drill.target}</code></span>
                    <span>Expected Safe Action: <strong className="text-emerald-400">{drill.expected_decision}</strong></span>
                    {drill.responded_at && (
                      <span className="text-slate-500">
                        Responded: {new Date(drill.responded_at).toLocaleTimeString()}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {drill.status === 'PENDING' ? (
                    <>
                      <button
                        onClick={() => handleDrillAction(drill.id, 'REJECTED')}
                        disabled={submittingDrillId === drill.id}
                        className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-colors disabled:opacity-50"
                        title="Vigilantly flag & reject this simulated canary (Correct action)"
                      >
                        <Check className="w-3.5 h-3.5" />
                        <span>Reject Canary (Correct)</span>
                      </button>
                      <button
                        onClick={() => handleDrillAction(drill.id, 'APPROVED')}
                        disabled={submittingDrillId === drill.id}
                        className="px-3 py-1.5 rounded-lg bg-[#141e34] hover:bg-rose-950/40 border border-[#233354] hover:border-rose-500/40 text-rose-300 text-xs font-medium transition-colors disabled:opacity-50"
                        title="Test fatigued behavior by approving (Will trigger attention failure)"
                      >
                        <X className="w-3.5 h-3.5" />
                        <span>Approve (Fail Drill)</span>
                      </button>
                    </>
                  ) : (
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-xs font-bold px-2.5 py-1 rounded border flex items-center gap-1.5 ${
                          drill.status === 'PASSED'
                            ? 'bg-emerald-950/70 text-emerald-300 border-emerald-500/40'
                            : 'bg-rose-950/70 text-rose-300 border-rose-500/40'
                        }`}
                      >
                        {drill.status === 'PASSED' ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        ) : (
                          <XCircle className="w-3.5 h-3.5 text-rose-400" />
                        )}
                        <span>{drill.status} (Never Executed)</span>
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Manual Restriction Override Modal */}
      {isOverrideOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-[#0d1527] border border-[#19253d] rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#19253d]">
              <div className="flex items-center gap-2">
                <Sliders className="w-5 h-5 text-cyan-400" />
                <h3 className="text-base font-bold text-white">
                  Authorized Manual Restriction Override
                </h3>
              </div>
              <button
                onClick={() => setIsOverrideOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleOverrideSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1.5">
                  Target Restriction Level:
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { lvl: 0, name: 'Level 0: NORMAL', desc: 'Standard gateway policies' },
                    { lvl: 1, name: 'Level 1: ELEVATED', desc: 'Tier 1 bundling disabled' },
                    { lvl: 2, name: 'Level 2: STRICT', desc: 'Cooldown delay on Tier 2' },
                    { lvl: 3, name: 'Level 3: EMERGENCY', desc: 'Fail-closed: All executions locked' }
                  ].map((opt) => (
                    <button
                      key={opt.lvl}
                      type="button"
                      onClick={() => setOverrideLevel(opt.lvl)}
                      className={`p-2.5 rounded-lg border text-left transition-all ${
                        overrideLevel === opt.lvl
                          ? 'bg-blue-600/20 border-cyan-400 text-white shadow-sm'
                          : 'bg-[#090e1a] border-[#19253d] text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      <div className="font-semibold text-white">{opt.name}</div>
                      <div className="text-[10px] text-slate-400 mt-0.5">{opt.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Authorized Reviewer ID:
                </label>
                <input
                  type="text"
                  value={overrideReviewer}
                  onChange={(e) => setOverrideReviewer(e.target.value)}
                  className="w-full bg-[#090e1a] border border-[#19253d] rounded-lg px-3 py-1.5 text-white font-mono focus:outline-none focus:border-cyan-400"
                  required
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Justification Reason (Logged to Cryptographic Audit Trail):
                </label>
                <textarea
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  rows={3}
                  placeholder="e.g. Cleared pending backlog and refreshed reviewer vigilance shift."
                  className="w-full bg-[#090e1a] border border-[#19253d] rounded-lg px-3 py-1.5 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#19253d]">
                <button
                  type="button"
                  onClick={() => setIsOverrideOpen(false)}
                  className="px-3.5 py-1.5 rounded-lg border border-[#233354] hover:bg-[#141e34] text-slate-300 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingOverride}
                  className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold shadow-md transition-colors disabled:opacity-50"
                >
                  {submittingOverride ? 'Saving...' : 'Apply Authorized Override'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
