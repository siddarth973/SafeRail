import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Database, Sparkles, RefreshCw, Terminal } from 'lucide-react';
import { GatewayHealthCard } from '../components/dashboard/GatewayHealthCard';
import { RiskActivityCard } from '../components/dashboard/RiskActivityCard';
import { AgentStatusCard } from '../components/dashboard/AgentStatusCard';
import { PendingActionsCard } from '../components/dashboard/PendingActionsCard';
import { OversightHealthCard } from '../components/dashboard/OversightHealthCard';
import { RecentSecurityEventsCard } from '../components/dashboard/RecentSecurityEventsCard';
import { GatewaySimulatorModal } from '../components/dashboard/GatewaySimulatorModal';
import { fetchDashboardSummary, INITIAL_FIXTURE_DATA } from '../api/client';
import { DashboardData } from '../types';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData>(INITIAL_FIXTURE_DATA);
  const [isFixture, setIsFixture] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSimulatorOpen, setIsSimulatorOpen] = useState<boolean>(false);

  const loadData = async () => {
    setIsLoading(true);
    const result = await fetchDashboardSummary();
    setData(result.data);
    setIsFixture(result.isFixture);
    setIsLoading(false);
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-5 pb-8">
      {/* Action Simulator Modal */}
      <GatewaySimulatorModal
        isOpen={isSimulatorOpen}
        onClose={() => setIsSimulatorOpen(false)}
        onActionComplete={loadData}
      />

      {/* Backend & Fixture status banner + Action Simulator Trigger */}
      <div className="flex items-center justify-between px-3 py-1.5 rounded-lg bg-[#0d1527]/70 border border-[#19253d] text-xs">
        <div className="flex items-center gap-2">
          {isFixture ? (
            <>
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <span className="text-slate-300">
                Mode: <span className="text-amber-400 font-semibold">Development Fixtures</span> (Initial UI Baseline)
              </span>
            </>
          ) : (
            <>
              <Database className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-slate-300">
                Mode: <span className="text-emerald-400 font-semibold">Live Backend Connected</span> (FastAPI + SQLite: saferail.db)
              </span>
            </>
          )}
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setIsSimulatorOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-gradient-to-r from-cyan-600/80 to-blue-600/80 hover:from-cyan-500 hover:to-blue-500 text-white font-medium shadow-[0_0_10px_rgba(6,182,212,0.25)] border border-cyan-400/40 transition-all text-xs"
          >
            <Terminal className="w-3.5 h-3.5 text-cyan-200" />
            <span>Simulate Agent Action</span>
          </button>

          <button
            onClick={loadData}
            disabled={isLoading}
            className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-cyan-400 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* TOP DASHBOARD ROW (3 Columns) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 items-stretch">
        <div className="h-full">
          <GatewayHealthCard
            healthScore={data.gateway_health}
            healthyPercent={data.healthy_percent}
            warningPercent={data.warning_percent}
            criticalPercent={data.critical_percent}
          />
        </div>

        <div className="h-full">
          <RiskActivityCard
            totalActions={data.total_actions}
            totalActionsDelta={data.total_actions_delta}
            blockedActions={data.blocked_actions}
            blockedActionsDelta={data.blocked_actions_delta}
            pendingApprovals={data.pending_approvals}
            pendingApprovalsDelta={data.pending_approvals_delta}
          />
        </div>

        <div className="h-full">
          <AgentStatusCard agents={data.agents} onRefresh={loadData} />
        </div>
      </div>

      {/* BOTTOM DASHBOARD ROW (3 Columns) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 items-stretch">
        <div className="h-full">
          <PendingActionsCard
            actions={data.pending_actions}
            onViewAll={() => navigate('/approvals')}
            onRefresh={loadData}
          />
        </div>

        <div className="h-full">
          <OversightHealthCard
            oversight={data.oversight}
            onViewDrills={() => navigate('/oversight')}
          />
        </div>

        <div className="h-full">
          <RecentSecurityEventsCard
            events={data.recent_events}
            onViewAll={() => navigate('/audit')}
          />
        </div>
      </div>
    </div>
  );
};
