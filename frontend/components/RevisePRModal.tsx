'use client';

import React, { useState, useEffect } from 'react';
import { PurchaseRequest, Item, Vendor, InventoryAnalysis } from '../lib/types';
import { api } from '../lib/api';
import {
  X,
  RotateCcw,
  AlertTriangle,
  Package,
  CheckCircle2,
  Sparkles,
  Send,
  Building,
  DollarSign,
  Info,
  Calendar,
  Layers
} from 'lucide-react';

interface RevisePRModalProps {
  pr: PurchaseRequest | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function RevisePRModal({ pr, isOpen, onClose, onSuccess }: RevisePRModalProps) {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Form State
  const [quantity, setQuantity] = useState<number>(1);
  const [selectedVendorId, setSelectedVendorId] = useState<string>('');
  const [notes, setNotes] = useState<string>('');

  // Additional Data
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [inventoryAnalysis, setInventoryAnalysis] = useState<InventoryAnalysis | null>(null);
  const [checkingInventory, setCheckingInventory] = useState<boolean>(false);
  const [latestSupervisorReview, setLatestSupervisorReview] = useState<{
    supervisorName?: string;
    reason?: string;
    createdAt?: string;
  } | null>(null);

  useEffect(() => {
    if (isOpen && pr) {
      setQuantity(pr.quantity || 1);
      setSelectedVendorId(pr.selected_vendor_id || '');
      setNotes(pr.notes || '');
      setError(null);
      setSuccessMsg(null);

      // Fetch vendors and detailed PR with review history
      fetchPrDetailAndVendors();
    }
  }, [isOpen, pr]);

  const fetchPrDetailAndVendors = async () => {
    if (!pr) return;
    try {
      setLoading(true);
      const [detailRes, vendorsRes] = await Promise.all([
        api.getPRDetail(pr.id),
        api.getVendors()
      ]);

      setVendors(vendorsRes.filter(v => v.is_active));
      if (detailRes.selected_vendor_id) {
        setSelectedVendorId(detailRes.selected_vendor_id);
      }
      if (detailRes.quantity) {
        setQuantity(detailRes.quantity);
      }
      if (detailRes.notes) {
        setNotes(detailRes.notes);
      }

      // Find the latest RETURNED supervisor review
      if (detailRes.reviews && detailRes.reviews.length > 0) {
        const returnedReviews = detailRes.reviews.filter(
          r => r.decision === 'RETURNED' || r.decision === 'RETURNED_FOR_REVISION'
        );
        if (returnedReviews.length > 0) {
          const latest = returnedReviews[returnedReviews.length - 1];
          setLatestSupervisorReview({
            supervisorName: latest.supervisor_name,
            reason: latest.reason,
            createdAt: latest.created_at
          });
        }
      }

      // Check live inventory for the item and current quantity
      if (detailRes.item_id) {
        runInventoryCheck(detailRes.item_id, detailRes.quantity || 1);
      }
    } catch (err: any) {
      console.error('Failed to load PR details:', err);
    } finally {
      setLoading(false);
    }
  };

  const runInventoryCheck = async (itemId: string, qty: number) => {
    if (!itemId || qty <= 0) return;
    setCheckingInventory(true);
    try {
      const inv = await api.checkInventory(itemId, qty);
      setInventoryAnalysis(inv);
    } catch (err) {
      console.error('Failed to analyze inventory:', err);
    } finally {
      setCheckingInventory(false);
    }
  };

  const handleQuantityChange = (newQty: number) => {
    const validQty = Math.max(1, newQty);
    setQuantity(validQty);
    if (pr?.item_id) {
      runInventoryCheck(pr.item_id, validQty);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pr) return;

    if (quantity <= 0) {
      setError('Quantity must be greater than 0.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await api.resubmitPR(pr.id, {
        quantity,
        selected_vendor_id: selectedVendorId || undefined,
        notes: notes.trim() ? notes : undefined
      });

      setSuccessMsg('Purchase Request successfully revised and resubmitted to your supervisor!');
      setTimeout(() => {
        onSuccess();
        onClose();
      }, 1200);
    } catch (err: any) {
      setError(err.message || 'Failed to resubmit Purchase Request.');
      setLoading(false);
    }
  };

  if (!isOpen || !pr) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden animate-scale-up">
        
        {/* Header */}
        <div className="px-6 py-5 bg-gradient-to-r from-amber-500/10 via-amber-50 to-orange-50 border-b border-amber-200/60 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-amber-500 text-white rounded-xl shadow-md shadow-amber-500/20">
              <RotateCcw className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-lg font-bold text-slate-900">Revise Purchase Request</h3>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-200">
                  {pr.reference_number}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Update request details in response to supervisor feedback and resubmit for approval.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-white rounded-lg transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto space-y-6 flex-1">
          {error && (
            <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-start space-x-2.5">
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-start space-x-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <span className="font-semibold">{successMsg}</span>
            </div>
          )}

          {/* Supervisor Feedback Callout */}
          {latestSupervisorReview && (
            <div className="p-4 bg-amber-50/80 rounded-xl border border-amber-200 shadow-sm space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-amber-900 flex items-center space-x-1.5">
                  <AlertTriangle className="w-4 h-4 text-amber-600" />
                  <span>Supervisor Revision Note ({latestSupervisorReview.supervisorName || 'Supervisor'})</span>
                </span>
                {latestSupervisorReview.createdAt && (
                  <span className="text-[10px] text-amber-700 font-medium">
                    {new Date(latestSupervisorReview.createdAt).toLocaleDateString()}
                  </span>
                )}
              </div>
              <p className="text-xs text-amber-950 font-medium bg-white/80 p-3 rounded-lg border border-amber-200/60 leading-relaxed italic">
                &ldquo;{latestSupervisorReview.reason}&rdquo;
              </p>
            </div>
          )}

          {/* Item Overview Card */}
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Item Details</span>
              <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-[10px] font-bold rounded">
                Department: {pr.department_name}
              </span>
            </div>
            <div className="flex items-center space-x-3">
              <div className="p-2.5 bg-white border border-slate-200 rounded-lg text-slate-700 shadow-sm">
                <Package className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900">{pr.item_name || 'Selected Item'}</h4>
                <p className="text-xs text-slate-500">Unit of Measurement: {pr.item_unit || 'Units'}</p>
              </div>
            </div>
          </div>

          {/* Quantity Stepper & Live Stock Analysis */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-700 flex items-center justify-between">
              <span>Requested Quantity ({pr.item_unit || 'Units'})</span>
              {checkingInventory && (
                <span className="text-[10px] text-blue-600 animate-pulse font-normal">
                  Checking warehouse stock...
                </span>
              )}
            </label>
            <div className="flex items-center space-x-3">
              <button
                type="button"
                onClick={() => handleQuantityChange(quantity - 1)}
                disabled={quantity <= 1}
                className="w-10 h-10 flex items-center justify-center rounded-xl border border-slate-300 bg-white hover:bg-slate-100 text-slate-700 font-bold text-lg disabled:opacity-40 transition"
              >
                -
              </button>
              <input
                type="number"
                min="1"
                value={quantity}
                onChange={(e) => handleQuantityChange(parseInt(e.target.value) || 1)}
                className="w-32 text-center text-base font-bold px-3 py-2 border border-slate-300 rounded-xl focus:ring-2 focus:ring-amber-500 focus:outline-none bg-white text-slate-800"
                required
              />
              <button
                type="button"
                onClick={() => handleQuantityChange(quantity + 1)}
                className="w-10 h-10 flex items-center justify-center rounded-xl border border-slate-300 bg-white hover:bg-slate-100 text-slate-700 font-bold text-lg transition"
              >
                +
              </button>
              <span className="text-xs text-slate-500 font-medium">{pr.item_unit || 'Units'}</span>
            </div>

            {/* Live Inventory Breakdown */}
            {inventoryAnalysis && (
              <div className={`mt-3 p-3.5 rounded-xl border text-xs space-y-2 ${
                inventoryAnalysis.coverage_status === 'SUFFICIENT'
                  ? 'bg-emerald-50/70 border-emerald-200 text-emerald-900'
                  : 'bg-amber-50/70 border-amber-200 text-amber-900'
              }`}>
                <div className="flex items-center justify-between font-semibold">
                  <span className="flex items-center space-x-1.5">
                    <Layers className="w-4 h-4 text-slate-600" />
                    <span>Live Warehouse Stock Check:</span>
                  </span>
                  <span className="font-bold">
                    {inventoryAnalysis.available_quantity} {pr.item_unit || 'units'} available
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-[11px] pt-1 border-t border-slate-200/50">
                  <div>
                    <span className="text-slate-500 block">Available Stock:</span>
                    <span className="font-bold">{inventoryAnalysis.available_quantity} {pr.item_unit || ''}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Requested:</span>
                    <span className="font-bold">{inventoryAnalysis.requested_quantity} {pr.item_unit || ''}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Shortage:</span>
                    <span className={`font-bold ${inventoryAnalysis.shortage_quantity > 0 ? 'text-amber-700' : 'text-emerald-700'}`}>
                      {inventoryAnalysis.shortage_quantity > 0 ? `${inventoryAnalysis.shortage_quantity} ${pr.item_unit || ''}` : '0 (None)'}
                    </span>
                  </div>
                </div>
                <p className="text-[11px] pt-1 text-slate-600">
                  {inventoryAnalysis.coverage_status === 'SUFFICIENT'
                    ? 'Sufficient internal inventory exists in warehouse reserves. You can adjust the quantity or proceed with external procurement.'
                    : `Current warehouse stock cannot satisfy this quantity (shortage of ${inventoryAnalysis.shortage_quantity} ${pr.item_unit || 'units'}). External procurement is needed.`}
                </p>
              </div>
            )}
          </div>

          {/* Vendor Selection */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 flex items-center space-x-1.5">
              <Building className="w-4 h-4 text-slate-500" />
              <span>Preferred Vendor / Supplier</span>
            </label>
            <select
              value={selectedVendorId}
              onChange={(e) => setSelectedVendorId(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-xl text-xs font-medium text-slate-800 focus:ring-2 focus:ring-amber-500 focus:outline-none"
              required
            >
              <option value="" disabled>Select a vendor...</option>
              {vendors.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name} — {v.email}
                </option>
              ))}
            </select>
          </div>

          {/* Requester Revision Notes */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 flex items-center justify-between">
              <span>Requester Revision Notes & Explanation</span>
              <span className="text-[10px] text-slate-400 font-normal">Optional</span>
            </label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Explain the changes made (e.g., 'Reduced quantity to 5 units as requested by supervisor and updated supplier')..."
              className="w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:ring-2 focus:ring-amber-500 focus:outline-none resize-none"
            />
          </div>
        </form>

        {/* Footer Actions */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-200 rounded-xl transition disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading || quantity <= 0}
            className="px-5 py-2.5 bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-700 hover:to-orange-700 text-white text-xs font-bold rounded-xl shadow-md shadow-amber-600/20 hover:shadow-lg transition flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <RotateCcw className="w-4 h-4 animate-spin" />
                <span>Resubmitting...</span>
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                <span>Resubmit to Supervisor</span>
              </>
            )}
          </button>
        </div>

      </div>
    </div>
  );
}
