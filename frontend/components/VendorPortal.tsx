'use client';

import React, { useState } from 'react';
import { RFQ } from '../lib/types';
import { api } from '../lib/api';
import { Send, Clock, DollarSign, CheckCircle2, AlertCircle, X, Calendar, AlertTriangle } from 'lucide-react';

interface VendorPortalProps {
  rfqs: RFQ[];
  onRefresh: () => void;
}

export const VendorPortal: React.FC<VendorPortalProps> = ({ rfqs, onRefresh }) => {
  const [selectedRfq, setSelectedRfq] = useState<RFQ | null>(null);
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
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const handleOpenModal = (rfq: RFQ) => {
    setSelectedRfq(rfq);
    setUnitPrice(100);
    setLeadTime(7);
    const d = new Date();
    d.setDate(d.getDate() + 7);
    setDeliveryDate(d.toISOString().split('T')[0]);
  };

  const handleLeadTimeChange = (days: number) => {
    const val = Math.max(1, days);
    setLeadTime(val);
    const d = new Date();
    d.setDate(d.getDate() + val);
    setDeliveryDate(d.toISOString().split('T')[0]);
  };

  const handleSubmitQuote = async () => {
    if (!selectedRfq || unitPrice <= 0 || leadTime <= 0) return;

    setIsSubmitting(true);
    setStatusMessage(null);
    try {
      await api.submitQuotation(selectedRfq.id, {
        quoted_unit_price: unitPrice,
        lead_time_days: leadTime,
        expected_delivery_date: deliveryDate,
        validity_period: validity,
        notes,
      });
      setStatusMessage(`Quotation submitted successfully for ${selectedRfq.reference_number}!`);
      setSelectedRfq(null);
      onRefresh();
    } catch (err: any) {
      setStatusMessage(err.message || 'Failed to submit quotation.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const isExpired = (rfq: RFQ) => {
    if (rfq.status === 'RFQ_EXPIRED') return true;
    if (rfq.due_at && !rfq.has_quotation && new Date(rfq.due_at) < new Date()) return true;
    return false;
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-4">
          <div>
            <h2 className="text-base font-bold text-slate-900">Vendor Bidding & Quotation Portal</h2>
            <p className="text-xs text-slate-500">
              View competitive RFQs assigned to your vendor account and submit formal commercial quotations with committed delivery dates.
            </p>
          </div>
          <span className="px-3 py-1 bg-amber-50 text-amber-800 border border-amber-200 rounded-full text-xs font-bold">
            {rfqs.length} Assigned RFQ(s)
          </span>
        </div>

        {statusMessage && (
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-xl text-xs text-blue-800 flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-blue-600" />
            <span>{statusMessage}</span>
          </div>
        )}

        {rfqs.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-xs">
            No RFQs currently assigned to your vendor organization.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {rfqs.map((rfq) => {
              const expired = isExpired(rfq);
              return (
                <div
                  key={rfq.id}
                  className={`p-4 rounded-xl border transition shadow-sm flex flex-col justify-between ${
                    expired ? 'border-rose-200 bg-rose-50/20' : 'border-slate-200 bg-white hover:border-slate-300'
                  }`}
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="font-bold text-sm text-slate-900">{rfq.reference_number}</span>
                        <div className="text-xs text-slate-400">Ref: {rfq.pr_reference}</div>
                      </div>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                        rfq.has_quotation
                          ? 'bg-emerald-100 text-emerald-800 border-emerald-200'
                          : expired
                          ? 'bg-rose-100 text-rose-800 border-rose-200'
                          : 'bg-blue-100 text-blue-800 border-blue-200'
                      }`}>
                        {rfq.has_quotation ? 'Quote Submitted' : expired ? 'RFQ Expired' : 'Action Required'}
                      </span>
                    </div>

                    <div className="p-3 bg-slate-50 rounded-lg space-y-1.5 text-xs">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Item:</span>
                        <span className="font-bold text-slate-800">{rfq.item_name}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Quantity Required:</span>
                        <span className="font-bold text-slate-800">{rfq.quantity} {rfq.item_unit}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Issued On:</span>
                        <span className="text-slate-700">{new Date(rfq.issued_at).toLocaleDateString()}</span>
                      </div>
                      {rfq.due_at && (
                        <div className="flex justify-between items-center pt-1 border-t border-slate-200/60">
                          <span className="text-slate-500 flex items-center space-x-1">
                            <Clock className="w-3 h-3 text-slate-400" />
                            <span>Submission Deadline:</span>
                          </span>
                          <span className={`font-bold ${expired && !rfq.has_quotation ? 'text-rose-600' : 'text-slate-800'}`}>
                            {new Date(rfq.due_at).toLocaleDateString()} ({new Date(rfq.due_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="pt-3 mt-2 border-t border-slate-100 flex justify-end">
                    {rfq.has_quotation ? (
                      <button
                        disabled
                        className="px-3.5 py-2 bg-slate-100 border border-slate-200 text-slate-500 text-xs font-bold rounded-xl flex items-center space-x-1.5 cursor-not-allowed shadow-none"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        <span>Quote Submitted (Locked)</span>
                      </button>
                    ) : expired ? (
                      <button
                        disabled
                        className="px-3.5 py-2 bg-rose-50 border border-rose-200 text-rose-500 text-xs font-bold rounded-xl flex items-center space-x-1.5 cursor-not-allowed shadow-none"
                      >
                        <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />
                        <span>Deadline Passed (Closed)</span>
                      </button>
                    ) : (
                      <button
                        onClick={() => handleOpenModal(rfq)}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl transition flex items-center space-x-1.5 shadow-sm"
                      >
                        <Send className="w-3.5 h-3.5" />
                        <span>Submit Formal Quote</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Quotation Submission Modal */}
      {selectedRfq && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <div>
                <h3 className="font-bold text-sm text-slate-900">Submit Quotation: {selectedRfq.reference_number}</h3>
                <p className="text-[11px] text-slate-500">{selectedRfq.quantity} {selectedRfq.item_unit} of {selectedRfq.item_name}</p>
              </div>
              <button onClick={() => setSelectedRfq(null)} className="p-1 text-slate-400 hover:text-slate-700">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-6 space-y-4 text-xs">
              <div className="space-y-1">
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Quoted Unit Price ($)</label>
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={unitPrice}
                  onChange={e => setUnitPrice(parseFloat(e.target.value) || 0)}
                  className="w-full p-2.5 border border-slate-300 rounded-xl font-bold text-slate-900 text-sm focus:ring-2 focus:ring-blue-500"
                />
              </div>

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
                    className="w-full p-2.5 border border-slate-300 rounded-xl font-bold text-slate-900 text-sm focus:ring-2 focus:ring-blue-500"
                  />
                  <span className="text-[10px] text-slate-400 block">
                    Calculated standard: {(() => {
                      const d = new Date();
                      d.setDate(d.getDate() + leadTime);
                      return d.toLocaleDateString();
                    })()}
                  </span>
                </div>

                <div className="space-y-1">
                  <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px] flex items-center space-x-1">
                    <Calendar className="w-3 h-3 text-purple-600" />
                    <span className="text-purple-900">Vendor Committed Delivery Date</span>
                  </label>
                  <input
                    type="date"
                    value={deliveryDate}
                    onChange={e => setDeliveryDate(e.target.value)}
                    className="w-full p-2.5 border-2 border-purple-300 rounded-xl font-bold text-slate-900 text-xs focus:ring-2 focus:ring-purple-500 bg-purple-50/20"
                  />
                  <span className="text-[10px] text-purple-700 block font-medium">
                    ⚡ Specify your confirmed delivery date (earlier dates boost score).
                  </span>
                </div>
              </div>

              <div className="space-y-1">
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Quote Validity</label>
                <input
                  type="text"
                  value={validity}
                  onChange={e => setValidity(e.target.value)}
                  className="w-full p-2.5 border border-slate-300 rounded-xl"
                />
              </div>

              <div className="space-y-1">
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Terms & Delivery Notes</label>
                <textarea
                  rows={2}
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                  className="w-full p-2.5 border border-slate-300 rounded-xl"
                />
              </div>

              <div className="p-3 bg-blue-50 rounded-xl border border-blue-100 flex justify-between items-center">
                <span className="text-slate-600 font-medium">Total Contract Value:</span>
                <span className="font-black text-blue-900 text-sm">
                  ${(unitPrice * selectedRfq.quantity).toLocaleString()}
                </span>
              </div>
            </div>

            <div className="px-6 py-3 bg-slate-50 border-t border-slate-100 flex justify-end space-x-2">
              <button
                onClick={() => setSelectedRfq(null)}
                className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-200 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitQuote}
                disabled={isSubmitting}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl shadow-md transition disabled:opacity-50"
              >
                {isSubmitting ? 'Submitting...' : 'Confirm Quotation'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
