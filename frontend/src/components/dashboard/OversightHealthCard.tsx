import React from 'react';
import {
  HeartPulse,
  UserCheck,
  Shield,
  AlertTriangle,
  CheckCircle2,
  ArrowRight
} from 'lucide-react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts';
import { CircularHealthGauge } from './CircularHealthGauge';
import { OversightHealthData } from '../../types';

interface OversightHealthCardProps {
  oversight?: OversightHealthData;
  onViewDrills?: () => void;
}

const fatigueData = [
  { date: 'Apr 14', approvals: 45, fatigueRisk: 22 },
  { date: 'Apr 15', approvals: 68, fatigueRisk: 35 },
  { date: 'Apr 16', approvals: 52, fatigueRisk: 28 },
  { date: 'Apr 17', approvals: 80, fatigueRisk: 42 },
  { date: 'Apr 18', approvals: 62, fatigueRisk: 30 },
];

export const OversightHealthCard: React.FC<OversightHealthCardProps> = ({
  oversight = {
    reviewer_health: 82,
    reviewer_health_status: "Good",
    reviewer_attention_rate: 78,
    approval_budget_used: 68,
    approval_budget_total: 100,
    active_restrictions: 1,
    gateway_health: 98
  },
  onViewDrills
}) => {
  return (
    <div className="bg-[#0d1527] border border-[#19253d] rounded-xl p-5 flex flex-col justify-between shadow-card h-full min-h-[380px]">
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-teal-500/10 border border-teal-500/20 text-teal-400">
            <HeartPulse className="w-5 h-5 text-teal-400" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-white tracking-wide">Oversight Health</h2>
            <p className="text-xs text-slate-400">Reviewer performance, system patterns and risk</p>
          </div>
        </div>
      </div>

      {/* Top Split: Health Gauge + Fatigue Trend */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 items-center bg-[#090e1a]/60 p-2 rounded-lg border border-[#19253d]">
        {/* Left: Circular Health Gauge */}
        <div className="flex justify-center border-b md:border-b-0 md:border-r border-[#19253d] pb-2 md:pb-0">
          <CircularHealthGauge
            score={oversight.reviewer_health}
            total={100}
            statusText={oversight.reviewer_health_status}
            subtext="System is performing well."
          />
        </div>

        {/* Right: Approval Fatigue Trend */}
        <div className="flex flex-col h-full justify-between pt-1">
          <div className="flex items-center justify-between text-[11px] mb-1 px-1">
            <span className="text-slate-300 font-medium">Approval Fatigue Trend</span>
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1 text-[10px] text-slate-400">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500" /> Approvals
              </span>
              <span className="flex items-center gap-1 text-[10px] text-slate-400">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" /> Fatigue Risk
              </span>
            </div>
          </div>

          <div className="w-full h-24">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={fatigueData} margin={{ top: 5, right: 5, left: -28, bottom: 0 }}>
                <XAxis dataKey="date" stroke="#64748b" fontSize={9} tickLine={false} axisLine={false} />
                <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} stroke="#64748b" fontSize={9} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0d1527',
                    borderColor: '#1e293b',
                    borderRadius: '6px',
                    fontSize: '10px',
                    color: '#f8fafc'
                  }}
                />
                <Line type="monotone" dataKey="approvals" stroke="#3b82f6" strokeWidth={1.8} dot={{ r: 2 }} />
                <Line type="monotone" dataKey="fatigueRisk" stroke="#f59e0b" strokeWidth={1.8} dot={{ r: 2 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Middle: 3 Metric Cards */}
      <div className="grid grid-cols-3 gap-2 my-2">
        {/* Metric 1 */}
        <div className="bg-[#090e1a]/80 p-2.5 rounded-lg border border-[#19253d]">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
            <UserCheck className="w-3.5 h-3.5 text-cyan-400" />
            <span className="truncate">Reviewer Attention</span>
          </div>
          <div className="text-lg font-bold text-white mt-0.5">{oversight.reviewer_attention_rate}%</div>
          <div className="text-[10px] text-slate-400">Active reviewers</div>
          <div className="text-[10px] text-emerald-400 font-medium mt-0.5">↑ 12% vs. prev week</div>
        </div>

        {/* Metric 2 */}
        <div className="bg-[#090e1a]/80 p-2.5 rounded-lg border border-[#19253d]">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
            <Shield className="w-3.5 h-3.5 text-blue-400" />
            <span className="truncate">Approval Budget</span>
          </div>
          <div className="text-lg font-bold text-white mt-0.5">
            {oversight.approval_budget_used} <span className="text-xs font-normal text-slate-400">/ {oversight.approval_budget_total}</span>
          </div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full mt-1 overflow-hidden">
            <div
              className="bg-cyan-500 h-full rounded-full transition-all"
              style={{ width: `${(oversight.approval_budget_used / oversight.approval_budget_total) * 100}%` }}
            />
          </div>
          <div className="text-[10px] text-slate-400 mt-1">67% used</div>
        </div>

        {/* Metric 3 */}
        <div className="bg-[#090e1a]/80 p-2.5 rounded-lg border border-[#19253d]">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            <span className="truncate">Automatic Restrictions</span>
          </div>
          <div className="text-lg font-bold text-white mt-0.5">{oversight.active_restrictions}</div>
          <div className="text-[10px] text-slate-400">Active restriction</div>
          <button className="text-[10px] text-cyan-400 hover:text-cyan-300 font-medium mt-0.5 flex items-center gap-0.5">
            View details →
          </button>
        </div>
      </div>

      {/* Bottom: Safety Drills */}
      <div className="pt-2 border-t border-[#19253d]/80">
        <div className="flex items-center justify-between text-xs mb-2">
          <span className="font-semibold text-white">Safety Drills</span>
          <button
            onClick={onViewDrills}
            className="text-[11px] text-slate-400 hover:text-cyan-400 flex items-center gap-0.5 transition-colors"
          >
            <span>View All</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          {/* Drill 1 */}
          <div className="bg-[#090e1a]/80 p-2 rounded-lg border border-[#19253d] flex flex-col justify-between">
            <div>
              <div className="text-[11px] font-medium text-slate-200">Attention Check</div>
              <div className="text-[9px] text-slate-400">Apr 17, 10:15 AM</div>
            </div>
            <div className="mt-1.5 flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-950/40 border border-emerald-500/30 px-1.5 py-0.5 rounded w-fit">
              <CheckCircle2 className="w-2.5 h-2.5" />
              <span>Completed</span>
            </div>
          </div>

          {/* Drill 2 */}
          <div className="bg-[#090e1a]/80 p-2 rounded-lg border border-[#19253d] flex flex-col justify-between">
            <div>
              <div className="text-[11px] font-medium text-slate-200">Policy Understanding</div>
              <div className="text-[9px] text-slate-400">Apr 16, 11:20 AM</div>
            </div>
            <div className="mt-1.5 flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-950/40 border border-emerald-500/30 px-1.5 py-0.5 rounded w-fit">
              <CheckCircle2 className="w-2.5 h-2.5" />
              <span>Completed</span>
            </div>
          </div>

          {/* Drill 3 */}
          <div className="bg-[#090e1a]/80 p-2 rounded-lg border border-[#19253d] flex flex-col justify-between">
            <div>
              <div className="text-[11px] font-medium text-slate-200">Risk Recognition</div>
              <div className="text-[9px] text-slate-400">Apr 14, 8:55 PM</div>
            </div>
            <div className="mt-1.5 flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-950/40 border border-emerald-500/30 px-1.5 py-0.5 rounded w-fit">
              <CheckCircle2 className="w-2.5 h-2.5" />
              <span>Completed</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
