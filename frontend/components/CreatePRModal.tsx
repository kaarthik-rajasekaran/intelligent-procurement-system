'use client';

import React, { useState, useEffect } from 'react';
import { Item, InventoryAnalysis, RAGVendorRecommendation, DuplicateMatch, Vendor } from '../lib/types';
import { api } from '../lib/api';
import {
  X,
  Package,
  AlertTriangle,
  CheckCircle2,
  Award,
  Sparkles,
  TrendingUp,
  TrendingDown,
  Minus,
  ShieldAlert,
  ArrowRight,
  Bot,
  Check,
  Search,
  MessageSquare,
  ShieldCheck,
  RefreshCw,
  Info
} from 'lucide-react';

interface CreatePRModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  items: Item[];
}

export const CreatePRModal: React.FC<CreatePRModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  items
}) => {
  const [selectedItemId, setSelectedItemId] = useState<string>('');
  const [quantity, setQuantity] = useState<number>(10);
  const [selectedVendorId, setSelectedVendorId] = useState<string>('');
  const [notes, setNotes] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Live Inventory State (User-Triggered)
  const [inventoryAnalysis, setInventoryAnalysis] = useState<InventoryAnalysis | null>(null);
  const [isCheckingInventory, setIsCheckingInventory] = useState(false);
  const [lastCheckedInvItem, setLastCheckedInvItem] = useState<string>('');
  const [lastCheckedInvQty, setLastCheckedInvQty] = useState<number>(0);

  // AI + RAG Vendor Recommendation State (User-Triggered)
  const [vendorRecs, setVendorRecs] = useState<RAGVendorRecommendation[]>([]);
  const [isLoadingRecs, setIsLoadingRecs] = useState(false);
  const [lastRecItem, setLastRecItem] = useState<string>('');
  const [lastRecQty, setLastRecQty] = useState<number>(0);
  const recsSectionRef = React.useRef<HTMLDivElement>(null);

  // Available vendors for direct manual selection fallback
  const [allVendors, setAllVendors] = useState<Vendor[]>([]);

  // Duplicate Warning Modal states
  const [showDuplicateModal, setShowDuplicateModal] = useState(false);
  const [detectedDuplicates, setDetectedDuplicates] = useState<DuplicateMatch[]>([]);
  const [duplicateAcknowledged, setDuplicateAcknowledged] = useState(false);

  // Set default item when opened & load vendors for manual fallback
  useEffect(() => {
    if (items.length > 0 && !selectedItemId) {
      setSelectedItemId(items[0].id);
    }
    api.getVendors().then(setAllVendors).catch(() => {});
  }, [items, selectedItemId]);

  if (!isOpen) return null;

  const selectedItem = items.find(i => i.id === selectedItemId);

  // Invalidation / Stale detection
  const isInventoryChecked = inventoryAnalysis !== null;
  const isInventoryStale = isInventoryChecked && (lastCheckedInvItem !== selectedItemId || lastCheckedInvQty !== quantity);

  const isRecGenerated = vendorRecs.length > 0;
  const isRecStale = isRecGenerated && (lastRecItem !== selectedItemId || lastRecQty !== quantity);

  // Handler: Check Live Inventory (Explicit button click)
  const handleCheckInventory = async () => {
    if (!selectedItemId || quantity <= 0) return;
    setIsCheckingInventory(true);
    setErrorMessage(null);
    try {
      const inv = await api.checkInventory(selectedItemId, quantity);
      setInventoryAnalysis(inv);
      setLastCheckedInvItem(selectedItemId);
      setLastCheckedInvQty(quantity);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to check inventory.');
    } finally {
      setIsCheckingInventory(false);
    }
  };

  // Handler: Run Vendor Recommendation (Explicit button click)
  const handleRunVendorRecommendation = async () => {
    if (!selectedItemId || quantity <= 0) return;
    setIsLoadingRecs(true);
    setErrorMessage(null);
    try {
      let recs: RAGVendorRecommendation[] = [];
      try {
        recs = await api.getVendorRecommendationsRAG(selectedItemId, quantity);
      } catch (err) {
        // Fallback to analytical if RAG endpoint encounters unexpected error
        const oldRecs = await api.getVendorRecommendations(selectedItemId);
        recs = oldRecs.map(r => ({
          rank: r.rank,
          vendor_id: r.vendor_id,
          vendor_name: r.vendor_name,
          recommendation_status: (r.rank === 1 ? 'RECOMMENDED' : 'ACCEPTABLE') as 'RECOMMENDED' | 'ACCEPTABLE' | 'CAUTION',
          reasoning_summary: r.explanation,
          key_strengths: [r.explanation],
          potential_risks: [],
          evidence_confidence: r.score_confidence as 'HIGH' | 'MEDIUM' | 'LOW',
          avg_quality_rating: r.factor_breakdown.quality / 10,
          avg_delivery_rating: r.factor_breakdown.delivery_reliability / 10,
          review_count: 0,
          review_insights: [],
          // No review data in this fallback — final score = analytical score
          final_recommendation_score: r.overall_score,
          analytical_score: r.overall_score,
          badges: r.badges,
          source: 'ANALYTICAL_FALLBACK' as const
        }));
      }

      setVendorRecs(recs);
      setLastRecItem(selectedItemId);
      setLastRecQty(quantity);

      // Pre-select rank 1 recommended vendor if none selected or if previously selected is no longer in recs
      if (recs.length > 0) {
        if (!selectedVendorId || !recs.some(r => r.vendor_id === selectedVendorId)) {
          setSelectedVendorId(recs[0].vendor_id);
        }
        setTimeout(() => {
          recsSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 150);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to run vendor recommendation analysis.');
    } finally {
      setIsLoadingRecs(false);
    }
  };

  const handleSubmitAttempt = async () => {
    setErrorMessage(null);
    if (!selectedItemId) {
      setErrorMessage('Please select an item to procure.');
      return;
    }
    if (quantity <= 0) {
      setErrorMessage('Quantity must be greater than zero.');
      return;
    }
    if (!selectedVendorId) {
      setErrorMessage('Please select a supplier for this purchase request.');
      return;
    }

    // Check for duplicates before submitting if not already acknowledged
    if (!duplicateAcknowledged) {
      let activeDups = detectedDuplicates;
      try {
        activeDups = await api.checkDuplicates(selectedItemId, quantity);
        setDetectedDuplicates(activeDups);
      } catch (e) {
        activeDups = [];
      }
      if (activeDups && activeDups.length > 0) {
        setShowDuplicateModal(true);
        return;
      }
    }

    executeSubmission(duplicateAcknowledged);
  };

  const executeSubmission = async (ack: boolean) => {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      const newPR = await api.createPR({
        item_id: selectedItemId,
        quantity,
        selected_vendor_id: selectedVendorId,
        notes,
        duplicate_acknowledged: ack,
      });

      // ─── Persist RAG recommendation snapshot (fire-and-forget) ───────────
      // Only if the employee actually ran the RAG recommendation engine.
      // This is a silent background save — it must NOT block PR creation.
      if (vendorRecs.length > 0 && newPR?.id) {
        const top = vendorRecs[0];
        const snapshotPayload = {
          item_id: selectedItemId,
          item_name: selectedItem?.name,
          category: selectedItem?.category,
          quantity,
          recommended_vendor_id: top.vendor_id,
          recommended_vendor_name: top.vendor_name,
          all_candidates: vendorRecs,
          evidence_confidence: top.evidence_confidence,
          reasoning_summary: top.reasoning_summary,
          key_strengths: top.key_strengths,
          potential_risks: top.potential_risks,
          avg_quality_rating: top.avg_quality_rating,
          avg_delivery_rating: top.avg_delivery_rating,
          avg_price_rating: top.avg_price_rating,
          trend_direction: top.trend_direction,
          review_count: top.review_count,
          final_recommendation_score: top.final_recommendation_score,
          analytical_score: top.analytical_score,
          source: top.source,
        };
        api.saveRecommendationSnapshot(newPR.id, snapshotPayload).catch(err => {
          // Non-blocking — log but don't disrupt PR creation success
          console.warn('[CreatePRModal] Failed to persist recommendation snapshot:', err);
        });
      }
      // ─────────────────────────────────────────────────────────────────────

      onSuccess();
      onClose();
    } catch (err: any) {
      if (err.status === 409 || err.message?.includes('duplicate')) {
        const dups = await api.checkDuplicates(selectedItemId, quantity).catch(() => []);
        setDetectedDuplicates(dups);
        setShowDuplicateModal(true);
      } else {
        setErrorMessage(err.message || 'Failed to submit Purchase Request.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAcknowledgeAndProceed = async () => {
    setDuplicateAcknowledged(true);
    setShowDuplicateModal(false);
    await executeSubmission(true);
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Create Structured Purchase Request</h2>
            <p className="text-xs text-slate-500">
              Deterministic inventory checking & user-triggered AI + RAG supplier recommendation
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-6 overflow-y-auto flex-1">
          {errorMessage && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 flex items-start space-x-2">
              <AlertTriangle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Section 1: Item & Quantity Input */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2 space-y-1.5">
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                1. Select Catalog Item
              </label>
              <select
                value={selectedItemId}
                onChange={e => {
                  setSelectedItemId(e.target.value);
                  setSelectedVendorId('');
                }}
                className="w-full px-3 py-2.5 bg-white border border-slate-300 rounded-xl text-sm font-medium focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
              >
                {items.map(item => (
                  <option key={item.id} value={item.id}>
                    {item.name} ({item.category})
                  </option>
                ))}
              </select>
              {selectedItem?.description && (
                <p className="text-xs text-slate-400 italic mt-1">{selectedItem.description}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                2. Required Quantity
              </label>
              <div className="relative">
                <input
                  type="number"
                  min="1"
                  max="10000"
                  value={quantity}
                  onChange={e => setQuantity(parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 bg-white border border-slate-300 rounded-xl text-sm font-semibold focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
                />
                <span className="absolute right-3 top-2.5 text-xs text-slate-400 font-medium">
                  {selectedItem?.unit || 'units'}
                </span>
              </div>
            </div>
          </div>

          {/* Section 2: Deterministic Live Inventory Section */}
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Package className="w-4 h-4 text-blue-600" />
                <span className="text-xs font-bold uppercase text-slate-800 tracking-wider">
                  Live Inventory Status
                </span>
              </div>
              <button
                type="button"
                onClick={handleCheckInventory}
                disabled={!selectedItemId || quantity <= 0 || isCheckingInventory}
                className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-sm transition flex items-center space-x-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isCheckingInventory ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Checking Live Inventory...</span>
                  </>
                ) : (
                  <>
                    <Search className="w-3.5 h-3.5" />
                    <span>Check Live Inventory</span>
                  </>
                )}
              </button>
            </div>

            {/* Stale warning if inputs changed after check */}
            {isInventoryStale && (
              <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                  <span>Item or quantity has changed. Re-check inventory for accurate stock status.</span>
                </div>
                <button
                  type="button"
                  onClick={handleCheckInventory}
                  className="underline font-bold text-amber-900 ml-2 text-xs"
                >
                  Refresh
                </button>
              </div>
            )}

            {/* Inventory Results Display */}
            {inventoryAnalysis ? (
              <div className="space-y-3 pt-1">
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div className="p-2.5 bg-white rounded-lg border border-slate-200 shadow-sm">
                    <div className="text-[10px] uppercase font-bold text-slate-400">Available Stock</div>
                    <div className="text-base font-bold text-slate-800">
                      {inventoryAnalysis.available_quantity} {selectedItem?.unit}
                    </div>
                  </div>
                  <div className="p-2.5 bg-white rounded-lg border border-slate-200 shadow-sm">
                    <div className="text-[10px] uppercase font-bold text-slate-400">Requested Quantity</div>
                    <div className="text-base font-bold text-slate-800">
                      {inventoryAnalysis.requested_quantity} {selectedItem?.unit}
                    </div>
                  </div>
                  <div className="p-2.5 bg-white rounded-lg border border-slate-200 shadow-sm">
                    <div className="text-[10px] uppercase font-bold text-slate-400">Net Shortage</div>
                    <div className={`text-base font-bold ${inventoryAnalysis.shortage_quantity > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>
                      {inventoryAnalysis.shortage_quantity > 0 ? `${inventoryAnalysis.shortage_quantity} ${selectedItem?.unit}` : '0 (None)'}
                    </div>
                  </div>
                </div>

                {/* Status Guidance Banner */}
                {inventoryAnalysis.coverage_status === 'SUFFICIENT' ? (
                  <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl flex items-start space-x-2.5 text-xs text-emerald-900">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <div>
                      <strong className="block font-bold">Inventory Available</strong>
                      <span>
                        Sufficient internal inventory ({inventoryAnalysis.available_quantity} {selectedItem?.unit}) is available in warehouse reserves. You may utilize available stock or continue with external procurement if separate project allocation is needed.
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-start space-x-2.5 text-xs text-amber-900">
                    <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                    <div>
                      <strong className="block font-bold">Insufficient Inventory — Procurement Recommended</strong>
                      <span>
                        Current warehouse stock ({inventoryAnalysis.available_quantity} {selectedItem?.unit}) cannot satisfy this request. A shortage of {inventoryAnalysis.shortage_quantity} {selectedItem?.unit} exists. External supplier procurement is recommended.
                      </span>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-3 bg-white rounded-lg border border-dashed border-slate-300 text-xs text-slate-500 flex items-center space-x-2">
                <Info className="w-4 h-4 text-slate-400 shrink-0" />
                <span>Live inventory has not been checked yet. Click <strong>&ldquo;Check Live Inventory&rdquo;</strong> to query current stock reserves.</span>
              </div>
            )}
          </div>

          {/* Section 3: AI + RAG Vendor Recommendations (User-Triggered) */}
          <div ref={recsSectionRef} className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-purple-600" />
                <label className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  3. AI + RAG Vendor Recommendations
                </label>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-200">
                  Contextual AI Intelligence
                </span>
              </div>
              <button
                type="button"
                onClick={handleRunVendorRecommendation}
                disabled={!selectedItemId || quantity <= 0 || isLoadingRecs}
                className="px-3.5 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold shadow-sm transition flex items-center space-x-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoadingRecs ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Analyzing Reviews...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>{isRecGenerated ? 'Re-run Recommendation' : 'Run Vendor Recommendation'}</span>
                  </>
                )}
              </button>
            </div>

            {/* Score legend — only shown once recommendations exist */}
            {isRecGenerated && (
              <div className="px-3 py-2 bg-slate-50 rounded-lg border border-slate-200 text-[10px] text-slate-500 leading-relaxed">
                <span className="font-bold text-slate-700">Final Score</span> = Historical Performance (40%) + Review Evidence (40%) + Confidence Bonus (20%)
                <span className="ml-1 text-purple-600 font-semibold">× AI modifier</span>
                <span className="ml-2 text-slate-400">(CAUTION −15% · RECOMMENDED +5%)</span>
                {' · '}
                <span className="font-bold text-slate-600">Rank always follows Final Score.</span>
              </div>
            )}

            {/* Stale warning if inputs changed after recommendations */}
            {isRecStale && (
              <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                  <span>Request item or quantity has changed. Run Vendor Recommendation again to update AI insights.</span>
                </div>
                <button
                  type="button"
                  onClick={handleRunVendorRecommendation}
                  className="underline font-bold text-amber-900 ml-2 text-xs"
                >
                  Refresh AI
                </button>
              </div>
            )}

            {/* State A: Loading State */}
            {isLoadingRecs && (
              <div className="p-8 rounded-xl border border-purple-200 bg-purple-50/50 flex flex-col items-center justify-center space-y-2 text-center text-purple-900 animate-pulse">
                <Bot className="w-8 h-8 text-purple-600 animate-bounce" />
                <span className="text-xs font-bold">Retrieving vendor reviews and generating contextual recommendations...</span>
                <span className="text-[11px] text-purple-600">Performing RAG semantic retrieval & Gemini qualitative reasoning</span>
              </div>
            )}

            {/* State B: Inactive / Un-run State */}
            {!isLoadingRecs && !isRecGenerated && (
              <div className="p-8 rounded-xl border-2 border-dashed border-slate-200 bg-slate-50/50 text-center flex flex-col items-center justify-center space-y-3">
                <div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center text-purple-600">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div className="max-w-md space-y-1">
                  <h4 className="text-xs font-bold text-slate-800">Vendor recommendations have not been generated yet</h4>
                  <p className="text-[11px] text-slate-500 leading-relaxed">
                    Click <strong>&ldquo;Run Vendor Recommendation&rdquo;</strong> to trigger the AI + RAG engine. It evaluates structured supplier ratings and qualitative review evidence to produce contextually ranked recommendations.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleRunVendorRecommendation}
                  disabled={!selectedItemId || quantity <= 0}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold rounded-xl shadow-sm transition flex items-center space-x-2 disabled:opacity-50"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Run Vendor Recommendation</span>
                </button>
              </div>
            )}

            {/* State C: Recommendation Results Display */}
            {!isLoadingRecs && isRecGenerated && (
              <div className="grid grid-cols-1 gap-3 max-h-80 overflow-y-auto p-1">
                {vendorRecs.map((rec) => {
                  const isSelected = selectedVendorId === rec.vendor_id;
                  const isCaution = rec.recommendation_status === 'CAUTION';
                  const isRecommended = rec.recommendation_status === 'RECOMMENDED';

                  return (
                    <div
                      key={rec.vendor_id}
                      onClick={() => setSelectedVendorId(rec.vendor_id)}
                      className={`p-4 rounded-xl border-2 cursor-pointer transition relative flex flex-col justify-between space-y-3 ${
                        isSelected
                          ? 'border-blue-600 bg-blue-50/40 shadow-sm ring-2 ring-blue-500/20'
                          : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/60'
                      }`}
                    >
                      {/* Top Row: Rank, Name, Status, Confidence & Source */}
                      <div className="flex items-start justify-between">
                        <div className="flex items-center space-x-2.5">
                          <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-black ${
                            rec.rank === 1 ? 'bg-amber-400 text-amber-950 shadow-sm' : 'bg-slate-200 text-slate-700'
                          }`}>
                            #{rec.rank}
                          </span>
                          <div>
                            <span className="font-bold text-sm text-slate-900">{rec.vendor_name}</span>
                            <div className="flex items-center space-x-1.5 mt-0.5">
                              {/* Status */}
                              <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                                isRecommended
                                  ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                                  : isCaution
                                  ? 'bg-amber-100 text-amber-800 border border-amber-300'
                                  : 'bg-blue-100 text-blue-800 border border-blue-200'
                              }`}>
                                {isRecommended && <Check className="w-3 h-3 mr-1" />}
                                {isCaution && <AlertTriangle className="w-3 h-3 mr-1" />}
                                {rec.recommendation_status}
                              </span>

                              {/* Confidence Tag */}
                              <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                                rec.evidence_confidence === 'HIGH'
                                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                  : rec.evidence_confidence === 'MEDIUM'
                                  ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                  : 'bg-rose-50 text-rose-700 border border-rose-200'
                              }`}>
                                <ShieldCheck className="w-3 h-3 mr-1" />
                                {rec.evidence_confidence} Confidence
                              </span>

                              {/* Source Badge */}
                              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-semibold bg-purple-50 text-purple-700 border border-purple-200">
                                {rec.source === 'LLM_RAG' ? '✨ LLM + RAG' : '📊 Analytical'}
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Final Score (canonical ranking score) + Historical Score (secondary) */}
                        <div className="text-right">
                          <div className="text-xs font-black text-purple-800 bg-purple-100 px-2.5 py-1 rounded-lg border border-purple-200 tabular-nums">
                            {rec.final_recommendation_score.toFixed(1)} / 100
                          </div>
                          <div className="text-[9px] text-slate-400 mt-0.5 text-right">
                            Historical: {rec.analytical_score.toFixed(1)}
                          </div>
                        </div>
                      </div>

                      {/* LLM Contextual Reasoning Summary */}
                      {rec.reasoning_summary && (
                        <div className="p-2.5 rounded-lg bg-slate-50/80 border border-slate-200/80 text-xs text-slate-700 leading-relaxed">
                          <span className="font-bold text-slate-900">AI Contextual Analysis: </span>
                          {rec.reasoning_summary}
                        </div>
                      )}

                      {/* Strengths & Risks Columns */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                        {rec.key_strengths && rec.key_strengths.length > 0 && (
                          <div className="p-2 rounded-lg bg-emerald-50/50 border border-emerald-100 space-y-1">
                            <span className="text-[10px] font-bold uppercase text-emerald-800 tracking-wider">Key Strengths</span>
                            <ul className="space-y-0.5 text-[11px] text-emerald-900">
                              {rec.key_strengths.map((str, idx) => (
                                <li key={idx} className="flex items-start space-x-1.5">
                                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                                  <span>{str}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {rec.potential_risks && rec.potential_risks.length > 0 && (
                          <div className="p-2 rounded-lg bg-amber-50/60 border border-amber-200 space-y-1">
                            <span className="text-[10px] font-bold uppercase text-amber-800 tracking-wider">Potential Risks</span>
                            <ul className="space-y-0.5 text-[11px] text-amber-900">
                              {rec.potential_risks.map((risk, idx) => (
                                <li key={idx} className="flex items-start space-x-1.5">
                                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                                  <span>{risk}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>

                      {/* Real Qualitative Review Insight Snippets */}
                      {rec.review_insights && rec.review_insights.length > 0 && (
                        <div className="space-y-1 pt-1 border-t border-slate-100">
                          <span className="text-[10px] font-bold uppercase text-slate-400 tracking-wider flex items-center space-x-1">
                            <MessageSquare className="w-3 h-3 text-slate-400" />
                            <span>Qualitative Review Evidence</span>
                          </span>
                          <div className="space-y-1">
                            {rec.review_insights.map((insight, idx) => (
                              <div key={idx} className="text-[11px] italic text-slate-600 bg-slate-50 p-2 rounded-md border border-slate-200/60">
                                &ldquo;{insight}&rdquo;
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Bottom Quantitative Summary Bar */}
                      <div className="flex flex-wrap items-center justify-between pt-2 border-t border-slate-100 text-[10px] text-slate-500 gap-2">
                        <div className="flex items-center space-x-3">
                          {rec.avg_quality_rating != null && (
                            <span>Quality: <strong className="text-slate-800">{rec.avg_quality_rating}/10</strong></span>
                          )}
                          {rec.avg_delivery_rating != null && (
                            <span>Delivery: <strong className="text-slate-800">{rec.avg_delivery_rating}/10</strong></span>
                          )}
                          {rec.review_count > 0 && (
                            <span>Reviews: <strong className="text-slate-800">{rec.review_count}</strong></span>
                          )}
                          {rec.trend_direction && (
                            <span className="flex items-center space-x-0.5">
                              <span>Trend:</span>
                              {rec.trend_direction === 'IMPROVING' && (
                                <span className="text-emerald-600 font-bold flex items-center">
                                  <TrendingUp className="w-3 h-3 mr-0.5" /> Improving
                                </span>
                              )}
                              {rec.trend_direction === 'DECLINING' && (
                                <span className="text-rose-600 font-bold flex items-center">
                                  <TrendingDown className="w-3 h-3 mr-0.5" /> Declining
                                </span>
                              )}
                              {rec.trend_direction === 'STABLE' && (
                                <span className="text-slate-600 font-bold flex items-center">
                                  <Minus className="w-3 h-3 mr-0.5" /> Stable
                                </span>
                              )}
                            </span>
                          )}
                        </div>

                        {/* Badges */}
                        <div className="flex flex-wrap gap-1">
                          {rec.badges && rec.badges.map((badge, idx) => (
                            <span
                              key={idx}
                              className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-slate-100 text-slate-700 border border-slate-200"
                            >
                              {badge.replace('_', ' ')}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Section 4: Supplier Selection (If recommendations not yet run, allows manual fallback) */}
          {!isRecGenerated && allVendors.length > 0 && (
            <div className="space-y-1.5 p-3 rounded-xl bg-slate-50 border border-slate-200">
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Select Supplier Manually (Optional or Run Recommendations above)
              </label>
              <select
                value={selectedVendorId}
                onChange={e => setSelectedVendorId(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-slate-300 rounded-xl text-xs font-medium focus:ring-2 focus:ring-blue-500 transition"
              >
                <option value="">-- Choose Supplier --</option>
                {allVendors.map(v => (
                  <option key={v.id} value={v.id}>
                    {v.name} ({v.email})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Section 5: Justification Notes */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">Procurement Justification / Notes</label>
            <textarea
              rows={2}
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="Provide operational context or urgency details for supervisor review..."
              className="w-full px-3 py-2 bg-white border border-slate-300 rounded-xl text-xs font-medium focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
            />
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-200 transition"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmitAttempt}
            disabled={isSubmitting}
            className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-md shadow-blue-500/20 transition flex items-center space-x-2 disabled:opacity-50"
          >
            {isSubmitting ? (
              <span>Submitting PR...</span>
            ) : (
              <>
                <span>Submit to Supervisor</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>

      </div>

      {/* Interactive Duplicate Warning Confirmation Modal */}
      {showDuplicateModal && (
        <div className="fixed inset-0 z-60 bg-slate-900/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 max-w-lg w-full shadow-2xl border border-amber-200 space-y-5 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-start space-x-3 text-amber-900">
              <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">Potential Duplicate Request Detected</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  The system identified {detectedDuplicates.length} active purchase request(s) for the same item in your department with a quantity within ±20%.
                </p>
              </div>
            </div>

            {/* List of conflicting PRs */}
            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {detectedDuplicates.map(dup => (
                <div key={dup.id} className="p-3 bg-amber-50/70 rounded-xl border border-amber-200/80 text-xs space-y-1">
                  <div className="flex items-center justify-between font-bold text-slate-900">
                    <span>{dup.reference_number}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded font-bold bg-amber-200/80 text-amber-900">
                      {dup.difference_percentage}% quantity diff
                    </span>
                  </div>
                  <div className="text-slate-600 flex items-center justify-between text-[11px]">
                    <span>Item: <strong>{dup.item_name}</strong></span>
                    <span>Existing Qty: <strong>{dup.existing_quantity}</strong> (Req: {dup.requested_quantity})</span>
                  </div>
                  <div className="text-slate-500 flex items-center justify-between text-[10px] pt-1 border-t border-amber-100">
                    <span>Status: <span className="font-semibold text-slate-700">{dup.status}</span></span>
                    <span>Date: {new Date(dup.request_date).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="p-3 bg-slate-50 rounded-xl text-[11px] text-slate-600 leading-relaxed border border-slate-100">
              <strong>Corporate Procurement Policy:</strong> Submitting redundant requests consumes department budget and may be returned by your supervisor. If this is a separate, intentional requirement, confirm acknowledgment to submit.
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end space-x-2 pt-2">
              <button
                type="button"
                onClick={() => setShowDuplicateModal(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition"
              >
                Cancel & Review
              </button>
              <button
                type="button"
                onClick={handleAcknowledgeAndProceed}
                disabled={isSubmitting}
                className="px-4 py-2 text-xs font-bold text-white bg-amber-600 hover:bg-amber-700 rounded-xl shadow-md shadow-amber-600/20 transition flex items-center space-x-1.5 disabled:opacity-50"
              >
                <ShieldAlert className="w-4 h-4" />
                <span>{isSubmitting ? 'Submitting...' : 'Acknowledge & Proceed'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
