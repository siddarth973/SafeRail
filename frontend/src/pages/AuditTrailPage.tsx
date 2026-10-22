import React, { useEffect, useState } from 'react';
import {
  Hash,
  Lock,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  HelpCircle,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  ArrowUpDown
} from 'lucide-react';
import { fetchAuditEvents, verifyAuditEvent, verifyAuditChain } from '../api/client';
import { AuditEventItem, AuditVerificationResult, AuditChainVerificationResult } from '../types';

export const AuditTrailPage: React.FC = () => {
  const [events, setEvents] = useState<AuditEventItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [chainResult, setChainResult] = useState<AuditChainVerificationResult | null>(null);
  const [verifyingChain, setVerifyingChain] = useState<boolean>(false);
  const [verifyingIds, setVerifyingIds] = useState<Set<number>>(new Set());
  const [verificationMap, setVerificationMap] = useState<Record<number, AuditVerificationResult>>({});
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [filter, setFilter] = useState<'ALL' | 'SIGNED' | 'LEGACY'>('ALL');
  const [sortOrder, setSortOrder] = useState<'NEWEST' | 'OLDEST'>('NEWEST');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 10;

  const loadData = async () => {
    setIsLoading(true);
    try {
      const data = await fetchAuditEvents();
      setEvents(data);
      // Run initial chain verification to populate live ledger health honestly
      setVerifyingChain(true);
      const chain = await verifyAuditChain();
      setChainResult(chain);
    } catch (err) {
      setChainResult(null);
      console.error('Failed to load audit events or verify chain:', err);
    } finally {
      setIsLoading(false);
      setVerifyingChain(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleVerifySingle = async (eventId: number) => {
    setVerifyingIds(prev => new Set(prev).add(eventId));
    try {
      const res = await verifyAuditEvent(eventId);
      setVerificationMap(prev => ({ ...prev, [eventId]: res }));
      setExpandedId(eventId);
    } catch (err: any) {
      alert(`Verification request failed: ${err.message}`);
    } finally {
      setVerifyingIds(prev => {
        const next = new Set(prev);
        next.delete(eventId);
        return next;
      });
    }
  };

  const handleVerifyChainAction = async () => {
    setVerifyingChain(true);
    try {
      const chain = await verifyAuditChain();
      setChainResult(chain);
    } catch (err: any) {
      setChainResult(null);
      alert(`Chain audit failed: ${err.message}`);
    } finally {
      setVerifyingChain(false);
    }
  };

  const handleVerifyAllVisible = async () => {
    const idsToVerify = paginatedEvents.map(e => e.id);
    setVerifyingIds(new Set(idsToVerify));
    try {
      const results = await Promise.all(
        idsToVerify.map(async id => {
          try {
            return await verifyAuditEvent(id);
          } catch (e) {
            return null;
          }
        })
      );
      setVerificationMap(prev => {
        const updated = { ...prev };
        results.forEach(res => {
          if (res) updated[res.event_id] = res;
        });
        return updated;
      });
      // Also refresh chain status
      await handleVerifyChainAction();
    } finally {
      setVerifyingIds(new Set());
    }
  };

  // Filter & Sort Logic
  const filteredEvents = events.filter(ev => {
    if (filter === 'SIGNED') return !!ev.current_hash;
    if (filter === 'LEGACY') return !ev.current_hash;
    return true;
  });

  const sortedEvents = [...filteredEvents].sort((a, b) => {
    return sortOrder === 'NEWEST' ? b.id - a.id : a.id - b.id;
  });

  const totalPages = Math.max(1, Math.ceil(sortedEvents.length / pageSize));
  const paginatedEvents = sortedEvents.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const signedCount = events.filter(e => !!e.current_hash).length;
  const legacyCount = events.length - signedCount;

  // Render Top Validation Badge strictly reflecting verification results
  const renderChainBadge = () => {
    if (verifyingChain) {
      return (
        <span className="px-3 py-1 rounded-full bg-slate-800/80 border border-slate-700 text-slate-300 text-xs font-semibold flex items-center gap-1.5 shadow-sm">
          <RefreshCw className="w-3.5 h-3.5 animate-spin text-cyan-400" />
          <span>Auditing Ledger...</span>
        </span>
      );
    }

    if (!chainResult) {
      return (
        <span className="px-3 py-1 rounded-full bg-slate-900 border border-slate-700/80 text-slate-400 text-xs font-semibold flex items-center gap-1.5 shadow-sm">
          <ShieldAlert className="w-3.5 h-3.5 text-slate-400" />
          <span>Unverified Ledger</span>
        </span>
      );
    }

    if (chainResult.status === 'VALID') {
      return (
        <span className="px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold flex items-center gap-1.5 shadow-[0_0_12px_rgba(16,185,129,0.2)]">
          <Lock className="w-3.5 h-3.5 text-emerald-400" />
          <span>Hash-Chain Validated ({chainResult.valid_count} Blocks)</span>
        </span>
      );
    }

    if (chainResult.status === 'INVALID') {
      return (
        <span className="px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-semibold flex items-center gap-1.5 shadow-[0_0_12px_rgba(244,63,94,0.2)]">
          <XCircle className="w-3.5 h-3.5 text-rose-400" />
          <span>Chain Tampered / Broken ({chainResult.invalid_count} errors)</span>
        </span>
      );
    }

    return (
      <span className="px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-semibold flex items-center gap-1.5">
        <HelpCircle className="w-3.5 h-3.5 text-amber-400" />
        <span>Unverifiable ({chainResult.unverifiable_count} Legacy Unsigned)</span>
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-[#141f33] gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-xl font-bold text-white tracking-wide">Cryptographic Audit Trail</h2>
            <span className="px-2 py-0.5 text-[10px] font-mono font-bold rounded bg-cyan-950/70 text-cyan-400 border border-cyan-800/40">
              SHA-256 Tamper-Evident
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic cryptographic verification of every gateway decision, policy evaluation, and security event.
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          {renderChainBadge()}

          <button
            onClick={handleVerifyChainAction}
            disabled={verifyingChain}
            className="px-3 py-1.5 rounded-lg bg-[#141e34] hover:bg-[#1a2846] text-cyan-400 border border-[#233354] hover:border-cyan-500/40 text-xs font-medium flex items-center gap-1.5 transition-all disabled:opacity-50"
            title="Verify every block from genesis sequentially"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
            <span>Verify Entire Chain</span>
          </button>

          <button
            onClick={loadData}
            disabled={isLoading}
            className="p-1.5 rounded-lg bg-[#141e34] hover:bg-[#1a2846] text-slate-400 hover:text-white border border-[#233354] text-xs transition-colors"
            title="Refresh audit ledger"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Ledger Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl bg-[#0d1527] border border-[#19253d] shadow-card">
          <div className="text-[11px] text-slate-400 font-medium uppercase tracking-wider">Total Ledger Entries</div>
          <div className="text-xl font-bold text-white mt-1 font-mono">{events.length}</div>
          <div className="text-[10px] text-slate-500 mt-0.5">Chronological records in database</div>
        </div>

        <div className="p-3.5 rounded-xl bg-[#0d1527] border border-[#19253d] shadow-card">
          <div className="text-[11px] text-emerald-400/90 font-medium uppercase tracking-wider">Cryptographic Blocks</div>
          <div className="text-xl font-bold text-emerald-400 mt-1 font-mono">{signedCount}</div>
          <div className="text-[10px] text-slate-500 mt-0.5">SHA-256 chained to genesis anchor</div>
        </div>

        <div className="p-3.5 rounded-xl bg-[#0d1527] border border-[#19253d] shadow-card">
          <div className="text-[11px] text-amber-400/90 font-medium uppercase tracking-wider">Legacy Unchained</div>
          <div className="text-xl font-bold text-amber-400 mt-1 font-mono">{legacyCount}</div>
          <div className="text-[10px] text-slate-500 mt-0.5">Pre-Stage 2 (honestly labeled UNVERIFIABLE)</div>
        </div>

        <div className="p-3.5 rounded-xl bg-[#0d1527] border border-[#19253d] shadow-card">
          <div className="text-[11px] text-cyan-400/90 font-medium uppercase tracking-wider">Audit Consensus</div>
          <div className="text-sm font-bold text-cyan-400 mt-1 truncate">
            {chainResult?.status === 'VALID' ? 'VALID (100% Intact)' : chainResult?.status === 'INVALID' ? 'COMPROMISED' : 'READY TO AUDIT'}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5 truncate">
            {chainResult?.message || 'Awaiting full verification run'}
          </div>
        </div>
      </div>

      {/* Main Ledger Card */}
      <div className="bg-[#0d1527] border border-[#19253d] rounded-xl overflow-hidden shadow-card">
        {/* Controls Bar */}
        <div className="p-4 border-b border-[#19253d] flex flex-col md:flex-row md:items-center justify-between gap-3 bg-[#0a101f]">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-white text-sm">Audit Log Records</span>
            <span className="text-xs text-slate-400">({sortedEvents.length} filtered)</span>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Filter Pills */}
            <div className="flex items-center bg-[#121c32] p-0.5 rounded-lg border border-[#1e2c47] text-xs">
              <button
                onClick={() => { setFilter('ALL'); setCurrentPage(1); }}
                className={`px-2.5 py-1 rounded-md transition-colors ${
                  filter === 'ALL' ? 'bg-cyan-500/20 text-cyan-400 font-semibold' : 'text-slate-400 hover:text-white'
                }`}
              >
                All ({events.length})
              </button>
              <button
                onClick={() => { setFilter('SIGNED'); setCurrentPage(1); }}
                className={`px-2.5 py-1 rounded-md transition-colors ${
                  filter === 'SIGNED' ? 'bg-emerald-500/20 text-emerald-400 font-semibold' : 'text-slate-400 hover:text-white'
                }`}
              >
                Signed ({signedCount})
              </button>
              <button
                onClick={() => { setFilter('LEGACY'); setCurrentPage(1); }}
                className={`px-2.5 py-1 rounded-md transition-colors ${
                  filter === 'LEGACY' ? 'bg-amber-500/20 text-amber-400 font-semibold' : 'text-slate-400 hover:text-white'
                }`}
              >
                Legacy ({legacyCount})
              </button>
            </div>

            {/* Sort Toggle */}
            <button
              onClick={() => setSortOrder(prev => prev === 'NEWEST' ? 'OLDEST' : 'NEWEST')}
              className="px-2.5 py-1 rounded-lg bg-[#141e34] border border-[#233354] text-xs text-slate-300 hover:text-cyan-400 flex items-center gap-1.5 transition-colors"
            >
              <ArrowUpDown className="w-3 h-3 text-cyan-400" />
              <span>{sortOrder === 'NEWEST' ? 'Newest First' : 'Oldest First'}</span>
            </button>

            {/* Verify Visible Page */}
            <button
              onClick={handleVerifyAllVisible}
              className="px-2.5 py-1 rounded-lg bg-cyan-950/60 border border-cyan-800/40 text-xs text-cyan-300 hover:text-white hover:bg-cyan-900/60 flex items-center gap-1.5 transition-colors"
            >
              <CheckCircle2 className="w-3 h-3 text-cyan-400" />
              <span>Verify Visible Page</span>
            </button>
          </div>
        </div>

        {/* Ledger Entries List */}
        <div className="divide-y divide-[#162238]">
          {paginatedEvents.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-sm">
              No audit records match the selected filter.
            </div>
          ) : (
            paginatedEvents.map(event => {
              const proof = verificationMap[event.id];
              const isVerifying = verifyingIds.has(event.id);
              const isExpanded = expandedId === event.id;

              return (
                <div
                  key={event.id}
                  className={`p-4 transition-colors ${
                    isExpanded ? 'bg-[#101a30]/80' : 'hover:bg-[#121c32]/40'
                  }`}
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                    {/* Event Core Info */}
                    <div className="space-y-1.5 flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-xs text-slate-400">[{event.time_str}]</span>
                        <span className="text-sm font-semibold text-white tracking-wide">{event.title}</span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                          event.status_tag === 'BLOCKED' ? 'bg-rose-950/60 text-rose-400 border border-rose-800/40' :
                          event.status_tag === 'APPROVED' ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/40' :
                          event.status_tag === 'WARNING' ? 'bg-amber-950/60 text-amber-400 border border-amber-800/40' :
                          'bg-blue-950/60 text-cyan-400 border border-blue-800/40'
                        }`}>
                          {event.status_tag}
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono">ID #{event.id}</span>
                      </div>

                      <div className="text-xs text-slate-300 leading-relaxed">{event.description}</div>

                      {/* Cryptographic Hash Line */}
                      <div className="text-[11px] font-mono flex items-center gap-2 flex-wrap">
                        {event.current_hash ? (
                          <>
                            <div className="flex items-center gap-1 text-cyan-400 bg-cyan-950/30 px-2 py-0.5 rounded border border-cyan-900/40">
                              <Hash className="w-3 h-3 text-cyan-400" />
                              <span title={event.current_hash}>
                                SHA256: {event.current_hash.slice(0, 10)}...{event.current_hash.slice(-8)}
                              </span>
                              <span className="text-slate-400 text-[10px]">
                                (Block #{event.sequence_number || event.id})
                              </span>
                            </div>
                            <span className="text-[10px] text-slate-500 truncate" title={event.prev_hash || ''}>
                              Prev: {event.prev_hash?.startsWith('GENESIS') ? 'GENESIS_0000... (Root)' : event.prev_hash ? event.prev_hash.slice(0, 8) + '...' : 'None'}
                            </span>
                          </>
                        ) : (
                          <div className="flex items-center gap-1 text-amber-400/90 italic bg-amber-950/20 px-2 py-0.5 rounded border border-amber-900/30">
                            <HelpCircle className="w-3 h-3 text-amber-400" />
                            <span>Legacy unchained record (created prior to SHA-256 hash chaining)</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Verification Actions & Honest Result Badge */}
                    <div className="flex items-center gap-2 shrink-0">
                      {proof ? (
                        <div className="flex items-center gap-1.5">
                          {proof.status === 'VALID' && (
                            <span className="px-2.5 py-1 rounded bg-emerald-950/60 border border-emerald-500/40 text-emerald-400 text-xs font-semibold flex items-center gap-1 shadow-sm">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              <span>VALID</span>
                            </span>
                          )}

                          {proof.status === 'INVALID' && (
                            <span className="px-2.5 py-1 rounded bg-rose-950/60 border border-rose-500/40 text-rose-400 text-xs font-semibold flex items-center gap-1 shadow-sm">
                              <XCircle className="w-3.5 h-3.5" />
                              <span>INVALID</span>
                            </span>
                          )}

                          {proof.status === 'UNVERIFIABLE' && (
                            <span className="px-2.5 py-1 rounded bg-amber-950/60 border border-amber-500/40 text-amber-400 text-xs font-semibold flex items-center gap-1 shadow-sm">
                              <HelpCircle className="w-3.5 h-3.5" />
                              <span>UNVERIFIABLE</span>
                            </span>
                          )}

                          <button
                            onClick={() => setExpandedId(isExpanded ? null : event.id)}
                            className="p-1 text-slate-400 hover:text-white rounded hover:bg-[#1a2846] transition-colors"
                            title="Toggle cryptographic proof details"
                          >
                            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => handleVerifySingle(event.id)}
                          disabled={isVerifying}
                          className="px-3 py-1 text-xs text-cyan-400 hover:text-white border border-[#233354] hover:border-cyan-500/40 rounded bg-[#141e34] hover:bg-cyan-600/20 transition-all font-medium flex items-center gap-1.5 disabled:opacity-50"
                        >
                          {isVerifying ? (
                            <>
                              <RefreshCw className="w-3 h-3 animate-spin text-cyan-400" />
                              <span>Verifying...</span>
                            </>
                          ) : (
                            <span>Verify Hash</span>
                          )}
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Expandable Cryptographic Proof Details */}
                  {isExpanded && proof && (
                    <div className="mt-3.5 p-3.5 rounded-lg bg-[#080d1a] border border-[#1e2c47] text-xs font-mono space-y-2.5">
                      <div className="flex items-center justify-between pb-2 border-b border-[#162238]">
                        <span className="font-semibold text-slate-200">Cryptographic Integrity Proof</span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          proof.status === 'VALID' ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800' :
                          proof.status === 'INVALID' ? 'bg-rose-950/80 text-rose-400 border border-rose-800' :
                          'bg-amber-950/80 text-amber-400 border border-amber-800'
                        }`}>
                          {proof.status}
                        </span>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 text-[11px]">
                        <div className="space-y-0.5">
                          <span className="text-slate-500 block">Stored Record Hash:</span>
                          <span className="text-slate-300 break-all select-all font-mono">
                            {proof.stored_hash || '(None - unhashed record)'}
                          </span>
                        </div>

                        <div className="space-y-0.5">
                          <span className="text-slate-500 block">Recomputed SHA-256 Hash:</span>
                          <span className="text-slate-300 break-all select-all font-mono">
                            {proof.computed_hash || '(Cannot recompute without genesis/sequence linkage)'}
                          </span>
                        </div>

                        <div className="space-y-0.5">
                          <span className="text-slate-500 block">Stored Predecessor Hash:</span>
                          <span className="text-slate-300 break-all select-all font-mono">
                            {proof.prev_hash || '(None)'}
                          </span>
                        </div>

                        <div className="space-y-0.5">
                          <span className="text-slate-500 block">Expected Predecessor Hash:</span>
                          <span className="text-slate-300 break-all select-all font-mono">
                            {proof.expected_prev_hash || '(None)'}
                          </span>
                        </div>
                      </div>

                      <div className="pt-2 border-t border-[#162238] flex flex-col md:flex-row md:items-center justify-between gap-2 text-slate-400 text-[11px]">
                        <div>
                          Verification Explanation: <strong className="text-slate-200">{proof.reason}</strong>
                        </div>
                        {proof.sequence_number && (
                          <span className="text-cyan-400">Ledger Block #{proof.sequence_number}</span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Pagination Controls */}
        <div className="p-3 border-t border-[#19253d] flex items-center justify-between bg-[#0a101f] text-xs text-slate-400">
          <div>
            Showing {paginatedEvents.length} of {sortedEvents.length} events (Page {currentPage} of {totalPages})
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-2.5 py-1 rounded bg-[#141e34] border border-[#233354] hover:text-white disabled:opacity-40 disabled:hover:text-slate-400 transition-colors"
            >
              Previous
            </button>
            <span className="font-mono text-white px-1">{currentPage}</span>
            <button
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="px-2.5 py-1 rounded bg-[#141e34] border border-[#233354] hover:text-white disabled:opacity-40 disabled:hover:text-slate-400 transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
