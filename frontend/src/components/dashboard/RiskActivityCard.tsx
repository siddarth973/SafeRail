import React from 'react';
import { Activity, ChevronDown } from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip
} from 'recharts';

interface RiskActivityCardProps {
  totalActions?: number;
  totalActionsDelta?: string;
  blockedActions?: number;
  blockedActionsDelta?: string;
  pendingApprovals?: number;
  pendingApprovalsDelta?: string;
}

const chartData = [
  { time: '12 AM', total: 45, blocked: 8, pending: 6 },
  { time: '4 AM', total: 42, blocked: 9, pending: 8 },
  { time: '8 AM', total: 60, blocked: 18, pending: 11 },
  { time: '12 PM', total: 54, blocked: 12, pending: 9 },
  { time: '4 PM', total: 68, blocked: 22, pending: 14 },
  { time: '8 PM', total: 52, blocked: 11, pending: 7 },
  { time: 'Now', total: 58, blocked: 16, pending: 8 },
];

export const RiskActivityCard: React.FC<RiskActivityCardProps> = ({
  totalActions = 248,
  totalActionsDelta = "↑ 12%",
  blockedActions = 18,
  blockedActionsDelta = "↓ 6%",
  pendingApprovals = 7,
  pendingApprovalsDelta = "↑ 40%"
}) => {
  return (
    <div className="bg-[#0d1527] border border-[#19253d] rounded-xl p-5 flex flex-col justify-between shadow-card h-full min-h-[300px]">
      {/* Header */}
      <div>
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <Activity className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white tracking-wide">Risk Activity</h2>
              <p className="text-xs text-slate-400">Threats and risk events (last 24 hours)</p>
            </div>
          </div>

          <div className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[#141e34] border border-[#233354] text-xs text-slate-300 cursor-pointer hover:bg-[#1a2744] transition-colors">
            <span>Last 24 hours</span>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center justify-end gap-4 text-[11px] text-slate-400 mb-1">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-blue-500" />
            <span>Total</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-rose-500" />
            <span>Blocked</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-400" />
            <span>Pending</span>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="w-full h-36">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 10, left: -25, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#162238" vertical={false} />
            <XAxis
              dataKey="time"
              stroke="#64748b"
              fontSize={10}
              tickLine={false}
              axisLine={{ stroke: '#19253d' }}
            />
            <YAxis
              stroke="#64748b"
              fontSize={10}
              domain={[0, 80]}
              ticks={[0, 20, 40, 60, 80]}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0d1527',
                borderColor: '#1e293b',
                borderRadius: '8px',
                fontSize: '11px',
                color: '#f8fafc',
                boxShadow: '0 4px 12px rgba(0,0,0,0.5)'
              }}
            />
            <Line
              type="monotone"
              dataKey="total"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#3b82f6' }}
            />
            <Line
              type="monotone"
              dataKey="blocked"
              stroke="#ef4444"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#ef4444' }}
            />
            <Line
              type="monotone"
              dataKey="pending"
              stroke="#f59e0b"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#f59e0b' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Summary Stats Row */}
      <div className="pt-3 border-t border-[#19253d]/80 grid grid-cols-3 divide-x divide-[#19253d] text-left">
        <div className="pr-2">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider">Total Actions</div>
          <div className="flex items-baseline gap-2 mt-0.5">
            <span className="text-xl font-bold text-white">{totalActions}</span>
            <span className="text-[11px] text-emerald-400 font-medium">{totalActionsDelta}</span>
          </div>
        </div>

        <div className="px-3">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider">Blocked Actions</div>
          <div className="flex items-baseline gap-2 mt-0.5">
            <span className="text-xl font-bold text-white">{blockedActions}</span>
            <span className="text-[11px] text-rose-400 font-medium">{blockedActionsDelta}</span>
          </div>
        </div>

        <div className="pl-3">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider">Pending Approvals</div>
          <div className="flex items-baseline gap-2 mt-0.5">
            <span className="text-xl font-bold text-white">{pendingApprovals}</span>
            <span className="text-[11px] text-amber-400 font-medium">{pendingApprovalsDelta}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
