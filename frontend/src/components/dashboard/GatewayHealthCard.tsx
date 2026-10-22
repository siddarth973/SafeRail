import React from 'react';
import { ShieldCheck } from 'lucide-react';
import { SegmentedGauge } from './SegmentedGauge';

interface GatewayHealthCardProps {
  healthScore?: number;
  healthyPercent?: number;
  warningPercent?: number;
  criticalPercent?: number;
}

export const GatewayHealthCard: React.FC<GatewayHealthCardProps> = ({
  healthScore = 98,
  healthyPercent = 98,
  warningPercent = 2,
  criticalPercent = 0,
}) => {
  return (
    <div className="bg-[#0d1527] border border-[#19253d] rounded-xl p-5 flex flex-col justify-between shadow-card h-full min-h-[300px]">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-white tracking-wide">Gateway Health</h2>
            <p className="text-xs text-slate-400">Overall system safety and control</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-950/40 border border-emerald-500/30 text-emerald-400 text-xs font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_#10b981]" />
          <span>Live</span>
        </div>
      </div>

      {/* Semicircular Gauge */}
      <div className="py-2 flex items-center justify-center">
        <SegmentedGauge value={healthScore} />
      </div>

      {/* Status Indicators Footer */}
      <div className="pt-3 border-t border-[#19253d]/80 flex items-center justify-around text-xs">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_6px_#10b981]" />
          <span className="text-slate-300 font-medium">Healthy</span>
          <span className="text-white font-semibold ml-1">{healthyPercent}%</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-amber-400 shadow-[0_0_6px_#f59e0b]" />
          <span className="text-slate-300 font-medium">Warning</span>
          <span className="text-white font-semibold ml-1">{warningPercent}%</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-rose-500 shadow-[0_0_6px_#ef4444]" />
          <span className="text-slate-300 font-medium">Critical</span>
          <span className="text-white font-semibold ml-1">{criticalPercent}%</span>
        </div>
      </div>
    </div>
  );
};
