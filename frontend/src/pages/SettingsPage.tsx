import React, { useState } from 'react';
import { Shield, Sliders, UserCheck } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const [failClosed, setFailClosed] = useState(true);
  const [drillFrequency, setDrillFrequency] = useState('Daily');
  const [budgetLimit, setBudgetLimit] = useState(100);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-[#141f33]">
        <div>
          <h2 className="text-xl font-bold text-white">Gateway & Policy Settings</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Configure safety thresholds, reviewer fatigue limits, and gateway intercept policies
          </p>
        </div>
        <button
          onClick={() => alert('Settings configuration saved locally.')}
          className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-sm transition-colors"
        >
          Save Changes
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Fail-closed Gateway Rule */}
        <div className="bg-[#0d1527] border border-[#19253d] rounded-xl p-5 shadow-card space-y-4">
          <div className="flex items-center gap-2 text-white font-semibold text-sm">
            <Shield className="w-5 h-5 text-emerald-400" />
            <span>Gateway Fail-Closed Enforcement</span>
          </div>
          <p className="text-xs text-slate-400">
            If the SafeRail gateway, database, or reviewer verification engine is unreachable or uncertain, actions automatically fail-closed and are quarantined.
          </p>
          <div className="flex items-center justify-between pt-2">
            <span className="text-xs text-slate-300 font-medium">Enforce Fail-Closed Mode</span>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={failClosed}
                onChange={(e) => setFailClosed(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-500"></div>
            </label>
          </div>
        </div>

        {/* Attention Drills Configuration */}
        <div className="bg-[#0d1527] border border-[#19253d] rounded-xl p-5 shadow-card space-y-4">
          <div className="flex items-center gap-2 text-white font-semibold text-sm">
            <Sliders className="w-5 h-5 text-cyan-400" />
            <span>Reviewer Attention Drills</span>
          </div>
          <p className="text-xs text-slate-400">
            Schedule benign synthetic traps that simulate unauthorized commands to continuously measure reviewer attention without risk.
          </p>
          <div className="flex items-center justify-between pt-2">
            <span className="text-xs text-slate-300 font-medium">Drill Frequency</span>
            <select
              value={drillFrequency}
              onChange={(e) => setDrillFrequency(e.target.value)}
              className="bg-[#090e1a] border border-[#19253d] text-white text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-cyan-500"
            >
              <option value="Hourly">Hourly</option>
              <option value="Daily">Daily</option>
              <option value="Weekly">Weekly</option>
            </select>
          </div>
        </div>

        {/* Approval Budget Limit */}
        <div className="bg-[#0d1527] border border-[#19253d] rounded-xl p-5 shadow-card space-y-4 md:col-span-2">
          <div className="flex items-center gap-2 text-white font-semibold text-sm">
            <UserCheck className="w-5 h-5 text-blue-400" />
            <span>Daily Reviewer Approval Quota</span>
          </div>
          <p className="text-xs text-slate-400">
            Maximum approvals allowed per reviewer per 24 hours before elevated friction and secondary verification are triggered.
          </p>
          <div className="flex items-center gap-4 pt-1">
            <input
              type="range"
              min="20"
              max="200"
              step="10"
              value={budgetLimit}
              onChange={(e) => setBudgetLimit(Number(e.target.value))}
              className="w-64 accent-cyan-400"
            />
            <span className="text-sm font-bold text-cyan-400">{budgetLimit} Approvals / Day</span>
          </div>
        </div>
      </div>
    </div>
  );
};
