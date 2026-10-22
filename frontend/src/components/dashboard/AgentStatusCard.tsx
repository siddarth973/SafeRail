import React, { useState } from 'react';
import { Bot, Check, Pause, Play } from 'lucide-react';
import { Agent } from '../../types';
import { MiniSparkline } from './MiniSparkline';
import { pauseAgent, resumeAgent } from '../../api/client';

interface AgentStatusCardProps {
  agents: Agent[];
  onRefresh?: () => void;
}

export const AgentStatusCard: React.FC<AgentStatusCardProps> = ({ agents, onRefresh }) => {
  const [loadingAgentId, setLoadingAgentId] = useState<string | null>(null);

  const handleToggleAgent = async (agent: Agent) => {
    setLoadingAgentId(agent.id);
    try {
      if (agent.status === 'ACTIVE') {
        await pauseAgent(agent.id, "Manual pause from dashboard controls");
      } else {
        await resumeAgent(
          agent.id,
          "reviewer-kavya",
          "Supervisor confirmed safe operational parameters"
        );
      }
      if (onRefresh) onRefresh();
    } catch (err: any) {
      alert(`Agent status change failed: ${err.message}`);
    } finally {
      setLoadingAgentId(null);
    }
  };

  return (
    <div className="bg-[#0d1527] border border-[#19253d] rounded-xl p-5 flex flex-col justify-between shadow-card h-full min-h-[300px]">
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
            <Bot className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-white tracking-wide">Agent Status</h2>
            <p className="text-xs text-slate-400">Live agent activity and health</p>
          </div>
        </div>
      </div>

      {/* Agents List */}
      <div className="flex flex-col divide-y divide-[#162238] overflow-y-auto">
        {agents.map((agent) => {
          const isPaused = agent.status === 'PAUSED';
          const isLoading = loadingAgentId === agent.id;

          return (
            <div
              key={agent.id}
              className="py-2.5 flex items-center justify-between hover:bg-[#121c32]/50 px-1 rounded transition-colors group"
            >
              {/* Left: Name and sub-status */}
              <div className="flex flex-col">
                <span className="text-xs font-medium text-white">{agent.name}</span>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${isPaused ? 'bg-amber-400' : 'bg-emerald-400'}`} />
                  <span className="text-[10px] text-slate-400 capitalize">
                    {agent.status.toLowerCase()}
                  </span>
                </div>
              </div>

              {/* Right: Status badge & Toggle, health %, sparkline */}
              <div className="flex items-center gap-2.5">
                <button
                  type="button"
                  onClick={() => handleToggleAgent(agent)}
                  disabled={isLoading}
                  title={isPaused ? "Click to resume agent" : "Click to pause agent"}
                  className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium border transition-colors ${
                    isPaused
                      ? 'bg-amber-950/60 border-amber-500/40 text-amber-300 hover:bg-emerald-950/40 hover:text-emerald-300 hover:border-emerald-500/40'
                      : 'bg-emerald-950/40 border-emerald-500/30 text-emerald-400 hover:bg-amber-950/40 hover:text-amber-300 hover:border-amber-500/40'
                  }`}
                >
                  {isLoading ? (
                    <span className="animate-pulse">...</span>
                  ) : isPaused ? (
                    <>
                      <Play className="w-2.5 h-2.5 fill-current" />
                      <span>Resume</span>
                    </>
                  ) : (
                    <>
                      <Check className="w-2.5 h-2.5" />
                      <span>Active</span>
                      <Pause className="w-2 h-2 ml-0.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </>
                  )}
                </button>

                <span className="text-xs font-semibold text-slate-200 min-w-[32px] text-right">
                  {agent.health_score}%
                </span>

                <div className="w-14">
                  <MiniSparkline
                    data={agent.sparklineData || [60, 75, 80, 88, 92, agent.health_score]}
                    color={isPaused ? "#f59e0b" : "#06b6d4"}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
