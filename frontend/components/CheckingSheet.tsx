'use client';

import React, { useState, useEffect } from 'react';
import { PurchaseRequest, RecommendationSnapshot, RAGVendorRecommendation, RFQ, QuotationAnalysis, Vendor } from '../lib/types';
import { api } from '../lib/api';
import { subscribeSyncEvent } from '../lib/sync';
import {
  X,
  XCircle,
  CheckCircle2,
  RotateCcw,
  Package,
  AlertTriangle,
  Award,
  DollarSign,
  Clock,
  Sparkles,
  ArrowRight,
  FileText,
  UserCheck,
  Trash2,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  BarChart2,
  ShieldAlert,
  TrendingUp,
  TrendingDown,
  Minus,
  Users,
  Bot,
  Star,
  Send,
  Calendar,
  Lock,
  FileCheck2,
  CheckSquare,
  Square
} from 'lucide-react';

interface CheckingSheetProps {
  pr: PurchaseRequest | null;
  isOpen: boolean;
  onClose: () => void;
  onRefresh: () => void;
  userRole: string;
  onOpenRevise?: (pr: PurchaseRequest) => void;
}

// ─── Helpers ────────────────────────────────────────────────────────────────

const confidenceBadge = (confidence?: string) => {
  const map: Record<string, string> = {
    HIGH: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    MEDIUM: 'bg-amber-100 text-amber-800 border-amber-300',
    LOW: 'bg-rose-100 text-rose-800 border-rose-300',
  };
  return `px-2 py-0.5 rounded text-[10px] font-bold border ${map[confidence ?? ''] ?? 'bg-slate-100 text-slate-600 border-slate-200'}`;
};

const statusBadge = (status?: string) => {
  const map: Record<string, string> = {
    RECOMMENDED: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    ACCEPTABLE: 'bg-blue-100 text-blue-800 border-blue-200',
    CAUTION: 'bg-amber-100 text-amber-800 border-amber-300',
  };
  return `px-2 py-0.5 rounded text-[10px] font-bold border ${map[status ?? ''] ?? 'bg-slate-100 text-slate-600 border-slate-200'}`;
};

const TrendIcon = ({ direction }: { direction?: string }) => {
  if (direction === 'IMPROVING') return <TrendingUp className="w-3.5 h-3.5 text-emerald-600" />;
  if (direction === 'DECLINING') return <TrendingDown className="w-3.5 h-3.5 text-rose-500" />;
  return <Minus className="w-3.5 h-3.5 text-slate-400" />;
};

const RatingBar = ({ label, value }: { label: string; value?: number }) => {
  if (value === undefined || value === null) return null;
  const pct = Math.min(Math.round((value / 10) * 100), 100);
  const color = pct >= 75 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-500' : 'bg-rose-500';
  return (
    <div className="space-y-0.5">
      <div className="flex justify-between text-[10px] text-slate-500">
        <span>{label}</span>
        <span className="font-bold text-slate-700">{value.toFixed(1)}/10</span>
      </div>
      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
};

// ─── Override reasons ────────────────────────────────────────────────────────
const OVERRIDE_REASONS = [
  'Better pricing and commercial proposal from selected supplier',
  'Committed delivery timeline meets urgent project milestone',
  'Existing master service agreement or certified framework',
  'Vendor-specific technical qualification or SLA warranty',
  'Prior positive performance and specialized logistics capability',
  'Strategic multi-vendor risk diversification policy',
  'Other (specify below)',
];

// ─── Compare Modal ───────────────────────────────────────────────────────────
const CompareModal: React.FC<{
  candidates: RAGVendorRecommendation[];
  onClose: () => void;
}> = ({ candidates, onClose }) => (
  <div className="fixed inset-0 z-70 bg-slate-900/70 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
    <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden">
      <div className="px-5 py-3.5 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Users className="w-4 h-4 text-purple-600" />
          <span className="text-sm font-bold text-slate-800">Compare All Pre-RFQ Vendor Candidates</span>
          <span className="text-xs text-slate-500">— Persisted AI Snapshot Intelligence</span>
        </div>
        <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200 rounded-lg transition">
          <X className="w-4 h-4" />
        </button>
      </div>
      <div className="overflow-auto flex-1 p-4">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="text-left px-3 py-2 font-bold text-slate-500 uppercase text-[10px] tracking-wider">Rank</th>
              <th className="text-left px-3 py-2 font-bold text-slate-500 uppercase text-[10px] tracking-wider">Vendor</th>
              <th className="text-left px-3 py-2 font-bold text-slate-500 uppercase text-[10px] tracking-wider">Status</th>
              <th className="text-left px-3 py-2 font-bold text-slate-500 uppercase text-[10px] tracking-wider">Confidence</th>
              <th className="text-left px-3 py-2 font-bold text-slate-500 uppercase text-[10px] tracking-wider">Quality</th>
              <th className="text-left px-3 py-2 font-bold text-slate-500 uppercase text-[10px] tracking-wider">Delivery</th>
              <th className="text-left px-3 py-2 font-bold text-slate-500 uppercase text-[10px] tracking-wider">Price</th>
              <th className="text-left px-3 py-2 font-bold text-slate-500 uppercase text-[10px] tracking-wider">Final Score ↓</th>
              <th className="text-left px-3 py-2 font-bold text-slate-500 uppercase text-[10px] tracking-wider">Historical</th>
              <th className="text-left px-3 py-2 font-bold text-slate-500 uppercase text-[10px] tracking-wider">Reviews</th>
              <th className="text-left px-3 py-2 font-bold text-slate-500 uppercase text-[10px] tracking-wider">Trend</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {candidates.map((c, i) => (
              <tr key={c.vendor_id} className={`hover:bg-slate-50 transition ${i === 0 ? 'bg-emerald-50/40' : ''}`}>
                <td className="px-3 py-2.5">
                  <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-extrabold
                    ${i === 0 ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-600'}`}>
                    {c.rank}
                  </span>
                </td>
                <td className="px-3 py-2.5">
                  <div className="font-bold text-slate-800">{c.vendor_name}</div>
                  {c.badges?.length > 0 && (
                    <div className="flex flex-wrap gap-0.5 mt-0.5">
                      {c.badges.slice(0, 2).map(b => (
                        <span key={b} className="px-1 py-0.5 bg-purple-100 text-purple-700 rounded text-[9px] font-semibold">{b.replace(/_/g, ' ')}</span>
                      ))}
                    </div>
                  )}
                </td>
                <td className="px-3 py-2.5">
                  <span className={statusBadge(c.recommendation_status)}>{c.recommendation_status}</span>
                </td>
                <td className="px-3 py-2.5">
                  <span className={confidenceBadge(c.evidence_confidence)}>{c.evidence_confidence ?? '—'}</span>
                </td>
                <td className="px-3 py-2.5 text-slate-700 font-medium">
                  {c.avg_quality_rating !== undefined ? `${c.avg_quality_rating.toFixed(1)}/10` : '—'}
                </td>
                <td className="px-3 py-2.5 text-slate-700 font-medium">
                  {c.avg_delivery_rating !== undefined ? `${c.avg_delivery_rating.toFixed(1)}/10` : '—'}
                </td>
                <td className="px-3 py-2.5 text-slate-700 font-medium">
                  {c.avg_price_rating !== undefined ? `${c.avg_price_rating.toFixed(1)}/10` : '—'}
                </td>
                <td className="px-3 py-2.5">
                  <span className="font-extrabold text-purple-800 bg-purple-100 px-1.5 py-0.5 rounded">
                    {(c.final_recommendation_score ?? 0).toFixed(1)}
                  </span>
                </td>
                <td className="px-3 py-2.5 text-slate-500 text-[10px]">
                  {c.analytical_score.toFixed(1)}
                </td>
                <td className="px-3 py-2.5 text-slate-600">{c.review_count}</td>
                <td className="px-3 py-2.5">
                  <div className="flex items-center space-x-1">
                    <TrendIcon direction={c.trend_direction} />
                    <span className="text-slate-500 text-[10px]">{c.trend_direction ?? '—'}</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Key Strengths & Risks per candidate */}
        <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-3">
          {candidates.slice(0, 4).map(c => (
            <div key={c.vendor_id} className={`p-3 rounded-xl border text-xs space-y-2 ${c.rank === 1 ? 'border-emerald-200 bg-emerald-50/30' : 'border-slate-200 bg-white'}`}>
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-800">#{c.rank} {c.vendor_name}</span>
                <span className={statusBadge(c.recommendation_status)}>{c.recommendation_status}</span>
              </div>
              {c.key_strengths?.length > 0 && (
                <div>
                  <span className="text-emerald-700 font-semibold block mb-0.5">Strengths</span>
                  {c.key_strengths.slice(0, 2).map((s, i) => (
                    <div key={i} className="text-slate-600 flex items-start space-x-1">
                      <span className="text-emerald-500 mt-0.5">✓</span><span>{s}</span>
                    </div>
                  ))}
                </div>
              )}
              {c.potential_risks?.length > 0 && (
                <div>
                  <span className="text-amber-700 font-semibold block mb-0.5">Risks</span>
                  {c.potential_risks.slice(0, 2).map((r, i) => (
                    <div key={i} className="text-slate-600 flex items-start space-x-1">
                      <span className="text-amber-500 mt-0.5">⚠</span><span>{r}</span>
                    </div>
                  ))}
                </div>
              )}
              {c.reasoning_summary && (
                <p className="text-slate-500 italic leading-relaxed line-clamp-2">{c.reasoning_summary}</p>
              )}
            </div>
          ))}
        </div>
      </div>
      <div className="px-5 py-3 border-t border-slate-200 bg-slate-50 flex justify-end">
        <button onClick={onClose} className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-200 rounded-xl transition">
          Close Comparison
        </button>
      </div>
    </div>
  </div>
);

// ─── Main Component ──────────────────────────────────────────────────────────
export const CheckingSheet: React.FC<CheckingSheetProps> = ({
  pr,
  isOpen,
  onClose,
  onRefresh,
  userRole,
  onOpenRevise
}) => {
  const [returnReason, setReturnReason] = useState('');
  const [showReturnModal, setShowReturnModal] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // ─── Recommendation Snapshot State ────────────────────────────────────────
  const [snapshot, setSnapshot] = useState<RecommendationSnapshot | null>(null);
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  const [snapshotError, setSnapshotError] = useState<string | null>(null);
  const [showCompareModal, setShowCompareModal] = useState(false);
  const [refreshingSnapshot, setRefreshingSnapshot] = useState(false);

  // ─── Multi-Vendor RFQ Selection State (Stage 1 / 2) ────────────────────────
  const [selectedVendorIds, setSelectedVendorIds] = useState<string[]>([]);
  const [rfqDeadline, setRfqDeadline] = useState<string>(() => {
    const d = new Date();
    d.setDate(d.getDate() + 7);
    return d.toISOString().split('T')[0];
  });
  const [availableVendors, setAvailableVendors] = useState<Vendor[]>([]);

  // ─── Post-RFQ Quotations & Evaluation State (Stage 3 / 4) ──────────────────
  const [prRfqs, setPrRfqs] = useState<RFQ[]>([]);
  const [quotationAnalysis, setQuotationAnalysis] = useState<QuotationAnalysis | null>(null);
  const [loadingQuotations, setLoadingQuotations] = useState(false);
  const [selectedWinningVendorId, setSelectedWinningVendorId] = useState<string>('');
  const [showPostRfqOverrideModal, setShowPostRfqOverrideModal] = useState(false);
  const [postRfqOverrideReason, setPostRfqOverrideReason] = useState('');
  const [postRfqOverrideDetail, setPostRfqOverrideDetail] = useState('');
  const [refreshingQuotes, setRefreshingQuotes] = useState(false);

  // Confirmed vendor tracking
  const [isVendorConfirmed, setIsVendorConfirmed] = useState(false);
  const [confirmedVendorId, setConfirmedVendorId] = useState<string>('');
  const [localStatus, setLocalStatus] = useState<string>('');

  const isSupervisor = userRole === 'SUPERVISOR' || userRole === 'ADMIN';

  // Workflow Stages
  const currentStatus = localStatus || pr?.status || '';
  const isPreRfqStage = ['SUBMITTED', 'UNDER_REVIEW', 'DRAFT', 'REVISION_REQUIRED', 'APPROVED_FOR_RFQ'].includes(currentStatus);
  const isPostRfqStage = [
    'RFQS_ISSUED',
    'AWAITING_QUOTATIONS',
    'QUOTATIONS_READY',
    'RFQ_ISSUED',
    'QUOTATION_RECEIVED',
    'VENDOR_SELECTION_PENDING',
    'FINAL_APPROVAL_PENDING',
    'APPROVED',
    'PO_GENERATED',
    'COMPLETED'
  ].includes(currentStatus);

  const isLockedPO = ['APPROVED', 'PO_GENERATED', 'COMPLETED'].includes(currentStatus);

  // Sync state when PR changes
  useEffect(() => {
    if (!isOpen || !pr) return;
    setLocalStatus(pr.status);
    const confirmed = pr.status === 'FINAL_APPROVAL_PENDING' || pr.status === 'APPROVED' || pr.status === 'PO_GENERATED' || pr.status === 'COMPLETED';
    setIsVendorConfirmed(confirmed);
    if (pr.selected_vendor_id) {
      setConfirmedVendorId(pr.selected_vendor_id);
    }
  }, [isOpen, pr?.id, pr?.status]);

  // Load snapshot & vendors & quotations when the sheet opens
  useEffect(() => {
    if (!isOpen || !pr) return;
    setSnapshot(null);
    setSnapshotError(null);
    setSnapshotLoading(true);
    setActionError(null);
    setQuotationAnalysis(null);
    setPrRfqs([]);
    setSelectedWinningVendorId('');

    // 1. Load pre-RFQ recommendation snapshot
    api.getRecommendationSnapshot(pr.id)
      .then(snap => {
        setSnapshot(snap);
        const initialSelections: string[] = [];
        if (snap.recommended_vendor_id) {
          initialSelections.push(snap.recommended_vendor_id);
        }
        if (pr.selected_vendor_id && !initialSelections.includes(pr.selected_vendor_id)) {
          initialSelections.push(pr.selected_vendor_id);
        }
        if (snap.all_candidates?.[1] && initialSelections.length < 3 && !initialSelections.includes(snap.all_candidates[1].vendor_id)) {
          initialSelections.push(snap.all_candidates[1].vendor_id);
        }
        setSelectedVendorIds(initialSelections);
      })
      .catch(err => {
        const msg = (err.message || '').toLowerCase();
        if (
          msg.includes('404') ||
          msg.includes('no ai recommendation') ||
          msg.includes('not found') ||
          msg.includes('no recommendation')
        ) {
          setSnapshotError('no_snapshot');
        } else {
          setSnapshotError(err.message || 'Failed to load AI recommendation snapshot.');
        }
        if (pr.selected_vendor_id) {
          setSelectedVendorIds([pr.selected_vendor_id]);
        }
      })
      .finally(() => setSnapshotLoading(false));

    // 2. Load all active vendors for manual selection fallback
    api.getVendors()
      .then(vList => setAvailableVendors(vList))
      .catch(err => console.error('Failed to load vendors:', err));

    // 3. If post-RFQ stage, load issued RFQs and Quotation Analysis
    if (isPostRfqStage) {
      loadPostRfqData();
    } else {
      setQuotationAnalysis(null);
      setPrRfqs([]);
      setSelectedWinningVendorId('');
    }
  }, [isOpen, pr?.id, pr?.status]);

  const loadPostRfqData = async () => {
    if (!pr) return;
    setLoadingQuotations(true);
    try {
      const [allRfqs, qa] = await Promise.all([
        api.getRFQs(),
        api.getQuotationAnalysis(pr.id).catch(() => null)
      ]);
      const myRfqs = allRfqs.filter(r => r.purchase_request_id === pr.id);
      setPrRfqs(myRfqs);
      if (qa && qa.purchase_request_id === pr.id && qa.evaluations && qa.evaluations.length > 0) {
        setQuotationAnalysis(qa);
        const initialPick = qa.recommended_vendor_id || qa.evaluations[0].vendor_id;
        setSelectedWinningVendorId(prev => prev || initialPick);
      } else {
        setQuotationAnalysis(null);
        setSelectedWinningVendorId('');
      }
    } catch (err) {
      console.error('Failed to load RFQs / Quotation Analysis:', err);
      setQuotationAnalysis(null);
      setSelectedWinningVendorId('');
    } finally {
      setLoadingQuotations(false);
    }
  };

  // Real-time synchronization for live quotations and status
  useEffect(() => {
    if (!isOpen || !pr) return;
    const unsubscribe = subscribeSyncEvent((payload) => {
      if (
        payload.type === 'QUOTATION_SUBMITTED' ||
        payload.type === 'RFQS_ISSUED' ||
        payload.type === 'VENDOR_SELECTED' ||
        payload.type === 'PO_GENERATED' ||
        payload.type === 'PR_UPDATED' ||
        payload.type === 'GENERAL_REFRESH'
      ) {
        if (isPostRfqStage) {
          loadPostRfqData();
        }
      }
    });

    return () => {
      unsubscribe();
    };
  }, [isOpen, pr?.id, isPostRfqStage]);

  if (!isOpen || !pr) return null;

  // ─── Vendor Selection Checkbox Toggle ──────────────────────────────────────
  const toggleVendorSelection = (vendorId: string) => {
    setSelectedVendorIds(prev => {
      if (prev.includes(vendorId)) {
        return prev.filter(id => id !== vendorId);
      } else {
        if (prev.length >= 3) {
          setActionError('A maximum of 3 vendors can be invited for competitive quotation bidding.');
          return prev;
        }
        setActionError(null);
        return [...prev, vendorId];
      }
    });
  };

  // ─── Stage 1 / 2: Issue RFQs Handler ───────────────────────────────────────
  const handleIssueRFQs = async () => {
    if (selectedVendorIds.length === 0) {
      setActionError('Please select at least 1 vendor to issue Requests for Quotation (RFQs).');
      return;
    }
    if (selectedVendorIds.length > 3) {
      setActionError('Maximum 3 vendors can be invited.');
      return;
    }

    setActionLoading(true);
    setActionError(null);
    try {
      await api.issueRFQs(pr.id, selectedVendorIds, rfqDeadline ? `${rfqDeadline}T23:59:59` : undefined);
      setLocalStatus('AWAITING_QUOTATIONS');
      onRefresh();
      await loadPostRfqData();
    } catch (err: any) {
      setActionError(err.message || 'Failed to issue RFQs.');
    } finally {
      setActionLoading(false);
    }
  };

  // ─── Stage 3: Refresh Quotations Handler (NO SIMULATE) ─────────────────────
  const handleRefreshQuotations = async () => {
    setRefreshingQuotes(true);
    setActionError(null);
    try {
      await loadPostRfqData();
      onRefresh();
    } catch (err: any) {
      setActionError(err.message || 'Failed to refresh quotations.');
    } finally {
      setRefreshingQuotes(false);
    }
  };

  // ─── Stage 3: Confirm Winning Vendor ──────────────────────────────────────
  const handleSelectWinningVendor = async () => {
    if (!selectedWinningVendorId) {
      setActionError('Please select a supplier from the quotation comparison table.');
      return;
    }

    const recommendedQuoteVendor = quotationAnalysis?.recommended_vendor_id;
    const isQuoteOverride = Boolean(
      recommendedQuoteVendor &&
      selectedWinningVendorId &&
      String(selectedWinningVendorId).toLowerCase() !== String(recommendedQuoteVendor).toLowerCase()
    );

    if (isQuoteOverride && (!postRfqOverrideReason || postRfqOverrideReason.trim().length < 3)) {
      setShowPostRfqOverrideModal(true);
      return;
    }

    setActionLoading(true);
    setActionError(null);
    try {
      await api.selectVendor(
        pr.id,
        selectedWinningVendorId,
        isQuoteOverride ? (postRfqOverrideReason === 'Other (specify below)' ? postRfqOverrideDetail : postRfqOverrideReason) : undefined
      );
      setShowPostRfqOverrideModal(false);
      setIsVendorConfirmed(true);
      setConfirmedVendorId(selectedWinningVendorId);
      setLocalStatus('FINAL_APPROVAL_PENDING');
      onRefresh();
      await loadPostRfqData();
    } catch (err: any) {
      setActionError(err.message || 'Vendor selection failed.');
    } finally {
      setActionLoading(false);
    }
  };

  // ─── Stage 4: Final Approval & PO Generation ──────────────────────────────
  const handleFinalApprovalAndPO = async () => {
    if (!isVendorConfirmed) {
      setActionError('Please confirm the winning supplier before authorizing the purchase order.');
      return;
    }

    setActionLoading(true);
    setActionError(null);
    try {
      // 1. Final Approval
      await api.finalApproval(pr.id);
      // 2. Generate Official PO
      await api.generatePO(pr.id);
      setLocalStatus('PO_GENERATED');
      onRefresh();
      onClose();
    } catch (err: any) {
      setActionError(err.message || 'Final approval & PO generation failed.');
    } finally {
      setActionLoading(false);
    }
  };

  // ─── Standard Governance Handlers ──────────────────────────────────────────
  const handleReturnForRevision = async () => {
    if (!returnReason || returnReason.trim().length < 3) {
      setActionError('Returning a PR requires a mandatory, substantive reason.');
      return;
    }

    setActionLoading(true);
    setActionError(null);
    try {
      await api.returnPR(pr.id, returnReason);
      setShowReturnModal(false);
      onRefresh();
      onClose();
    } catch (err: any) {
      setActionError(err.message || 'Failed to return PR.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRejectPR = async () => {
    if (!rejectReason || rejectReason.trim().length < 3) {
      setActionError('Rejecting a PR requires a mandatory, substantive reason.');
      return;
    }

    setActionLoading(true);
    setActionError(null);
    try {
      await api.rejectPR(pr.id, rejectReason);
      setShowRejectModal(false);
      onRefresh();
      onClose();
    } catch (err: any) {
      setActionError(err.message || 'Failed to reject PR.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeletePR = async () => {
    if (!confirm(`Are you sure you want to delete purchase request ${pr.reference_number}? This will permanently remove it from the system.`)) {
      return;
    }
    setActionLoading(true);
    try {
      await api.deletePR(pr.id);
      onRefresh();
      onClose();
    } catch (err: any) {
      setActionError(err.message || 'Failed to delete request.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRefreshSnapshot = async () => {
    setRefreshingSnapshot(true);
    setSnapshotError(null);
    try {
      const fresh = await api.refreshRecommendationSnapshot(pr.id);
      setSnapshot(fresh);
    } catch (err: any) {
      setSnapshotError(err.message || 'Failed to refresh recommendation. Please try again.');
    } finally {
      setRefreshingSnapshot(false);
    }
  };

  // Build candidate pool for RFQ invitation selection
  const candidatePool: Array<{
    vendor_id: string;
    vendor_name: string;
    badges: string[];
    final_score?: number;
    analytical_score?: number;
    status?: string;
    confidence?: string;
    isSnapshotCandidate: boolean;
  }> = [];

  if (snapshot?.all_candidates && snapshot.all_candidates.length > 0) {
    snapshot.all_candidates.forEach(c => {
      candidatePool.push({
        vendor_id: c.vendor_id,
        vendor_name: c.vendor_name,
        badges: c.badges || [],
        final_score: c.final_recommendation_score,
        analytical_score: c.analytical_score,
        status: c.recommendation_status,
        confidence: c.evidence_confidence,
        isSnapshotCandidate: true,
      });
    });
  }

  availableVendors.forEach(v => {
    if (!candidatePool.some(c => c.vendor_id === v.id)) {
      candidatePool.push({
        vendor_id: v.id,
        vendor_name: v.name,
        badges: v.badges || [],
        isSnapshotCandidate: false,
      });
    }
  });

  const recommendedQuoteVendor = quotationAnalysis?.recommended_vendor_id;
  const isPostRfqOverriding = Boolean(
    recommendedQuoteVendor &&
    selectedWinningVendorId &&
    String(selectedWinningVendorId).toLowerCase() !== String(recommendedQuoteVendor).toLowerCase()
  );

  const winningVendorName = quotationAnalysis?.evaluations.find(
    e => e.vendor_id === (confirmedVendorId || selectedWinningVendorId)
  )?.vendor_name || 'Selected Supplier';

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-5xl max-h-[92vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-100 text-blue-700 rounded-lg">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-base font-bold text-slate-900">Supervisor Checking Sheet: {pr.reference_number}</h2>
                <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-blue-100 text-blue-800 border border-blue-200">
                  {currentStatus}
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Department: <span className="font-semibold text-slate-700">{pr.department_name}</span> • Requester: <span className="font-semibold text-slate-700">{pr.requester_name}</span>
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200 rounded-lg transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Sheet Content */}
        <div className="p-6 space-y-6 overflow-y-auto flex-1">
          {actionError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
              <span>{actionError}</span>
            </div>
          )}

          {currentStatus === 'REVISION_REQUIRED' && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs space-y-2.5 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="font-bold text-amber-900 flex items-center space-x-2 text-sm">
                  <RotateCcw className="w-4 h-4 text-amber-600" />
                  <span>This Purchase Request is returned for revision</span>
                </span>
                {onOpenRevise && (
                  <button
                    onClick={() => {
                      onClose();
                      onOpenRevise(pr);
                    }}
                    className="px-3.5 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-bold transition flex items-center space-x-1.5 shadow-sm hover:shadow"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Open Revision Form</span>
                  </button>
                )}
              </div>
              {pr.reviews && pr.reviews.filter(r => r.decision === 'RETURNED' || r.decision === 'RETURNED_FOR_REVISION').length > 0 && (
                <div className="bg-white/90 p-3 rounded-lg border border-amber-200 text-amber-950 font-medium italic">
                  <span className="text-[10px] text-amber-700 font-bold block not-italic mb-0.5">
                    Supervisor Feedback ({pr.reviews.filter(r => r.decision === 'RETURNED' || r.decision === 'RETURNED_FOR_REVISION').slice(-1)[0].supervisor_name || 'Supervisor'}):
                  </span>
                  &ldquo;{pr.reviews.filter(r => r.decision === 'RETURNED' || r.decision === 'RETURNED_FOR_REVISION').slice(-1)[0].reason}&rdquo;
                </div>
              )}
            </div>
          )}

          {/* Grid Layout: Order Context & Inventory */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            {/* 1. Request Details */}
            <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm space-y-3">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400">Order Context</div>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Procurement Item</span>
                  <span className="font-bold text-slate-900">{pr.item_name}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Requested Quantity</span>
                  <span className="font-bold text-slate-900">{pr.quantity} {pr.item_unit}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Employee Preferred Supplier</span>
                  <span className="font-bold text-slate-900">{pr.selected_vendor_name || 'None Specified'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Submission Date</span>
                  <span className="font-medium text-slate-700">{new Date(pr.created_at).toLocaleDateString()}</span>
                </div>
                {pr.notes && (
                  <div className="pt-1">
                    <span className="text-slate-500 block mb-0.5">Requester Justification:</span>
                    <p className="p-2 bg-slate-50 rounded text-slate-700 italic border border-slate-100">{pr.notes}</p>
                  </div>
                )}
              </div>
            </div>

            {/* 2. Deterministic Inventory Intelligence */}
            <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
                  <Package className="w-3.5 h-3.5 text-blue-600" />
                  <span>Inventory Reserve Analysis</span>
                </div>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                  pr.inventory_analysis?.coverage_status === 'SUFFICIENT'
                    ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                    : 'bg-amber-100 text-amber-800 border-amber-300'
                }`}>
                  {pr.inventory_analysis?.coverage_status}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-2 text-center text-xs">
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                  <div className="text-[10px] text-slate-400 uppercase font-bold">In Stock</div>
                  <div className="font-bold text-slate-900 text-sm">{pr.inventory_analysis?.available_quantity ?? 0} {pr.item_unit || 'units'}</div>
                </div>
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                  <div className="text-[10px] text-slate-400 uppercase font-bold">Requested</div>
                  <div className="font-bold text-slate-900 text-sm">{pr.inventory_analysis?.requested_quantity ?? pr.quantity} {pr.item_unit || 'units'}</div>
                </div>
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                  <div className="text-[10px] text-slate-400 uppercase font-bold">Shortage</div>
                  <div className={`font-bold text-sm ${(pr.inventory_analysis?.shortage_quantity ?? 0) > 0 ? 'text-amber-700' : 'text-emerald-700'}`}>
                    {(pr.inventory_analysis?.shortage_quantity ?? 0) > 0 ? `${pr.inventory_analysis?.shortage_quantity} ${pr.item_unit || 'units'}` : '0 (None)'}
                  </div>
                </div>
              </div>

              {/* Contextual Inventory Reserve Result */}
              <div className={`p-3 rounded-lg border text-xs space-y-1 ${
                pr.inventory_analysis?.coverage_status === 'SUFFICIENT'
                  ? 'bg-emerald-50/70 border-emerald-200 text-emerald-900'
                  : 'bg-amber-50/70 border-amber-200 text-amber-900'
              }`}>
                <div className="font-bold text-[11px] flex items-center space-x-1.5">
                  <Package className="w-3.5 h-3.5" />
                  <span>
                    {pr.inventory_analysis?.coverage_status === 'SUFFICIENT'
                      ? 'Inventory Available — Procurement Still Available'
                      : 'Insufficient Inventory — External Procurement Recommended'}
                  </span>
                </div>
                <p className="text-[10px] text-slate-600 leading-relaxed">
                  {pr.inventory_analysis?.coverage_status === 'SUFFICIENT'
                    ? `Sufficient internal inventory (${pr.inventory_analysis?.available_quantity ?? 0} ${pr.item_unit || 'units'}) is available in warehouse reserves. You may utilize internal stock or continue with external procurement if separate project allocation is needed.`
                    : `Current warehouse stock (${pr.inventory_analysis?.available_quantity ?? 0} ${pr.item_unit || 'units'}) cannot satisfy this request. A shortage of ${pr.inventory_analysis?.shortage_quantity ?? 0} ${pr.item_unit || 'units'} exists. External supplier procurement is recommended.`}
                </p>
              </div>
            </div>

          </div>

          {/* Duplicate Detection Banner */}
          {pr.duplicate_matches && pr.duplicate_matches.length > 0 && (
            <div className="p-4 rounded-xl border border-amber-300 bg-amber-50/80 space-y-2">
              <div className="flex items-center space-x-2 text-amber-900 font-bold text-xs">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                <span>Deterministic Duplicate Warning: {pr.duplicate_matches.length} similar active request(s) found in {pr.department_name}</span>
              </div>
              <div className="space-y-1.5">
                {pr.duplicate_matches.map(m => (
                  <div key={m.id} className="p-2.5 bg-white rounded-lg border border-amber-200 text-xs flex items-center justify-between">
                    <div>
                      <span className="font-bold text-slate-900">{m.reference_number}</span> — {m.existing_quantity} {pr.item_unit} ({m.status})
                    </div>
                    <span className="text-[11px] font-semibold text-amber-800 bg-amber-100 px-2 py-0.5 rounded">
                      {m.difference_percentage}% difference
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════
              3. AI + RAG Pre-RFQ Vendor Intelligence Snapshot
              ═══════════════════════════════════════════════════════════════ */}
          <div className="p-4 rounded-xl border border-purple-200 bg-gradient-to-br from-white to-purple-50/30 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className="p-1.5 bg-purple-100 rounded-lg">
                  <Bot className="w-4 h-4 text-purple-700" />
                </div>
                <div>
                  <div className="text-xs font-bold uppercase tracking-wider text-slate-800">Pre-RFQ AI Intelligence Snapshot</div>
                  <div className="text-[10px] text-slate-400">Determines which vendors to invite • Persisted at submission</div>
                </div>
              </div>
              <button
                onClick={handleRefreshSnapshot}
                disabled={refreshingSnapshot || snapshotLoading}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold transition shadow-sm shadow-purple-600/20 disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${refreshingSnapshot ? 'animate-spin' : ''}`} />
                <span>{refreshingSnapshot ? 'Refreshing...' : 'Refresh AI Recommendation'}</span>
              </button>
            </div>

            {(snapshotLoading || refreshingSnapshot) && (
              <div className="flex items-center space-x-2 text-xs text-slate-500 py-4 justify-center">
                <RefreshCw className="w-4 h-4 text-purple-500 animate-spin" />
                <span>{refreshingSnapshot ? 'Re-running RAG+LLM pipeline...' : 'Loading recommendation snapshot...'}</span>
              </div>
            )}

            {!snapshotLoading && !refreshingSnapshot && snapshotError && (
              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-600 flex items-center justify-between">
                <span>No pre-submission AI snapshot found. Click Refresh AI Recommendation to generate one.</span>
                <button
                  type="button"
                  onClick={handleRefreshSnapshot}
                  className="px-3 py-1 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-bold shrink-0 transition"
                >
                  Generate Now
                </button>
              </div>
            )}

            {!snapshotLoading && !refreshingSnapshot && snapshot && (
              <div className="space-y-3">
                {snapshot.is_stale && (
                  <div className="flex items-start space-x-2 p-3 bg-amber-50 rounded-lg border border-amber-300 text-xs">
                    <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <span className="font-bold text-amber-800">Recommendation snapshot may be outdated</span>
                      <p className="text-amber-700 mt-0.5">The item or quantity changed since this was generated. Consider clicking Refresh AI Recommendation.</p>
                    </div>
                  </div>
                )}

                <div className="flex items-center flex-wrap gap-2 text-[10px] text-slate-400">
                  <span className={confidenceBadge(snapshot.evidence_confidence)}>
                    {snapshot.evidence_confidence ?? '?'} CONFIDENCE
                  </span>
                  <span className="px-2 py-0.5 rounded border text-[10px] font-bold border-slate-200 bg-slate-50 text-slate-500">
                    {snapshot.source === 'LLM_RAG' ? '🤖 LLM + RAG' : '📊 Analytical Fallback'}
                  </span>
                  <span className="px-2 py-0.5 rounded border text-[10px] font-bold border-slate-200 bg-slate-50 text-slate-500">
                    v{snapshot.version} • {snapshot.triggered_by === 'SUPERVISOR_REFRESH' ? 'Supervisor Refresh' : 'Employee Generated'}
                  </span>
                </div>

                <div className="p-3 rounded-xl border-2 border-emerald-300 bg-emerald-50/30 text-xs">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <Star className="w-4 h-4 text-emerald-600" />
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase font-bold">Top Recommended Supplier Candidate</div>
                        <div className="font-extrabold text-slate-900 text-sm">{snapshot.recommended_vendor_name ?? '—'}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs font-extrabold text-purple-800 bg-purple-100 px-2.5 py-0.5 rounded-full tabular-nums">
                        {(snapshot.final_recommendation_score ?? 0).toFixed(1)} / 100
                      </div>
                      <div className="text-[9px] text-slate-400 mt-0.5 text-right">
                        Historical: {snapshot.analytical_score.toFixed(1)}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2 mt-2">
                    <div className="p-2 bg-white/70 rounded-lg">
                      <div className="text-[10px] text-slate-400 font-bold uppercase mb-1">Quality</div>
                      <RatingBar label="" value={snapshot.avg_quality_rating} />
                    </div>
                    <div className="p-2 bg-white/70 rounded-lg">
                      <div className="text-[10px] text-slate-400 font-bold uppercase mb-1">Delivery</div>
                      <RatingBar label="" value={snapshot.avg_delivery_rating} />
                    </div>
                    <div className="p-2 bg-white/70 rounded-lg">
                      <div className="text-[10px] text-slate-400 font-bold uppercase mb-1">Price</div>
                      <RatingBar label="" value={snapshot.avg_price_rating} />
                    </div>
                  </div>
                </div>

                {snapshot.all_candidates?.length > 1 && (
                  <button
                    onClick={() => setShowCompareModal(true)}
                    className="flex items-center space-x-1.5 px-3 py-2 text-xs font-bold text-purple-700 border border-purple-200 bg-purple-50 hover:bg-purple-100 rounded-xl transition"
                  >
                    <Users className="w-3.5 h-3.5" />
                    <span>Compare All {snapshot.all_candidates.length} Vendor Candidates</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                )}
              </div>
            )}
          </div>

          {/* ═══════════════════════════════════════════════════════════════
              4. PRE-RFQ STAGE: Multi-Vendor RFQ Invitation Selector
              ═══════════════════════════════════════════════════════════════ */}
          {isPreRfqStage && (
            <div className="p-5 rounded-2xl border-2 border-blue-200 bg-white shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                    <Send className="w-4 h-4 text-blue-600" />
                    <span>Select Vendors to Invite for Quotations (1–3 Suppliers)</span>
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Curate competitive suppliers who will receive formal RFQs for this purchase request.
                  </p>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold px-2.5 py-1 bg-blue-50 text-blue-800 rounded-lg border border-blue-200">
                    {selectedVendorIds.length} / 3 Selected
                  </span>
                </div>
              </div>

              {/* Vendor Checklist */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {candidatePool.map((candidate) => {
                  const isChecked = selectedVendorIds.includes(candidate.vendor_id);
                  const isAiTopPick = snapshot?.recommended_vendor_id === candidate.vendor_id;
                  const isEmployeePref = pr.selected_vendor_id === candidate.vendor_id;

                  return (
                    <div
                      key={candidate.vendor_id}
                      onClick={() => toggleVendorSelection(candidate.vendor_id)}
                      className={`p-3.5 rounded-xl border-2 transition cursor-pointer flex items-start space-x-3 ${
                        isChecked
                          ? 'border-blue-500 bg-blue-50/40 shadow-sm'
                          : 'border-slate-200 bg-white hover:border-slate-300'
                      }`}
                    >
                      <div className="pt-0.5">
                        {isChecked ? (
                          <CheckSquare className="w-4 h-4 text-blue-600" />
                        ) : (
                          <Square className="w-4 h-4 text-slate-300" />
                        )}
                      </div>
                      <div className="flex-1 space-y-1 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-slate-900">{candidate.vendor_name}</span>
                          {candidate.final_score !== undefined && (
                            <span className="font-bold text-purple-700 bg-purple-100 px-1.5 py-0.2 rounded text-[10px]">
                              Score: {candidate.final_score.toFixed(1)}
                            </span>
                          )}
                        </div>

                        <div className="flex flex-wrap gap-1 items-center">
                          {isAiTopPick && (
                            <span className="px-1.5 py-0.2 rounded text-[9px] font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-300">
                              ★ AI TOP PICK
                            </span>
                          )}
                          {isEmployeePref && (
                            <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-blue-100 text-blue-800 border border-blue-300">
                              Employee Preference
                            </span>
                          )}
                          {candidate.status && (
                            <span className={statusBadge(candidate.status)}>
                              {candidate.status}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Deadline Picker */}
              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                <div className="flex items-center space-x-2">
                  <Calendar className="w-4 h-4 text-purple-600" />
                  <div>
                    <span className="font-bold text-slate-800 block">RFQ Quotation Submission Deadline</span>
                    <span className="text-[11px] text-slate-500">Suppliers cannot submit bids after this date.</span>
                  </div>
                </div>
                <input
                  type="date"
                  value={rfqDeadline}
                  onChange={e => setRfqDeadline(e.target.value)}
                  className="p-2 border border-slate-300 rounded-lg text-xs font-bold text-slate-900 focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════
              5. POST-RFQ STAGE: Quotation Tracking & Bid Evaluation Matrix
              ═══════════════════════════════════════════════════════════════ */}
          {isPostRfqStage && (
            <div className="space-y-4">
              {/* Issued RFQ Status Cards */}
              <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <div className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center space-x-1.5">
                    <Clock className="w-3.5 h-3.5 text-blue-600" />
                    <span>Competitive RFQ Dispatch Status ({prRfqs.length} Invited)</span>
                  </div>
                  {!isLockedPO && (
                    <button
                      onClick={handleRefreshQuotations}
                      disabled={refreshingQuotes}
                      className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 rounded-lg text-xs font-bold transition flex items-center space-x-1.5"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 text-slate-600 ${refreshingQuotes ? 'animate-spin' : ''}`} />
                      <span>{refreshingQuotes ? 'Checking for Quotes...' : 'Refresh Quotations'}</span>
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 text-xs">
                  {prRfqs.map(rfq => (
                    <div key={rfq.id} className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900">{rfq.vendor_name}</span>
                        <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold border ${
                          rfq.has_quotation
                            ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                            : 'bg-blue-100 text-blue-800 border-blue-200'
                        }`}>
                          {rfq.has_quotation ? 'Quote Received ✓' : 'Awaiting Quote'}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-500">Ref: {rfq.reference_number}</div>
                      {rfq.due_at && (
                        <div className="text-[10px] text-slate-600">
                          Due: {new Date(rfq.due_at).toLocaleDateString()}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Quotation Comparison Matrix (if available) */}
              {quotationAnalysis && quotationAnalysis.purchase_request_id === pr.id && quotationAnalysis.evaluations && quotationAnalysis.evaluations.length > 0 ? (
                <div className="p-5 rounded-2xl border-2 border-purple-200 bg-white shadow-sm space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                    <div>
                      <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                        <Award className="w-4 h-4 text-purple-600" />
                        <span>Analytical Quotation Evaluation (Post-RFQ Actual Bids)</span>
                      </h3>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Price (35%) • Delivery Date (20%) • Lead Time (15%) • Reliability (15%) • Quality (15%)
                      </p>
                    </div>
                    {isLockedPO ? (
                      <span className="px-3 py-1 bg-emerald-100 text-emerald-950 border border-emerald-300 rounded-xl text-xs font-bold flex items-center space-x-1.5">
                        <Lock className="w-3.5 h-3.5 text-emerald-700" />
                        <span>Decision Finalized & PO Generated</span>
                      </span>
                    ) : isVendorConfirmed ? (
                      <span className="px-3 py-1 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-xl text-xs font-bold flex items-center space-x-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        <span>Supplier Confirmed: {winningVendorName}</span>
                      </span>
                    ) : (
                      <span className="text-xs font-semibold text-purple-700 bg-purple-50 px-2.5 py-1 rounded-lg border border-purple-200">
                        Step 1: Select and Confirm Winning Supplier
                      </span>
                    )}
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-slate-50 text-slate-600 font-bold border-b border-slate-200">
                          <th className="py-2.5 px-3">Select</th>
                          <th className="py-2.5 px-3">Rank & Supplier</th>
                          <th className="py-2.5 px-3 text-right">Unit Price</th>
                          <th className="py-2.5 px-3 text-right">Total Bid</th>
                          <th className="py-2.5 px-3 text-right">Delivery Date</th>
                          <th className="py-2.5 px-3 text-right">Lead Time</th>
                          <th className="py-2.5 px-3 text-right">Price Score</th>
                          <th className="py-2.5 px-3 text-right">Delivery Score</th>
                          <th className="py-2.5 px-3 text-right">Total Score</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {quotationAnalysis.evaluations.map((item) => {
                          const isSelected = selectedWinningVendorId === item.vendor_id;
                          const isRec = item.is_recommended;

                          return (
                            <tr
                              key={item.vendor_id}
                              onClick={() => {
                                if (!isLockedPO) {
                                  setSelectedWinningVendorId(item.vendor_id);
                                  if (isVendorConfirmed && item.vendor_id !== confirmedVendorId) {
                                    setIsVendorConfirmed(false); // Reset confirmation if user switches vendor
                                  }
                                }
                              }}
                              className={`transition ${isLockedPO ? 'cursor-default' : 'cursor-pointer'} ${
                                isSelected ? 'bg-purple-50/60 font-semibold' : 'hover:bg-slate-50'
                              }`}
                            >
                              <td className="py-3 px-3">
                                <input
                                  type="radio"
                                  name="winning_vendor_select"
                                  checked={isSelected}
                                  disabled={isLockedPO}
                                  onChange={() => {
                                    if (!isLockedPO) {
                                      setSelectedWinningVendorId(item.vendor_id);
                                      if (isVendorConfirmed && item.vendor_id !== confirmedVendorId) {
                                        setIsVendorConfirmed(false);
                                      }
                                    }
                                  }}
                                  className="w-4 h-4 text-purple-600 focus:ring-purple-500 cursor-pointer disabled:opacity-50"
                                />
                              </td>
                              <td className="py-3 px-3">
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
                                        <span className="px-1.5 py-0.2 rounded text-[9px] font-black bg-amber-100 text-amber-800 border border-amber-300">
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
                              <td className="py-3 px-3 text-right font-medium text-slate-800">${item.quoted_unit_price}</td>
                              <td className="py-3 px-3 text-right font-bold text-slate-950">${item.total_price.toLocaleString()}</td>
                              <td className="py-3 px-3 text-right">
                                {item.expected_delivery_date ? (
                                  <span className="inline-flex items-center space-x-1 font-bold text-purple-900 bg-purple-50 px-2 py-0.5 rounded border border-purple-200">
                                    <Calendar className="w-3 h-3 text-purple-600 shrink-0" />
                                    <span>{item.expected_delivery_date}</span>
                                  </span>
                                ) : (
                                  <span className="text-slate-400 italic">—</span>
                                )}
                              </td>
                              <td className="py-3 px-3 text-right text-slate-600">{item.lead_time_days}d</td>
                              <td className="py-3 px-3 text-right text-slate-600">{item.price_score}</td>
                              <td className="py-3 px-3 text-right text-slate-600">
                                {item.delivery_date_score !== undefined ? item.delivery_date_score : item.delivery_score}
                              </td>
                              <td className="py-3 px-3 text-right font-black text-purple-800 text-sm">
                                {item.final_weighted_score} / 100
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>

                  {/* Override Warning for Post-RFQ Selection */}
                  {isPostRfqOverriding && (
                    <div className="p-3.5 bg-amber-50 rounded-xl border border-amber-300 text-xs space-y-1 text-amber-900">
                      <div className="flex items-center space-x-2 font-bold">
                        <ShieldAlert className="w-4 h-4 text-amber-600" />
                        <span>Supplier Override: You have selected a supplier other than the analytical recommendation ({quotationAnalysis.recommended_vendor_name}).</span>
                      </div>
                      <p className="text-[11px] text-amber-700">A structured justification will be required when confirming this procurement.</p>
                    </div>
                  )}

                  {/* Action Buttons for Post-RFQ */}
                  {isSupervisor && !isLockedPO && (
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-slate-100">
                      <div className="text-xs">
                        {isVendorConfirmed ? (
                          <div className="flex items-center space-x-2 text-emerald-800 bg-emerald-50 px-3 py-1.5 rounded-xl border border-emerald-200 font-medium">
                            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                            <span><strong>{winningVendorName}</strong> confirmed. Step 2: Click "Final Approval & Generate Purchase Order".</span>
                          </div>
                        ) : (
                          <span className="text-slate-500">
                            Select winning supplier above, then click <strong>Confirm Winning Supplier</strong> to unlock final approval.
                          </span>
                        )}
                      </div>

                      <div className="flex items-center space-x-3 shrink-0">
                        <button
                          type="button"
                          onClick={handleSelectWinningVendor}
                          disabled={actionLoading || !selectedWinningVendorId || isVendorConfirmed}
                          className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center space-x-1.5 ${
                            isVendorConfirmed
                              ? 'bg-slate-100 text-slate-500 border border-slate-200 cursor-default'
                              : 'bg-purple-600 hover:bg-purple-700 text-white shadow-sm shadow-purple-600/20'
                          }`}
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>{actionLoading ? 'Confirming...' : isVendorConfirmed ? 'Supplier Confirmed ✓' : 'Confirm Winning Supplier'}</span>
                        </button>

                        <button
                          type="button"
                          onClick={handleFinalApprovalAndPO}
                          disabled={actionLoading || !isVendorConfirmed}
                          className={`px-5 py-2.5 rounded-xl text-xs font-bold transition flex items-center space-x-2 ${
                            isVendorConfirmed
                              ? 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-md shadow-emerald-600/20 cursor-pointer animate-pulse'
                              : 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed shadow-none'
                          }`}
                          title={!isVendorConfirmed ? 'Please confirm winning supplier first' : 'Authorize procurement and generate PO'}
                        >
                          <FileCheck2 className="w-4 h-4" />
                          <span>{actionLoading ? 'Generating PO...' : 'Final Approval & Generate Purchase Order'}</span>
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-6 bg-slate-50 rounded-2xl border border-slate-200 text-center space-y-2 text-xs text-slate-500">
                  <Clock className="w-5 h-5 text-slate-400 mx-auto" />
                  <div className="font-bold text-slate-800">Awaiting Quotations from Invited Suppliers</div>
                  <p>Suppliers have been invited to submit bids through the Vendor Portal. Click <strong>Refresh Quotations</strong> to check for incoming submissions.</p>
                </div>
              )}
            </div>
          )}

          {/* Review History */}
          {pr.reviews && pr.reviews.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400">Previous Review Actions</div>
              <div className="space-y-1.5">
                {pr.reviews.map(r => (
                  <div key={r.id} className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 text-xs flex items-start justify-between">
                    <div>
                      <div className="font-bold text-slate-800">{r.decision.replace(/_/g, ' ')} by {r.supervisor_name}</div>
                      {r.reason && <p className="text-slate-600 mt-0.5 italic">"{r.reason}"</p>}
                    </div>
                    <span className="text-[10px] text-slate-400">{new Date(r.created_at).toLocaleDateString()}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-200 transition"
            >
              Close
            </button>
            {pr.status !== 'PO_GENERATED' && pr.status !== 'COMPLETED' && (
              <button
                type="button"
                onClick={handleDeletePR}
                disabled={actionLoading}
                className="px-3.5 py-2 rounded-xl border border-rose-200 text-rose-700 bg-rose-50 hover:bg-rose-100 text-xs font-bold transition flex items-center space-x-1.5 disabled:opacity-50"
              >
                <Trash2 className="w-3.5 h-3.5 text-rose-600" />
                <span>Delete Request</span>
              </button>
            )}
          </div>

          {isSupervisor && isPreRfqStage && (
            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={() => setShowRejectModal(true)}
                disabled={actionLoading}
                className="px-3.5 py-2 rounded-xl border border-rose-300 text-rose-800 bg-rose-50 hover:bg-rose-100 text-xs font-bold transition flex items-center space-x-1.5 disabled:opacity-50"
              >
                <XCircle className="w-4 h-4 text-rose-600" />
                <span>Reject Request</span>
              </button>

              <button
                type="button"
                onClick={() => setShowReturnModal(true)}
                disabled={actionLoading}
                className="px-3.5 py-2 rounded-xl border border-amber-300 text-amber-800 bg-amber-50 hover:bg-amber-100 text-xs font-bold transition flex items-center space-x-1.5 disabled:opacity-50"
              >
                <RotateCcw className="w-4 h-4 text-amber-700" />
                <span>Request Revision</span>
              </button>

              <button
                type="button"
                onClick={handleIssueRFQs}
                disabled={actionLoading || selectedVendorIds.length === 0}
                className="px-5 py-2.5 rounded-xl text-white text-xs font-bold bg-blue-600 hover:bg-blue-700 shadow-md shadow-blue-600/20 transition flex items-center space-x-2 disabled:opacity-50 cursor-pointer"
              >
                <Send className="w-4 h-4" />
                <span>{actionLoading ? 'Issuing RFQs...' : `Approve & Issue RFQs (${selectedVendorIds.length} Selected)`}</span>
              </button>
            </div>
          )}

          {!isSupervisor && (
            <div className="text-xs text-slate-500 bg-blue-50/70 border border-blue-200 text-blue-800 px-3.5 py-1.5 rounded-xl font-medium">
              ℹ Viewing as Employee (Requester). Supervisor review and RFQ issuance are authorized under Supervisor accounts (e.g. Rachel Zhang).
            </div>
          )}
        </div>

      </div>

      {/* ── Compare Modal ── */}
      {showCompareModal && snapshot?.all_candidates && (
        <CompareModal
          candidates={snapshot.all_candidates}
          onClose={() => setShowCompareModal(false)}
        />
      )}

      {/* ── Post-RFQ Override Reason Modal ── */}
      {showPostRfqOverrideModal && (
        <div className="fixed inset-0 z-60 bg-slate-900/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl border border-amber-200 space-y-4">
            <div className="flex items-center space-x-2 text-amber-700 font-bold text-sm">
              <ShieldAlert className="w-5 h-5" />
              <span>Quotation Override Governance Reason Required</span>
            </div>
            <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 text-xs text-amber-800 space-y-1">
              <p className="font-semibold">You are approving a supplier other than the analytical recommendation.</p>
              <p>Analytical Pick: <strong>{quotationAnalysis?.recommended_vendor_name}</strong></p>
              <p>Selected Supplier: <strong>{quotationAnalysis?.evaluations.find(e => e.vendor_id === selectedWinningVendorId)?.vendor_name}</strong></p>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-700">Override Reason <span className="text-rose-500">*</span></label>
              <select
                value={postRfqOverrideReason}
                onChange={e => { setPostRfqOverrideReason(e.target.value); setPostRfqOverrideDetail(''); }}
                className="w-full p-2.5 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-amber-500"
              >
                <option value="">— Select a reason —</option>
                {OVERRIDE_REASONS.map(r => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
              {postRfqOverrideReason === 'Other (specify below)' && (
                <textarea
                  rows={3}
                  value={postRfqOverrideDetail}
                  onChange={e => setPostRfqOverrideDetail(e.target.value)}
                  placeholder="Provide specific business justification..."
                  className="w-full p-3 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-amber-500"
                />
              )}
            </div>
            {actionError && (
              <div className="text-xs text-rose-600 bg-rose-50 p-2 rounded-lg border border-rose-200">
                {actionError}
              </div>
            )}
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => { setShowPostRfqOverrideModal(false); setActionError(null); }}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleSelectWinningVendor}
                disabled={actionLoading || !postRfqOverrideReason}
                className="px-4 py-2 text-xs font-bold text-white bg-purple-600 hover:bg-purple-700 rounded-xl transition disabled:opacity-50"
              >
                Confirm Supplier
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Mandatory Return Reason Modal */}
      {showReturnModal && (
        <div className="fixed inset-0 z-60 bg-slate-900/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl border border-slate-200 space-y-4">
            <div className="flex items-center space-x-2 text-amber-600 font-bold text-sm">
              <RotateCcw className="w-5 h-5" />
              <span>Return Purchase Request for Revision</span>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              Business rules mandate a documented, substantive reason before returning a request to the employee.
            </p>
            <textarea
              rows={4}
              value={returnReason}
              onChange={e => setReturnReason(e.target.value)}
              placeholder="Specify required corrections, inventory reallocation, or budget adjustment..."
              className="w-full p-3 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-amber-500"
            />
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowReturnModal(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleReturnForRevision}
                disabled={actionLoading}
                className="px-4 py-2 text-xs font-bold text-white bg-amber-600 hover:bg-amber-700 rounded-xl transition"
              >
                Confirm Return
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Mandatory Reject Reason Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 z-60 bg-slate-900/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl border border-slate-200 space-y-4">
            <div className="flex items-center space-x-2 text-rose-600 font-bold text-sm">
              <XCircle className="w-5 h-5" />
              <span>Reject Purchase Request</span>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              Rejecting a purchase request terminates the procurement workflow. A substantive governance justification is mandatory.
            </p>
            <textarea
              rows={4}
              value={rejectReason}
              onChange={e => setRejectReason(e.target.value)}
              placeholder="Specify rationale for rejection (e.g., redundant expenditure, unauthorized item, budget freeze)..."
              className="w-full p-3 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-rose-500"
            />
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowRejectModal(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleRejectPR}
                disabled={actionLoading}
                className="px-4 py-2 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 rounded-xl transition"
              >
                Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
