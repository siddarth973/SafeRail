import React from 'react';
import {
  ShieldAlert,
  CheckCircle,
  AlertTriangle,
  Info,
  XCircle,
  ArrowRight
} from 'lucide-react';
import { SecurityEvent, SecurityEventTag } from '../../types';

interface RecentSecurityEventsCardProps {
  events: SecurityEvent[];
  onViewAll?: () => void;
}

export const RecentSecurityEventsCard: React.FC<RecentSecurityEventsCardProps> = ({
  events,
  onViewAll
}) => {
  const getEventIcon = (tag: SecurityEventTag, title: string) => {
    if (tag === 'BLOCKED') {
      if (title.includes('Policy Check')) {
        return <AlertTriangle className="w-4 h-4 text-amber-400" />;
      }
      return <XCircle className="w-4 h-4 text-rose-400" />;
    }
    if (tag === 'APPROVED') {
      return <CheckCircle className="w-4 h-4 text-emerald-400" />;
    }
    return <Info className="w-4 h-4 text-cyan-400" />;
  };

  const getTagBadge = (tag: SecurityEventTag) => {
    switch (tag) {
      case 'BLOCKED':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider bg-rose-950/60 text-rose-400 border border-rose-800/40">
            BLOCKED
          </span>
        );
      case 'APPROVED':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
            APPROVED
          </span>
        );
      case 'WARNING':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider bg-amber-950/60 text-amber-400 border border-amber-800/40">
            WARNING
          </span>
        );
      case 'INFO':
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider bg-blue-950/60 text-cyan-400 border border-blue-800/40">
            INFO
          </span>
        );
    }
  };

  return (
    <div className="bg-[#0d1527] border border-[#19253d] rounded-xl p-5 flex flex-col justify-between shadow-card h-full min-h-[380px]">
      {/* Header */}
      <div>
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <ShieldAlert className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white tracking-wide">Recent Security Events</h2>
              <p className="text-xs text-slate-400">Chronological feed of security decisions</p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-950/40 border border-emerald-500/30 text-emerald-400 text-xs font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_#10b981]" />
            <span>Live Feed</span>
          </div>
        </div>
      </div>

      {/* Events Feed List */}
      <div className="flex flex-col divide-y divide-[#162238] overflow-y-auto max-h-[300px] pr-1">
        {events.map((ev) => (
          <div
            key={ev.id}
            className="py-2.5 flex items-center justify-between hover:bg-[#121c32]/50 px-1 rounded transition-colors"
          >
            {/* Left: Icon, Timestamp, Title & Desc */}
            <div className="flex items-center gap-3">
              <div className="w-7 h-7 rounded-full bg-[#141e34] border border-[#233354] flex items-center justify-center shrink-0">
                {getEventIcon(ev.status_tag, ev.title)}
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-400 font-mono">{ev.time_str}</span>
                  <span className="text-xs font-medium text-white">{ev.title}</span>
                </div>
                <div className="text-[11px] text-slate-400 line-clamp-1">{ev.description}</div>
              </div>
            </div>

            {/* Right: Badge */}
            <div className="shrink-0 ml-2">
              {getTagBadge(ev.status_tag)}
            </div>
          </div>
        ))}
      </div>

      {/* Footer Link */}
      <div className="pt-2 border-t border-[#19253d]/80">
        <button
          onClick={onViewAll}
          className="text-xs text-slate-400 hover:text-cyan-400 flex items-center gap-1 transition-colors"
        >
          <span>View All Events</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
