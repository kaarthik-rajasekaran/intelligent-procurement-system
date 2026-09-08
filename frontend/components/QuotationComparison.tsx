'use client';

import React, { useState, useEffect } from 'react';
import { QuotationAnalysis, PurchaseRequest } from '../lib/types';
import { api } from '../lib/api';
import { subscribeSyncEvent } from '../lib/sync';
import {
  Award,
  AlertTriangle,
  CheckCircle2,
  FileCheck2,
  Sparkles,
  ShieldAlert,
  ArrowRight,
  TrendingDown,
  Clock,
  Calendar,
  Lock,
  RefreshCw
} from 'lucide-react';

interface QuotationComparisonProps {
  analysis: QuotationAnalysis | null;
  pr: PurchaseRequest | null;
  onRefresh: () => void;
  userRole: string;
}

export const QuotationComparison: React.FC<QuotationComparisonProps> = ({
  analysis,
  pr,
  onRefresh,
  userRole
}) => {
  const [localAnalysis, setLocalAnalysis] = useState<QuotationAnalysis | null>(analysis);
  const [selectedVendorId, setSelectedVendorId] = useState<string>(
    analysis?.recommended_vendor_id || ''
  );
  const [overrideReason, setOverrideReason] = useState<string>('');
  const [showOverrideDialog, setShowOverrideDialog] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isLocallyFinalized, setIsLocallyFinalized] = useState(false);
  const [isLocallyConfirmed, setIsLocallyConfirmed] = useState(false);
  const [refreshingQuotes, setRefreshingQuotes] = useState(false);

  // AI Explanation state
  const [aiExplanation, setAiExplanation] = useState<string | null>(null);
  const [loadingAi, setLoadingAi] = useState(false);

  const isSupervisor = userRole === 'SUPERVISOR' || userRole === 'ADMIN';
  const isFinalized = isLocallyFinalized || (pr ? (pr.status === 'APPROVED' || pr.status === 'PO_GENERATED' || pr.status === 'COMPLETED') : false);
  const isVendorConfirmed = isLocallyConfirmed || (pr ? (pr.status === 'FINAL_APPROVAL_PENDING' || isFinalized) : false);

  useEffect(() => {
    setLocalAnalysis(analysis);
  }, [analysis]);

  const activeAnalysis = (localAnalysis && pr && localAnalysis.purchase_request_id === pr.id)
    ? localAnalysis
    : (analysis && pr && analysis.purchase_request_id === pr.id ? analysis : null);

  // Ensure selectedVendorId stays in sync when activeAnalysis changes
  useEffect(() => {
    if (activeAnalysis && pr && activeAnalysis.purchase_request_id === pr.id) {
      if (activeAnalysis.recommended_vendor_id) {
        setSelectedVendorId(activeAnalysis.recommended_vendor_id);
      } else if (activeAnalysis.evaluations && activeAnalysis.evaluations.length > 0) {
        setSelectedVendorId(activeAnalysis.evaluations[0].vendor_id);
      } else {
        setSelectedVendorId('');
      }
    } else {
      setSelectedVendorId('');
    }
  }, [activeAnalysis?.purchase_request_id, pr?.id, activeAnalysis?.recommended_vendor_id, activeAnalysis?.evaluations]);

  // Sync confirmed state when PR changes
  useEffect(() => {
    if (pr) {
      if (pr.status === 'FINAL_APPROVAL_PENDING') {
        setIsLocallyConfirmed(true);
      } else {
        setIsLocallyConfirmed(false);
      }
      setStatusMessage(null);
      setShowOverrideDialog(false);
      setOverrideReason('');
    }
  }, [pr?.id, pr?.status]);

  const handleRefreshQuotes = async () => {
    if (!pr) return;
    setRefreshingQuotes(true);
    setStatusMessage(null);
    try {
      const fresh = await api.getQuotationAnalysis(pr.id);
      if (fresh && fresh.purchase_request_id === pr.id) {
        setLocalAnalysis(fresh);
        if (fresh.recommended_vendor_id) {
          setSelectedVendorId(fresh.recommended_vendor_id);
        } else if (fresh.evaluations && fresh.evaluations.length > 0) {
          setSelectedVendorId(fresh.evaluations[0].vendor_id);
        }
      }
      onRefresh();
      setStatusMessage('✓ Quotations refreshed successfully.');
    } catch (err: any) {
      setStatusMessage(err.message || 'Failed to refresh quotes.');
    } finally {
      setRefreshingQuotes(false);
    }
  };

  // Real-time synchronization for new quotations in QuotationComparison
  useEffect(() => {
    if (!pr) return;
    const unsubscribe = subscribeSyncEvent(async (payload) => {
      if (payload.type === 'QUOTATION_SUBMITTED' || payload.type === 'RFQS_ISSUED' || payload.type === 'GENERAL_REFRESH') {
        try {
          const fresh = await api.getQuotationAnalysis(pr.id);
          if (fresh && fresh.purchase_request_id === pr.id) {
            setLocalAnalysis(fresh);
            if (!selectedVendorId && fresh.recommended_vendor_id) {
              setSelectedVendorId(fresh.recommended_vendor_id);
            }
          }
        } catch (_) {}
      }
    });
    return () => {
      unsubscribe();
    };
  }, [pr?.id, selectedVendorId]);

  if (
    !activeAnalysis ||
    !pr ||
    activeAnalysis.purchase_request_id !== pr.id ||
    !activeAnalysis.evaluations ||
    activeAnalysis.evaluations.length === 0
  ) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-8 text-center space-y-4">
        <div className="w-12 h-12 bg-purple-50 text-purple-600 rounded-2xl flex items-center justify-center mx-auto">
          <Clock className="w-6 h-6" />
        </div>
        <div className="max-w-md mx-auto space-y-1">
          <h4 className="font-bold text-slate-900 text-base">Awaiting Competitive Quotations</h4>
          <p className="text-xs text-slate-500 leading-relaxed">
            Requests for Quotation (RFQs) have been dispatched for <span className="font-semibold text-slate-700">{pr?.item_name || 'this request'}</span>.
            Suppliers submit bids through the Vendor Portal. Click Refresh Quotations to check for new submissions.
          </p>
        </div>
        {isSupervisor && pr && (
          <div className="pt-2">
            <button
              onClick={handleRefreshQuotes}
              disabled={refreshingQuotes}
              className="px-5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl border border-slate-200 transition inline-flex items-center space-x-2 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${refreshingQuotes ? 'animate-spin' : ''}`} />
              <span>{refreshingQuotes ? 'Checking for Quotes...' : 'Refresh Quotations'}</span>
            </button>
          </div>
        )}
      </div>
    );
  }

  const recommendedId = activeAnalysis.recommended_vendor_id;
  const isOverriding = Boolean(
    selectedVendorId && recommendedId && String(selectedVendorId).toLowerCase() !== String(recommendedId).toLowerCase()
  );

  const handleSelectVendor = async () => {
    if (!selectedVendorId) return;

    if (isOverriding && (!overrideReason || overrideReason.trim().length < 3)) {
      setShowOverrideDialog(true);
      return;
    }

    setIsProcessing(true);
    setStatusMessage(null);
    try {
      await api.selectVendor(pr.id, selectedVendorId, isOverriding ? overrideReason : undefined);
      setShowOverrideDialog(false);
      setIsLocallyConfirmed(true);
      onRefresh();
      setStatusMessage('✓ Winning vendor confirmed. You can now grant final approval to generate the Purchase Order.');
    } catch (err: any) {
      setStatusMessage(`❌ ${err.message || 'Vendor selection failed.'}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleFinalApprovalAndPO = async () => {
    if (!isVendorConfirmed) {
      setStatusMessage('Please click "Confirm Selected Vendor" first before generating the Purchase Order.');
      return;
    }
    setIsProcessing(true);
    setStatusMessage(null);
    try {
      // 1. Final Approval
      await api.finalApproval(pr.id);
      // 2. Idempotent PO Generation
      const po = await api.generatePO(pr.id);
      setIsLocallyFinalized(true);
      onRefresh();
      setStatusMessage(`✅ Procurement Approved! Official Purchase Order ${po.po_number} generated.`);
    } catch (err: any) {
      setStatusMessage(`❌ ${err.message || 'Approval / PO Generation failed.'}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleAiExplainQuotes = async () => {
    setLoadingAi(true);
    try {
      const res = await api.aiExplainQuotation(pr.id);
      setAiExplanation(res.rationale);
    } catch (err) {
      setAiExplanation('Analytical comparison: Lowest unit price is balanced against committed delivery speed, lead time velocity, and verified historical reliability.');
    } finally {
      setLoadingAi(false);
    }
  };

  const winningVendorName = activeAnalysis.evaluations.find(e => e.vendor_id === selectedVendorId)?.vendor_name || 'Selected Vendor';

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
        <div>
          <div className="flex items-center space-x-2">
            <h3 className="text-base font-bold text-slate-900">
              Quotation Evaluation Matrix: {pr.reference_number}
            </h3>
            <span className="px-2 py-0.5 rounded text-xs font-extrabold bg-blue-100 text-blue-800 border border-blue-200">
              Multi-Factor Weighted V2
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Price (35%) • Delivery Date (20%) • Lead Time (15%) • Reliability (15%) • Quality (15%) — Lowest quote is never blindly awarded.
          </p>
          <p className="text-[10px] text-slate-400 mt-0.5 flex items-center space-x-1">
            <span className="px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 font-bold border border-blue-200">Post-RFQ Stage</span>
            <span>Evaluates actual supplier quotations received. Distinct from the pre-RFQ AI vendor recommendation.</span>
          </p>
        </div>

        <div className="flex items-center space-x-2 shrink-0">
          {isSupervisor && !isFinalized && (
            <button
              onClick={handleRefreshQuotes}
              disabled={refreshingQuotes}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold border border-slate-200 transition"
              title="Refresh quotes submitted by suppliers"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-slate-600 ${refreshingQuotes ? 'animate-spin' : ''}`} />
              <span>{refreshingQuotes ? 'Checking...' : 'Refresh Quotations'}</span>
            </button>
          )}

          <button
            onClick={handleAiExplainQuotes}
            disabled={loadingAi}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-purple-50 text-purple-700 hover:bg-purple-100 text-xs font-bold border border-purple-200 transition"
          >
            <Sparkles className="w-4 h-4 text-purple-600" />
            <span>{loadingAi ? 'Analyzing...' : 'AI Quotation Breakdown'}</span>
          </button>
        </div>
      </div>

      {statusMessage && (
        <div className={`p-3 rounded-xl text-xs flex items-center space-x-2 border ${
          statusMessage.startsWith('✓') || statusMessage.startsWith('✅')
            ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
            : statusMessage.startsWith('❌')
            ? 'bg-rose-50 border-rose-200 text-rose-800'
            : 'bg-blue-50 border-blue-200 text-blue-800'
        }`}>
          {statusMessage.startsWith('❌') ? (
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          ) : (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          )}
          <span>{statusMessage}</span>
        </div>
      )}

      {aiExplanation && (
        <div className="p-4 bg-purple-50/70 border border-purple-200 rounded-xl text-xs text-purple-900 leading-relaxed">
          <span className="font-bold block mb-1">AI Analytical Rationale:</span>
          {aiExplanation}
        </div>
      )}

      {/* Comparison Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-50 text-slate-600 font-bold border-b border-slate-200">
              <th className="py-3 px-3">Select</th>
              <th className="py-3 px-3">Rank & Supplier</th>
              <th className="py-3 px-3 text-right">Unit Price</th>
              <th className="py-3 px-3 text-right">Total Bid</th>
              <th className="py-3 px-3 text-right">Committed Delivery</th>
              <th className="py-3 px-3 text-right">Lead Time</th>
              <th className="py-3 px-3 text-right">Price Score</th>
              <th className="py-3 px-3 text-right">Delivery Score</th>
              <th className="py-3 px-3 text-right">Reliability</th>
              <th className="py-3 px-3 text-right">Weighted Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {activeAnalysis.evaluations.map((item) => {
              const isSelected = selectedVendorId === item.vendor_id;
              const isRec = item.is_recommended;

              return (
                <tr
                  key={item.vendor_id}
                  onClick={() => {
                    if (!isFinalized) {
                      setSelectedVendorId(item.vendor_id);
                      if (isLocallyConfirmed && item.vendor_id !== pr.selected_vendor_id) {
                        setIsLocallyConfirmed(false); // Reset confirmation if switching vendor
                      }
                    }
                  }}
                  className={`transition ${isFinalized ? 'cursor-default' : 'cursor-pointer'} ${
                    isSelected ? 'bg-blue-50/60 font-semibold' : isFinalized ? '' : 'hover:bg-slate-50'
                  }`}
                >
                  <td className="py-3.5 px-3">
                    <input
                      type="radio"
                      name="vendor_select"
                      checked={isSelected}
                      disabled={isFinalized}
                      onChange={() => {
                        if (!isFinalized) {
                          setSelectedVendorId(item.vendor_id);
                          if (isLocallyConfirmed && item.vendor_id !== pr.selected_vendor_id) {
                            setIsLocallyConfirmed(false);
                          }
                        }
                      }}
                      className="w-4 h-4 text-blue-600 focus:ring-blue-500 cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
                    />
                  </td>
                  <td className="py-3.5 px-3">
                    <div className="flex items-center space-x-2">
                      <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                        item.rank === 1 ? 'bg-amber-400 text-amber-950 font-black' : 'bg-slate-200 text-slate-700'
                      }`}>
                        #{item.rank}
                      </span>
                      <div>
                        <div className="font-bold text-slate-900 flex items-center space-x-1.5">
                          <span>{item.vendor_name}</span>
                          {isRec && (
                            <span className="px-1.5 py-0.2 rounded text-[10px] font-black bg-amber-100 text-amber-800 border border-amber-300">
                              ★ RECOMMENDED
                            </span>
                          )}
                        </div>
                        {item.vendor_badges && (
                          <div className="flex gap-1 mt-0.5">
                            {item.vendor_badges.map((b, idx) => (
                              <span key={idx} className="text-[9px] text-slate-500 font-medium">{b}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="py-3.5 px-3 text-right font-medium text-slate-800">${item.quoted_unit_price}</td>
                  <td className="py-3.5 px-3 text-right font-bold text-slate-950">${item.total_price.toLocaleString()}</td>
                  <td className="py-3.5 px-3 text-right">
                    {item.expected_delivery_date ? (
                      <span className="inline-flex items-center space-x-1 font-bold text-purple-900 bg-purple-50 px-2 py-0.5 rounded border border-purple-200">
                        <Calendar className="w-3 h-3 text-purple-600 shrink-0" />
                        <span>{item.expected_delivery_date}</span>
                      </span>
                    ) : (
                      <span className="text-slate-400 italic">Not specified</span>
                    )}
                  </td>
                  <td className="py-3.5 px-3 text-right text-slate-600">{item.lead_time_days} days</td>
                  <td className="py-3.5 px-3 text-right text-slate-600">{item.price_score}</td>
                  <td className="py-3.5 px-3 text-right text-slate-600">
                    {item.delivery_date_score !== undefined ? item.delivery_date_score : item.delivery_score}
                  </td>
                  <td className="py-3.5 px-3 text-right text-slate-600">{item.reliability_score}</td>
                  <td className="py-3.5 px-3 text-right font-black text-blue-700 text-sm">{item.final_weighted_score} / 100</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Human Override Warning Banner */}
      {isOverriding && (
        <div className="p-4 bg-amber-50 border border-amber-300 rounded-xl text-xs space-y-2">
          <div className="flex items-center space-x-2 font-bold text-amber-900">
            <ShieldAlert className="w-4 h-4 text-amber-600" />
            <span>Supervisor Override Detected: You are selecting a vendor different from the system recommendation.</span>
          </div>
          <p className="text-amber-800 text-[11px] leading-relaxed">
            Corporate governance requires a documented, audited justification for overriding the analytical recommendation.
          </p>
          <div className="space-y-1">
            <label className="font-bold text-amber-950 text-[11px]">Reason for Override (Mandatory):</label>
            <input
              type="text"
              value={overrideReason}
              onChange={e => setOverrideReason(e.target.value)}
              placeholder="e.g., Expedited lead time critical for server migration milestone..."
              className="w-full p-2 bg-white border border-amber-300 rounded-lg text-xs font-medium text-slate-800 focus:ring-2 focus:ring-amber-500"
            />
          </div>
        </div>
      )}

      {/* Decision Actions for Supervisor (Sequential Two-Step) */}
      {isSupervisor && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-4 border-t border-slate-100">
          <div className="text-xs text-slate-500">
            {isFinalized ? (
              <span className="font-bold text-emerald-800">Status: PO Generated (Locked)</span>
            ) : isVendorConfirmed ? (
              <div className="flex items-center space-x-1.5 text-emerald-800 font-bold">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Supplier Confirmed ({winningVendorName}). Ready for final approval.</span>
              </div>
            ) : (
              <span>Step 1: Select a supplier and click <strong>Confirm Selected Vendor</strong>.</span>
            )}
          </div>

          {isFinalized ? (
            <div className="flex items-center space-x-2 px-4 py-2 bg-emerald-100 border border-emerald-300 rounded-xl text-emerald-950 text-xs font-bold shadow-sm">
              <Lock className="w-4 h-4 text-emerald-700 shrink-0" />
              <span>Official Purchase Order Generated — Decision Locked</span>
            </div>
          ) : (
            <div className="flex items-center space-x-3">
              <button
                onClick={handleSelectVendor}
                disabled={isProcessing || !selectedVendorId || isVendorConfirmed}
                className={`px-4 py-2 text-xs font-bold rounded-xl transition flex items-center space-x-1.5 ${
                  isVendorConfirmed
                    ? 'bg-slate-100 text-slate-500 border border-slate-200 cursor-default'
                    : 'bg-purple-600 hover:bg-purple-700 text-white shadow-sm'
                }`}
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>{isProcessing ? 'Confirming...' : isVendorConfirmed ? 'Vendor Confirmed ✓' : 'Confirm Selected Vendor'}</span>
              </button>

              <button
                onClick={handleFinalApprovalAndPO}
                disabled={isProcessing || !isVendorConfirmed}
                className={`px-5 py-2.5 text-xs font-bold rounded-xl transition flex items-center space-x-2 ${
                  isVendorConfirmed
                    ? 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-md shadow-emerald-600/20 cursor-pointer animate-pulse'
                    : 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed shadow-none'
                }`}
                title={!isVendorConfirmed ? 'Please confirm winning supplier first' : 'Authorize procurement and generate PO'}
              >
                <FileCheck2 className="w-4 h-4" />
                <span>{isProcessing ? 'Generating...' : 'Final Approval & Generate PO'}</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* Override Dialog Modal */}
      {showOverrideDialog && (
        <div className="fixed inset-0 z-60 bg-slate-900/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl border border-slate-200 space-y-4">
            <div className="flex items-center space-x-2 text-amber-600 font-bold text-sm">
              <AlertTriangle className="w-5 h-5" />
              <span>Override Justification Required</span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              You selected a supplier other than the system recommendation ({activeAnalysis.recommended_vendor_name}). Please provide your rationale.
            </p>
            <textarea
              rows={3}
              value={overrideReason}
              onChange={e => setOverrideReason(e.target.value)}
              placeholder="Document required operational justification..."
              className="w-full p-2.5 border border-slate-300 rounded-xl text-xs"
            />
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => setShowOverrideDialog(false)}
                className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleSelectVendor}
                className="px-4 py-1.5 text-xs font-bold text-white bg-amber-600 hover:bg-amber-700 rounded-lg"
              >
                Submit Override & Confirm
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
