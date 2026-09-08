'use client';

import React, { useState, useEffect } from 'react';
import { RFQ } from '../lib/types';
import { api } from '../lib/api';
import { Send, Calendar, Clock, DollarSign, X, CheckCircle2, AlertCircle } from 'lucide-react';

interface SubmitQuotationModalProps {
  isOpen: boolean;
  rfq: RFQ | null;
  onClose: () => void;
  onSuccess: () => void;
}

export const SubmitQuotationModal: React.FC<SubmitQuotationModalProps> = ({
  isOpen,
  rfq,
  onClose,
  onSuccess,
}) => {
  const [unitPrice, setUnitPrice] = useState<number>(100);
  const [leadTime, setLeadTime] = useState<number>(7);
  const [deliveryDate, setDeliveryDate] = useState<string>(() => {
    const d = new Date();
    d.setDate(d.getDate() + 7);
    return d.toISOString().split('T')[0];
  });
  const [validity, setValidity] = useState<string>('30 Days');
  const [notes, setNotes] = useState<string>('Standard commercial delivery terms apply.');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (rfq) {
      setUnitPrice(100);
      setLeadTime(7);
      const d = new Date();
      d.setDate(d.getDate() + 7);
      setDeliveryDate(d.toISOString().split('T')[0]);
      setValidity('30 Days');
      setNotes('Standard commercial delivery terms apply.');
      setErrorMessage(null);
    }
  }, [rfq]);

  if (!isOpen || !rfq) return null;

  const handleLeadTimeChange = (days: number) => {
    const val = Math.max(1, days);
    setLeadTime(val);
    const d = new Date();
    d.setDate(d.getDate() + val);
    setDeliveryDate(d.toISOString().split('T')[0]);
  };

  const handleSubmitQuote = async () => {
    if (unitPrice <= 0 || leadTime <= 0) {
      setErrorMessage('Please enter a valid unit price and lead time.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await api.submitQuotation(rfq.id, {
        quoted_unit_price: unitPrice,
        lead_time_days: leadTime,
        expected_delivery_date: deliveryDate,
        validity_period: validity,
        notes,
      });
      onSuccess();
      onClose();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to submit quotation.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const totalPrice = unitPrice * (rfq.quantity || 1);

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-sm text-slate-900">Submit Quotation</span>
              <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-[10px] font-bold rounded">
                {rfq.reference_number}
              </span>
            </div>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Ref PR: <span className="font-semibold text-slate-700">{rfq.pr_reference}</span> • Requested: {rfq.quantity} {rfq.item_unit} of {rfq.item_name}
            </p>
          </div>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-200 transition">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <div className="p-6 space-y-4 text-xs">
          {errorMessage && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Pricing & Summary Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                Quoted Unit Price ($)
              </label>
              <div className="relative">
                <span className="absolute left-3 top-2.5 text-slate-400 font-bold">$</span>
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={unitPrice}
                  onChange={e => setUnitPrice(parseFloat(e.target.value) || 0)}
                  className="w-full pl-7 pr-3 py-2 border border-slate-300 rounded-xl font-bold text-slate-900 text-sm focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                Total Quoted Amount
              </label>
              <div className="p-2 bg-slate-50 rounded-xl border border-slate-200 text-slate-900 font-black text-sm flex items-center justify-between">
                <span>Total:</span>
                <span className="text-emerald-700">${totalPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
              </div>
            </div>
          </div>

          {/* Lead time & Committed Delivery Date */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                Standard Lead Time (Days)
              </label>
              <input
                type="number"
                min="1"
                value={leadTime}
                onChange={e => handleLeadTimeChange(parseInt(e.target.value) || 1)}
                className="w-full p-2 border border-slate-300 rounded-xl font-bold text-slate-900 text-xs focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-[10px] text-slate-400 block">
                Standard dispatch: {(() => {
                  const d = new Date();
                  d.setDate(d.getDate() + leadTime);
                  return d.toLocaleDateString();
                })()}
              </span>
            </div>

            <div className="space-y-1">
              <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px] flex items-center space-x-1">
                <Calendar className="w-3 h-3 text-purple-600" />
                <span className="text-purple-900">Committed Delivery Date</span>
              </label>
              <input
                type="date"
                value={deliveryDate}
                onChange={e => setDeliveryDate(e.target.value)}
                className="w-full p-2 border-2 border-purple-300 rounded-xl font-bold text-slate-900 text-xs focus:ring-2 focus:ring-purple-500 bg-purple-50/30"
              />
              <span className="text-[10px] text-purple-700 block font-medium">
                ⚡ Earliest delivery gives higher analytical score.
              </span>
            </div>
          </div>

          {/* Validity & Terms */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Quote Validity Period</label>
              <select
                value={validity}
                onChange={e => setValidity(e.target.value)}
                className="w-full p-2 border border-slate-300 rounded-xl font-medium text-slate-800 text-xs focus:ring-2 focus:ring-blue-500"
              >
                <option value="15 Days">15 Days</option>
                <option value="30 Days">30 Days (Standard)</option>
                <option value="45 Days">45 Days</option>
                <option value="60 Days">60 Days</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Required Quantity</label>
              <div className="p-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-700 font-semibold text-xs">
                {rfq.quantity} {rfq.item_unit}
              </div>
            </div>
          </div>

          {/* Commercial Notes */}
          <div className="space-y-1">
            <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Commercial Terms & Warranty Notes</label>
            <textarea
              rows={2}
              value={notes}
              onChange={e => setNotes(e.target.value)}
              className="w-full p-2 border border-slate-300 rounded-xl text-slate-800 text-xs focus:ring-2 focus:ring-blue-500"
              placeholder="Specify warranty, payment terms, or delivery conditions..."
            />
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-end space-x-2">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-slate-200 text-slate-600 hover:bg-slate-100 rounded-xl font-bold text-xs transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmitQuote}
            disabled={isSubmitting || unitPrice <= 0}
            className="px-5 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-xl font-bold text-xs transition flex items-center space-x-1.5 shadow-md shadow-blue-500/20"
          >
            <Send className="w-3.5 h-3.5" />
            <span>{isSubmitting ? 'Submitting Quote...' : 'Submit Commercial Quotation'}</span>
          </button>
        </div>

      </div>
    </div>
  );
};
