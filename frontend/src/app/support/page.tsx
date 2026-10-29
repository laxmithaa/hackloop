"use client";

import React, { useState } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import DemoNotice from "@/components/DemoNotice";
import StatusBadge, { BadgeVariant } from "@/components/StatusBadge";
import { useLanguage } from "@/lib/context/LanguageContext";
import {
  Users,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  PhoneCall,
  FileText,
  AlertCircle,
  Plus,
  Building2,
  ShieldCheck,
  Calendar,
  MessageSquare,
} from "lucide-react";
import { INITIAL_SUPPORT_TICKETS } from "@/lib/services/mockData";
import type { SupportTicket, TicketStatus } from "@/lib/types/billing";

export default function SupportWorkerDashboard() {
  const { t, lang } = useLanguage();

  const [tickets, setTickets] = useState<SupportTicket[]>(INITIAL_SUPPORT_TICKETS);
  const [selectedTicketId, setSelectedTicketId] = useState<string>(INITIAL_SUPPORT_TICKETS[0].ticketId);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("All");
  const [newNote, setNewNote] = useState("");

  const activeTicket = tickets.find((t) => t.ticketId === selectedTicketId) || tickets[0];

  const filteredTickets = tickets.filter((ticket) => {
    const matchesSearch =
      ticket.patientName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ticket.billNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ticket.referenceId.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ticket.ticketId.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus = statusFilter === "All" || ticket.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const handleStatusChange = (newStatus: TicketStatus) => {
    setTickets((prev) =>
      prev.map((item) =>
        item.ticketId === activeTicket.ticketId
          ? {
              ...item,
              status: newStatus,
              staffNotes: [
                ...(item.staffNotes || []),
                `Status updated to "${newStatus}" by Support Worker at ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`,
              ],
            }
          : item
      )
    );
  };

  const handleAddNote = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNote.trim()) return;

    setTickets((prev) =>
      prev.map((item) =>
        item.ticketId === activeTicket.ticketId
          ? {
              ...item,
              staffNotes: [
                ...(item.staffNotes || []),
                `${newNote.trim()} (${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })})`,
              ],
            }
          : item
      )
    );
    setNewNote("");
  };

  const getStatusVariant = (status: TicketStatus): BadgeVariant => {
    switch (status) {
      case "New":
        return "info";
      case "Callback scheduled":
        return "warning";
      case "Contacted":
        return "neutral";
      case "Resolved":
        return "success";
      default:
        return "neutral";
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#f8fafc]">
      <DemoNotice />
      <Navbar />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 md:py-12">
        {/* Top Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-900 border border-amber-300">
                {t.supportDashboard.demoBadge}
              </span>
              <span className="text-xs text-slate-500">Authorized Worker Portal</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
              {t.supportDashboard.title}
            </h1>
            <p className="text-sm text-slate-600 mt-0.5">
              {t.supportDashboard.subtitle}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-500">Hospital:</span>
            <span className="text-xs font-bold text-slate-800 bg-white px-3 py-1.5 rounded-xl border border-slate-200 shadow-sm">
              Sunrise Community Hospital (ID: HOSP-SUNRISE-01)
            </span>
          </div>
        </div>

        {/* ── Search & Filter Controls ── */}
        <div className="bg-white rounded-2xl border border-slate-200 p-4 mb-6 flex flex-col md:flex-row items-center justify-between gap-4 shadow-sm">
          {/* Search Box */}
          <div className="relative w-full md:w-96">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t.supportDashboard.searchPlaceholder}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-300 text-sm placeholder-slate-400 focus-visible:ring-4 focus-visible:ring-blue-600/20"
            />
          </div>

          {/* Status Filter Buttons */}
          <div className="flex flex-wrap items-center gap-1.5 w-full md:w-auto">
            {["All", "New", "Callback scheduled", "Contacted", "Resolved"].map((status) => (
              <button
                key={status}
                type="button"
                onClick={() => setStatusFilter(status)}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold border transition-colors ${
                  statusFilter === status
                    ? "bg-slate-900 text-white border-slate-900 shadow-sm"
                    : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                }`}
              >
                {status === "All" ? t.supportDashboard.filterAll : status}
              </button>
            ))}
          </div>
        </div>

        {/* ── 2-Column Dashboard Layout: Ticket List & Details Panel ── */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Ticket List (5 cols) */}
          <div className="lg:col-span-5 space-y-3">
            <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-slate-500 px-1">
              <span>{t.supportDashboard.ticketListHeading}</span>
              <span>{filteredTickets.length} cases</span>
            </div>

            {filteredTickets.length === 0 ? (
              <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-slate-500 text-sm">
                {t.supportDashboard.noTickets}
              </div>
            ) : (
              <div className="space-y-2.5 max-h-[640px] overflow-y-auto pr-1">
                {filteredTickets.map((ticket) => {
                  const isSelected = activeTicket && activeTicket.ticketId === ticket.ticketId;
                  return (
                    <div
                      key={ticket.ticketId}
                      onClick={() => setSelectedTicketId(ticket.ticketId)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          setSelectedTicketId(ticket.ticketId);
                        }
                      }}
                      tabIndex={0}
                      role="button"
                      aria-pressed={isSelected}
                      className={`p-4 rounded-2xl border text-left transition-all cursor-pointer ${
                        isSelected
                          ? "bg-blue-50/80 border-blue-400 shadow-sm ring-2 ring-blue-600/20"
                          : "bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <span className="text-xs font-mono font-bold text-slate-500">
                          {ticket.ticketId} · {ticket.referenceId}
                        </span>
                        <StatusBadge
                          variant={getStatusVariant(ticket.status)}
                          label={ticket.status}
                          size="sm"
                        />
                      </div>

                      <div className="font-extrabold text-slate-900 text-sm sm:text-base">
                        {ticket.patientName}
                      </div>

                      <div className="text-xs text-slate-500 mt-0.5">
                        Bill #{ticket.billNumber} · {ticket.hospitalName}
                      </div>

                      <p className="text-xs text-slate-700 mt-2 line-clamp-2 leading-relaxed">
                        {ticket.patientNote}
                      </p>

                      <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500 font-medium">
                        <span>Window: {ticket.preferredCallbackTime}</span>
                        <span>{ticket.createdAt}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Right Column: Active Ticket Details Panel (7 cols) */}
          <div className="lg:col-span-7">
            {activeTicket ? (
              <div className="bg-white rounded-3xl border border-slate-200/80 shadow-sm p-6 sm:p-8 space-y-6">
                {/* Details Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-slate-200">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-xs font-bold text-slate-500">
                        {activeTicket.ticketId}
                      </span>
                      <StatusBadge
                        variant={getStatusVariant(activeTicket.status)}
                        label={activeTicket.status}
                      />
                    </div>
                    <h2 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
                      {activeTicket.patientName}
                    </h2>
                    <div className="text-xs text-slate-500 font-mono mt-0.5">
                      Case Reference: {activeTicket.referenceId}
                    </div>
                  </div>

                  {/* Status Action Buttons */}
                  <div className="space-y-1.5">
                    <span className="text-xs font-bold text-slate-500 block">
                      {t.supportDashboard.changeStatusBtn}:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {(["New", "Callback scheduled", "Contacted", "Resolved"] as TicketStatus[]).map(
                        (st) => (
                          <button
                            key={st}
                            type="button"
                            onClick={() => handleStatusChange(st)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-colors ${
                              activeTicket.status === st
                                ? "bg-blue-700 text-white border-blue-700"
                                : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                            }`}
                          >
                            {st}
                          </button>
                        )
                      )}
                    </div>
                  </div>
                </div>

                {/* Case Info Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 bg-slate-50 rounded-2xl border border-slate-200 text-xs sm:text-sm">
                  <div>
                    <span className="text-slate-500 block">
                      {t.supportDashboard.patientContactLabel}
                    </span>
                    <strong className="text-slate-900 font-mono">
                      {activeTicket.contactNumber}
                    </strong>
                  </div>

                  <div>
                    <span className="text-slate-500 block">
                      {t.supportDashboard.preferredLangLabel}
                    </span>
                    <strong className="text-slate-900 uppercase">
                      {activeTicket.preferredLanguage}
                    </strong>
                  </div>

                  <div>
                    <span className="text-slate-500 block">
                      {t.supportDashboard.callbackWindowLabel}
                    </span>
                    <strong className="text-slate-900 capitalize">
                      {activeTicket.preferredCallbackTime}
                    </strong>
                  </div>

                  <div>
                    <span className="text-slate-500 block">Consent Verified:</span>
                    <span className="inline-flex items-center gap-1 font-bold text-emerald-700">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Yes
                    </span>
                  </div>
                </div>

                {/* Patient's Stated Reason */}
                <div className="p-4 rounded-2xl border border-slate-200 bg-white space-y-1.5">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block">
                    Reason for Requesting Help:
                  </span>
                  <p className="text-sm sm:text-base text-slate-800 leading-relaxed font-medium">
                    &ldquo;{activeTicket.patientNote}&rdquo;
                  </p>
                </div>

                {/* Staff Case Notes Audit Trail */}
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1.5">
                    <MessageSquare className="w-4 h-4 text-blue-700" />
                    <span>Internal Staff Case Notes</span>
                  </h3>

                  <div className="space-y-2 mb-4">
                    {activeTicket.staffNotes && activeTicket.staffNotes.length > 0 ? (
                      activeTicket.staffNotes.map((note, idx) => (
                        <div
                          key={idx}
                          className="p-3 bg-slate-50 rounded-xl text-xs text-slate-700 border border-slate-200"
                        >
                          {note}
                        </div>
                      ))
                    ) : (
                      <div className="text-xs text-slate-400 italic p-3">No staff notes yet.</div>
                    )}
                  </div>

                  {/* Add Note Form */}
                  <form onSubmit={handleAddNote} className="flex gap-2">
                    <input
                      type="text"
                      value={newNote}
                      onChange={(e) => setNewNote(e.target.value)}
                      placeholder={t.supportDashboard.addNotePlaceholder}
                      className="flex-1 px-4 py-2.5 rounded-xl border border-slate-300 text-xs sm:text-sm text-slate-900 placeholder-slate-400 focus-visible:ring-4 focus-visible:ring-blue-600/20"
                    />
                    <button
                      type="submit"
                      disabled={!newNote.trim()}
                      className="inline-flex items-center gap-1.5 px-4 py-2.5 bg-blue-700 hover:bg-blue-800 disabled:opacity-50 text-white font-bold rounded-xl text-xs sm:text-sm transition-colors"
                    >
                      <Plus className="w-4 h-4" />
                      <span>{t.supportDashboard.addNoteBtn}</span>
                    </button>
                  </form>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-3xl border border-slate-200 p-12 text-center text-slate-500">
                Select a ticket to review details.
              </div>
            )}
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
