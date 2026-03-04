"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { ReportSummary, ReviewItem } from "@/types/types";
import { useRouter } from "next/navigation";

/* ── Confidence badge ─────────────────────────────────────────── */

function ConfidenceBadge({
  confidence,
  reviewStatus,
}: {
  confidence?: number | null;
  reviewStatus?: string;
}) {
  if (reviewStatus === "accepted") {
    return (
      <span className="px-2 py-0.5 bg-green-500/20 border border-green-400/30 rounded-md text-green-300 text-xs font-medium">
        {confidence != null ? `${Math.round(confidence * 100)}%` : "Accepted"}
      </span>
    );
  }
  if (reviewStatus === "rejected") {
    return (
      <span className="px-2 py-0.5 bg-red-500/20 border border-red-400/30 rounded-md text-red-300 text-xs font-medium">
        Rejected
      </span>
    );
  }
  if (confidence != null && confidence >= 0.85) {
    return (
      <span className="px-2 py-0.5 bg-green-500/20 border border-green-400/30 rounded-md text-green-300 text-xs font-medium">
        {Math.round(confidence * 100)}%
      </span>
    );
  }
  if (confidence != null) {
    return (
      <span className="px-2 py-0.5 bg-amber-500/20 border border-amber-400/30 rounded-md text-amber-300 text-xs font-medium">
        {Math.round(confidence * 100)}% — Review
      </span>
    );
  }
  return (
    <span className="px-2 py-0.5 bg-amber-500/20 border border-amber-400/30 rounded-md text-amber-300 text-xs font-medium">
      Pending
    </span>
  );
}

/* ── Review card ──────────────────────────────────────────────── */

function ReviewCard({
  item,
  reportId,
  onReviewed,
}: {
  item: ReviewItem;
  reportId: string;
  onReviewed: (linkId: number, newStatus: string, newCode?: string) => void;
}) {
  const [editMode, setEditMode] = useState(false);
  const [codeInput, setCodeInput] = useState(item.code ?? "");
  const [saving, setSaving] = useState(false);

  const patch = useCallback(
    async (action: "accept" | "reject" | "update") => {
      if (item.link_id == null) return;
      setSaving(true);
      try {
        const body: Record<string, unknown> = { action };
        if (action === "update") {
          body.code = codeInput.trim() || undefined;
        }
        const res = await fetch(
          `/api/review/by-report/${reportId}/${item.entity_type}/${item.link_id}`,
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          }
        );
        if (!res.ok) throw new Error(await res.text());
        const updated: ReviewItem = await res.json();
        onReviewed(
          item.link_id,
          updated.review_status,
          updated.code ?? undefined
        );
      } catch (e) {
        console.error("Review PATCH failed:", e);
      } finally {
        setSaving(false);
        setEditMode(false);
      }
    },
    [item, reportId, codeInput, onReviewed]
  );

  const entityLabel =
    item.entity_type === "medication"
      ? "Medication"
      : item.entity_type === "disease"
      ? "Disease / Condition"
      : "Procedure";

  const entityColor =
    item.entity_type === "medication"
      ? "from-slate-600 to-slate-700"
      : item.entity_type === "disease"
      ? "from-amber-700/60 to-amber-800/60"
      : "from-purple-700/60 to-purple-800/60";

  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl p-5 space-y-3">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={`px-2 py-0.5 rounded-md text-white text-xs font-semibold bg-gradient-to-r ${entityColor}`}
          >
            {entityLabel}
          </span>
          <h4 className="font-bold text-white text-base">{item.name}</h4>
          {/* Assigned billing code */}
          {item.entity_type === "medication" ? (
            item.cui ? (
              <span
                className="px-2 py-0.5 bg-slate-500/20 border border-slate-400/30 rounded-md text-slate-300 text-xs font-mono"
                title="UMLS Concept Identifier"
              >
                CUI: {item.cui}
              </span>
            ) : (
              <span className="px-2 py-0.5 bg-white/5 border border-white/10 rounded-md text-white/30 text-xs italic">
                No code yet
              </span>
            )
          ) : item.code ? (
            <span className="px-2 py-0.5 bg-blue-500/20 border border-blue-400/30 rounded-md text-blue-300 text-xs font-mono">
              {item.entity_type === "procedure" ? `CPT ${item.code}` : item.code}
            </span>
          ) : (
            <span className="px-2 py-0.5 bg-amber-500/10 border border-amber-400/20 rounded-md text-amber-400/60 text-xs italic animate-pulse">
              No code yet
            </span>
          )}
          <ConfidenceBadge
            confidence={item.confidence}
            reviewStatus={item.review_status}
          />
        </div>
      </div>

      {/* Code candidates */}
      {item.candidates && item.candidates.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs text-white/50 font-medium uppercase tracking-wide">
            Top candidates
          </p>
          <div className="flex flex-wrap gap-2">
            {item.candidates.slice(0, 5).map((c, i) => (
              <button
                key={i}
                onClick={() => {
                  setCodeInput(c.code);
                  setEditMode(true);
                }}
                className="px-2.5 py-1 bg-white/10 hover:bg-white/20 border border-white/10 hover:border-white/20 rounded-lg text-xs text-white/80 hover:text-white transition-all duration-150"
                title={c.description ?? c.code}
              >
                {c.code}
                {c.description ? (
                  <span className="ml-1 text-white/50">
                    — {c.description.slice(0, 30)}
                    {c.description.length > 30 ? "…" : ""}
                  </span>
                ) : null}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Edit mode */}
      {editMode && (
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={codeInput}
            onChange={(e) => setCodeInput(e.target.value)}
            placeholder="Enter code (ICD-10 / CPT / CUI)"
            className="flex-1 bg-black/40 border border-white/20 rounded-lg px-3 py-1.5 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-white/40"
          />
          <button
            onClick={() => patch("update")}
            disabled={saving}
            className="px-3 py-1.5 bg-green-600/80 hover:bg-green-500/80 rounded-lg text-xs font-semibold text-white transition-all disabled:opacity-50"
          >
            Confirm
          </button>
          <button
            onClick={() => setEditMode(false)}
            disabled={saving}
            className="px-3 py-1.5 bg-white/10 hover:bg-white/20 rounded-lg text-xs font-semibold text-white transition-all disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Action buttons */}
      {!editMode && (
        <div className="flex items-center gap-2 pt-1">
          <button
            onClick={() => patch("accept")}
            disabled={saving}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600/70 hover:bg-green-500/70 rounded-lg text-xs font-semibold text-white transition-all disabled:opacity-40"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-3.5 w-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M5 13l4 4L19 7"
              />
            </svg>
            Accept
          </button>
          <button
            onClick={() => setEditMode(true)}
            disabled={saving}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600/70 hover:bg-blue-500/70 rounded-lg text-xs font-semibold text-white transition-all disabled:opacity-40"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-3.5 w-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
              />
            </svg>
            Edit code
          </button>
          <button
            onClick={() => patch("reject")}
            disabled={saving}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600/60 hover:bg-red-500/60 rounded-lg text-xs font-semibold text-white transition-all disabled:opacity-40"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-3.5 w-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
            Reject
          </button>
        </div>
      )}
    </div>
  );
}

/* ── Main modal ───────────────────────────────────────────────── */

interface ModalProps {
  open: boolean;
  onClose: () => void;
  contents: ReportSummary[];
}

type ReviewStatuses = Record<number, { status: string; code?: string }>;
type EntityType = ReviewItem["entity_type"];

const ReportModal: React.FC<ModalProps> = ({ open, onClose, contents }) => {
  const [currentPage, setCurrentPage] = useState(0);
  const [isCreating, setIsCreating] = useState(false);
  const [view, setView] = useState<"summary" | "review">("summary");
  const [reviewQueue, setReviewQueue] = useState<ReviewItem[]>([]);
  const [reviewStatuses, setReviewStatuses] = useState<ReviewStatuses>({});
  const [loadingQueue, setLoadingQueue] = useState(false);
  const [bulkSaving, setBulkSaving] = useState<Record<string, boolean>>({});
  const [recentlyReviewed, setRecentlyReviewed] = useState<Set<number>>(new Set());
  const router = useRouter();

  const reloadReviewQueue = useCallback(
    async (reportId: string, showLoading = true) => {
      if (showLoading) {
        setLoadingQueue(true);
      }
      try {
        const res = await fetch(`/api/review/by-report/${reportId}`);
        const payload = await res.json().catch(() => null);

        if (!res.ok) {
          console.error("Failed to load report review queue", payload);
          setReviewQueue([]);
          setReviewStatuses({});
          return;
        }

        const items: ReviewItem[] = Array.isArray(payload) ? payload : [];
        if (!Array.isArray(payload)) {
          console.error("Unexpected review queue response shape", payload);
        }

        setReviewQueue(items);
        const init: ReviewStatuses = {};
        items.forEach((i) => {
          if (i.link_id != null) {
            init[i.link_id] = {
              status: i.review_status,
              code: i.code ?? undefined,
            };
          }
        });
        setReviewStatuses(init);
      } catch (error) {
        console.error("Failed to load report review queue", error);
        setReviewQueue([]);
        setReviewStatuses({});
      } finally {
        if (showLoading) {
          setLoadingQueue(false);
        }
      }
    },
    []
  );

  // True once every extracted entity has had confidence written by the coding agent.
  // confidence is always written by the agent (even when no code is found), so it
  // is the reliable "coding complete" signal — drug classes start with confidence=0.5
  // but other entities start with null until the agent runs.
  const allCoded =
    reviewQueue.length === 0 ||
    reviewQueue.every((i) => i.confidence != null);

  const total = contents.length;
  const current = contents[currentPage] ?? null;

  // ── Fetch per-report review queue whenever the visible report changes ──
  useEffect(() => {
    if (!open || !current?.reportId) return;

    let cancelled = false;

    reloadReviewQueue(current.reportId, true).catch(() => {
      if (!cancelled) {
        setLoadingQueue(false);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [open, current?.reportId, reloadReviewQueue]);

  // Reset to summary view when page changes
  useEffect(() => {
    setView("summary");
    setReviewQueue([]);
    setReviewStatuses({});
  }, [currentPage]);

  // Always-on polling: runs every 5 s while the modal is open and the coding
  // agent hasn't finished writing confidence scores for all items.
  // Updates the queue on EVERY successful response so codes appear live in
  // both the review and summary tabs as soon as the agent finishes each entity.
  useEffect(() => {
    if (!open || !current?.reportId || allCoded) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/review/by-report/${current.reportId}`);
        if (!res.ok) return;
        const items: ReviewItem[] = await res.json().catch(() => null);
        if (!Array.isArray(items)) return;
        // Always refresh queue — partial code updates appear immediately.
        setReviewQueue(items);
        // Merge server state into reviewStatuses without overwriting local
        // optimistic updates (accepted/rejected by the user this session).
        setReviewStatuses((prev) => {
          const next = { ...prev };
          items.forEach((i) => {
            if (i.link_id == null) return;
            // Only back-fill if the user hasn't locally actioned this item.
            if (!prev[i.link_id]) {
              next[i.link_id] = { status: i.review_status, code: i.code ?? undefined };
            }
          });
          return next;
        });
      } catch {
        // ignore transient network errors
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [open, current?.reportId, allCoded]);

  const handleReviewed = useCallback(
    (linkId: number, newStatus: string, newCode?: string) => {
      setReviewStatuses((prev) => ({
        ...prev,
        [linkId]: { status: newStatus, code: newCode },
      }));
      // Briefly highlight the corresponding summary row
      setRecentlyReviewed((prev) => {
        const next = new Set(prev);
        next.add(linkId);
        return next;
      });
      setTimeout(() => {
        setRecentlyReviewed((prev) => {
          const next = new Set(prev);
          next.delete(linkId);
          return next;
        });
      }, 2500);
    },
    []
  );

  // Name-keyed lookup so summary tab can resolve live status/codes even
  // though entities in `contents` always have link_id=null (pre-persistence DTOs)
  const reviewQueueByName = useMemo(() => {
    const map = new Map<string, ReviewItem>();
    reviewQueue.forEach((item) =>
      map.set(`${item.entity_type}:${item.name.toLowerCase()}`, item)
    );
    return map;
  }, [reviewQueue]);

  // Items still pending (not yet actioned in this session)
  const pendingItems = reviewQueue.filter((item) => {
    if (item.link_id == null) return false;
    const local = reviewStatuses[item.link_id];
    const status = local?.status ?? item.review_status;
    return status === "pending_review";
  });

  const allDoneCount = reviewQueue.length > 0
    ? reviewQueue.filter((item) => {
        if (item.link_id == null) return true;
        const local = reviewStatuses[item.link_id];
        const status = local?.status ?? item.review_status;
        return status !== "pending_review";
      }).length
    : 0;

  const pendingByType = useMemo(
    () => ({
      medication: pendingItems.filter((item) => item.entity_type === "medication"),
      disease: pendingItems.filter((item) => item.entity_type === "disease"),
      procedure: pendingItems.filter((item) => item.entity_type === "procedure"),
    }),
    [pendingItems]
  );

  const handleBulkReview = useCallback(
    async (entityType: EntityType, action: "accept" | "reject") => {
      if (!current?.reportId) return;

      const items = pendingByType[entityType].filter((item) => item.link_id != null);
      if (items.length === 0) return;

      const key = `${entityType}:${action}`;
      setBulkSaving((prev) => ({ ...prev, [key]: true }));

      try {
        const results = await Promise.allSettled(
          items.map(async (item) => {
            const response = await fetch(
              `/api/review/by-report/${current.reportId}/${entityType}/${item.link_id}`,
              {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action }),
              }
            );
            if (!response.ok) {
              throw new Error(await response.text());
            }
            return (await response.json()) as ReviewItem;
          })
        );

        setReviewStatuses((prev) => {
          const next = { ...prev };
          results.forEach((result) => {
            if (result.status !== "fulfilled") return;
            const updated = result.value;
            if (updated.link_id == null) return;
            next[updated.link_id] = {
              status: updated.review_status,
              code: updated.code ?? undefined,
            };
          });
          return next;
        });

        const failures = results.filter((result) => result.status === "rejected");
        if (failures.length > 0) {
          console.error(`Bulk ${action} failed for ${failures.length} item(s)`, failures);
        }

        await reloadReviewQueue(current.reportId, false);
      } finally {
        setBulkSaving((prev) => ({ ...prev, [key]: false }));
      }
    },
    [current?.reportId, pendingByType, reloadReviewQueue]
  );

  if (!open || contents.length === 0) return null;

  const prev = () => setCurrentPage((p) => Math.max(p - 1, 0));
  const next = () => setCurrentPage((p) => Math.min(p + 1, total - 1));

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex justify-center items-center p-4 z-50 animate-in fade-in duration-200">
      <div className="bg-gradient-to-br from-slate-950/95 via-slate-900/95 to-slate-800/95 backdrop-blur-xl border border-white/20 rounded-3xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden">

        {/* ── Header ── */}
        <div className="relative px-6 py-5 border-b border-white/10">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 bg-gradient-to-br from-slate-700 to-slate-600 rounded-xl flex items-center justify-center flex-shrink-0">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <h2 className="text-2xl font-bold text-white truncate">{current.filename}</h2>
                  <p className="text-sm text-white/60 mt-0.5">
                    {view === "review" ? "Admin Review Queue" : "Medical Report Analysis"}
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 flex-shrink-0">
              {view === "review" && (
                <button
                  onClick={() => setView("summary")}
                  className="px-3 py-1.5 bg-white/10 hover:bg-white/20 text-white/70 hover:text-white rounded-xl text-sm font-medium transition-all duration-200 flex items-center gap-1.5"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                  </svg>
                  Summary
                </button>
              )}
              <button
                onClick={onClose}
                className="w-8 h-8 flex items-center justify-center rounded-full bg-white/10 hover:bg-white/20 text-white/70 hover:text-white transition-all duration-200"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* ── Body ── */}
        <div className="flex-grow overflow-y-auto px-6 py-6 space-y-6 scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent">

          {/* ── REVIEW VIEW ── */}
          {view === "review" && (
            <>
              {loadingQueue ? (
                <div className="flex flex-col items-center gap-4 py-16 text-white/50">
                  <svg className="animate-spin h-8 w-8 text-white/40" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <p className="text-sm">Loading review queue…</p>
                </div>
              ) : !allCoded && reviewQueue.length > 0 ? (
                <div className="flex flex-col items-center gap-5 py-16 text-center">
                  <div className="relative flex items-center justify-center w-16 h-16">
                    <div className="absolute inset-0 rounded-full border-2 border-amber-400/30 animate-ping" />
                    <div className="w-16 h-16 bg-amber-500/10 border border-amber-400/30 rounded-full flex items-center justify-center">
                      <svg className="animate-spin h-7 w-7 text-amber-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                    </div>
                  </div>
                  <div>
                    <p className="text-white font-semibold text-base">Assigning billing codes…</p>
                    <p className="text-white/50 text-sm mt-1.5 leading-relaxed">
                      The AI coding agent is processing this report.<br />
                      This usually takes under 30 seconds.
                    </p>
                  </div>
                  <div className="flex gap-1.5 mt-1">
                    <span className="w-2 h-2 bg-amber-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-2 h-2 bg-amber-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-2 h-2 bg-amber-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              ) : pendingItems.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center gap-4">
                  <div className="w-16 h-16 bg-green-500/20 border border-green-400/30 rounded-full flex items-center justify-center">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-white text-lg font-bold">All items reviewed!</p>
                    <p className="text-white/50 text-sm mt-1">
                      {allDoneCount} {allDoneCount === 1 ? "item" : "items"} reviewed for this report.
                    </p>
                  </div>
                  <button
                    onClick={() => setView("summary")}
                    className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-xl text-sm font-medium text-white transition-all"
                  >
                    Back to Summary
                  </button>
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-white/60 text-sm">
                      {pendingItems.length} item{pendingItems.length !== 1 ? "s" : ""} pending review
                    </p>
                    {allDoneCount > 0 && (
                      <p className="text-green-400 text-sm font-medium">
                        {allDoneCount} reviewed ✓
                      </p>
                    )}
                  </div>
                  <div className="space-y-5">
                    {([
                      { type: "medication", label: "Medications" },
                      { type: "disease", label: "Diseases" },
                      { type: "procedure", label: "Procedures" },
                    ] as const).map((section) => {
                      const sectionItems = pendingByType[section.type];
                      const acceptKey = `${section.type}:accept`;
                      const rejectKey = `${section.type}:reject`;
                      const isAccepting = bulkSaving[acceptKey] ?? false;
                      const isRejecting = bulkSaving[rejectKey] ?? false;
                      return (
                        <section
                          key={section.type}
                          className="bg-white/5 border border-white/10 rounded-2xl p-4 space-y-3"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <p className="text-white/80 text-sm font-semibold">
                              {section.label}: {sectionItems.length} pending
                            </p>
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => handleBulkReview(section.type, "accept")}
                                disabled={
                                  sectionItems.length === 0 ||
                                  isAccepting ||
                                  isRejecting
                                }
                                className="px-3 py-1.5 bg-green-600/70 hover:bg-green-500/70 rounded-lg text-xs font-semibold text-white transition-all disabled:opacity-40"
                              >
                                {isAccepting ? "Accepting…" : "Accept All"}
                              </button>
                              <button
                                onClick={() => handleBulkReview(section.type, "reject")}
                                disabled={
                                  sectionItems.length === 0 ||
                                  isAccepting ||
                                  isRejecting
                                }
                                className="px-3 py-1.5 bg-red-600/60 hover:bg-red-500/60 rounded-lg text-xs font-semibold text-white transition-all disabled:opacity-40"
                              >
                                {isRejecting ? "Rejecting…" : "Reject All"}
                              </button>
                            </div>
                          </div>

                          {sectionItems.length > 0 && (
                            <div className="space-y-4">
                              {sectionItems.map((item) => (
                                <ReviewCard
                                  key={item.link_id ?? `${item.entity_type}-${item.id}`}
                                  item={item}
                                  reportId={current.reportId!}
                                  onReviewed={handleReviewed}
                                />
                              ))}
                            </div>
                          )}
                        </section>
                      );
                    })}
                  </div>
                </>
              )}
            </>
          )}

          {/* ── SUMMARY VIEW ── */}
          {view === "summary" && (
            <>
              {/* Pending review banner */}
              {pendingItems.length > 0 && !loadingQueue && (
                <div className="bg-amber-500/10 border border-amber-400/30 rounded-2xl px-5 py-4 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-amber-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                    <p className="text-amber-300 text-sm font-medium">
                      <span className="font-bold">{pendingItems.length} {pendingItems.length === 1 ? "item" : "items"}</span>
                      {" "}need{pendingItems.length === 1 ? "s" : ""} admin review for billing codes
                    </p>
                  </div>
                  <button
                    onClick={() => setView("review")}
                    className="flex-shrink-0 px-3 py-1.5 bg-amber-500/80 hover:bg-amber-400/80 text-black font-semibold rounded-lg text-sm transition-all hover:scale-105"
                  >
                    Review now →
                  </button>
                </div>
              )}

              {/* Summary Section */}
              <section className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6 hover:bg-white/10 transition-all duration-300">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-8 h-8 bg-slate-700/30 rounded-lg flex items-center justify-center">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <h3 className="text-xl font-bold text-white">Summary</h3>
                </div>
                <p className="text-white/80 whitespace-pre-wrap leading-relaxed">{current.summary}</p>
              </section>

              {/* Medications */}
              {current.medications.length > 0 && (
                <section className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6 hover:bg-white/10 transition-all duration-300">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-8 h-8 bg-slate-700/30 rounded-lg flex items-center justify-center">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                      </svg>
                    </div>
                    <h3 className="text-xl font-bold text-white">Medications</h3>
                    <span className="ml-auto px-3 py-1 bg-slate-700/30 border border-slate-600/40 rounded-full text-slate-300 text-sm font-medium">
                      {current.medications.length}
                    </span>
                  </div>
                  <div className="grid gap-3">
                    {current.medications.map((med, idx) => {
                      const qItem = reviewQueueByName.get(`medication:${med.name.toLowerCase()}`);
                      const effectiveStatus = qItem
                        ? (reviewStatuses[qItem.link_id!]?.status ?? qItem.review_status)
                        : med.review_status;
                      const effectiveCui = qItem
                        ? (reviewStatuses[qItem.link_id!]?.code ?? qItem.cui ?? med.cui)
                        : med.cui;
                      const isRecent = qItem?.link_id != null && recentlyReviewed.has(qItem.link_id);
                      return (
                        <div
                          key={idx}
                          className={`border rounded-xl p-4 transition-all duration-500 ${
                            isRecent
                              ? "bg-green-500/10 border-green-400/40 ring-1 ring-green-400/30"
                              : "bg-white/5 border-white/10 hover:bg-white/10 hover:border-white/20"
                          }`}
                        >
                          <div className="flex items-start gap-3">
                            <div className="w-6 h-6 bg-gradient-to-br from-slate-600 to-slate-700 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                              <span className="text-white text-xs font-bold">{idx + 1}</span>
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                                <h4 className="font-bold text-white text-base">{med.name}</h4>
                                {med.is_drug_class && (
                                  <span className="px-1.5 py-0.5 bg-slate-500/30 border border-slate-400/30 rounded text-slate-300 text-xs">
                                    Drug class
                                  </span>
                                )}
                                {effectiveCui ? (
                                  <span
                                    className="px-2 py-0.5 bg-slate-500/20 border border-slate-400/30 rounded-md text-slate-300 text-xs font-mono"
                                    title="UMLS Concept Identifier"
                                  >
                                    CUI: {effectiveCui}
                                  </span>
                                ) : null}
                                <ConfidenceBadge
                                  confidence={med.confidence}
                                  reviewStatus={effectiveStatus}
                                />
                              </div>
                              <p className="text-white/60 text-sm mt-0.5">{med.purpose}</p>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </section>
              )}

              {/* Diseases */}
              {current.diseases && current.diseases.length > 0 && (
                <section className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6 hover:bg-white/10 transition-all duration-300">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-8 h-8 bg-slate-700/30 rounded-lg flex items-center justify-center">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                      </svg>
                    </div>
                    <h3 className="text-xl font-bold text-white">Diseases & Conditions</h3>
                    <span className="ml-auto px-3 py-1 bg-slate-700/30 border border-slate-600/40 rounded-full text-slate-300 text-sm font-medium">
                      {current.diseases.length}
                    </span>
                  </div>
                  <div className="grid gap-3">
                    {current.diseases.map((dis, idx) => {
                      const qItem = reviewQueueByName.get(`disease:${dis.name.toLowerCase()}`);
                      const effectiveStatus = qItem
                        ? (reviewStatuses[qItem.link_id!]?.status ?? qItem.review_status)
                        : dis.review_status;
                      const code = qItem
                        ? (reviewStatuses[qItem.link_id!]?.code ?? qItem.code ?? dis.icd10_code)
                        : dis.icd10_code;
                      return (
                        <div
                          key={idx}
                          className={`border rounded-xl p-4 transition-all duration-500 ${
                            dis.link_id != null && recentlyReviewed.has(dis.link_id)
                              ? "bg-green-500/10 border-green-400/40 ring-1 ring-green-400/30"
                              : "bg-white/5 border-white/10 hover:bg-white/10 hover:border-white/20"
                          }`}
                        >
                          <div className="flex items-start gap-3">
                            <div className="w-6 h-6 bg-gradient-to-br from-slate-600 to-slate-700 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                              <span className="text-white text-xs font-bold">{idx + 1}</span>
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                                <h4 className="font-bold text-white text-base">{dis.name}</h4>
                                {code ? (
                                  <span className="px-2 py-0.5 bg-blue-500/20 border border-blue-400/30 rounded-md text-blue-300 text-xs font-mono">
                                    {code}
                                  </span>
                                ) : (
                                  <span className="px-2 py-0.5 bg-white/5 border border-white/10 rounded-md text-white/30 text-xs italic">
                                    No ICD-10 yet
                                  </span>
                                )}
                                <ConfidenceBadge
                                  confidence={dis.confidence}
                                  reviewStatus={effectiveStatus}
                                />
                              </div>
                              <div className="flex gap-3 mt-1 text-sm text-white/50">
                                {dis.severity && <span>Severity: {dis.severity}</span>}
                                {dis.status && <span>Status: {dis.status}</span>}
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </section>
              )}

              {/* Procedures */}
              {current.procedures && current.procedures.length > 0 && (
                <section className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6 hover:bg-white/10 transition-all duration-300">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-8 h-8 bg-slate-700/30 rounded-lg flex items-center justify-center">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                      </svg>
                    </div>
                    <h3 className="text-xl font-bold text-white">Procedures</h3>
                    <span className="ml-auto px-3 py-1 bg-slate-700/30 border border-slate-600/40 rounded-full text-slate-300 text-sm font-medium">
                      {current.procedures.length}
                    </span>
                  </div>
                  <div className="grid gap-3">
                    {current.procedures.map((proc, idx) => {
                      const qItem = reviewQueueByName.get(`procedure:${proc.name.toLowerCase()}`);
                      const effectiveStatus = qItem
                        ? (reviewStatuses[qItem.link_id!]?.status ?? qItem.review_status)
                        : proc.review_status;
                      const code = qItem
                        ? (reviewStatuses[qItem.link_id!]?.code ?? qItem.code ?? proc.cpt_code)
                        : proc.cpt_code;
                      return (
                        <div
                          key={idx}
                          className={`border rounded-xl p-4 transition-all duration-500 ${
                            qItem?.link_id != null && recentlyReviewed.has(qItem.link_id)
                              ? "bg-green-500/10 border-green-400/40 ring-1 ring-green-400/30"
                              : "bg-white/5 border-white/10 hover:bg-white/10 hover:border-white/20"
                          }`}
                        >
                          <div className="flex items-start gap-3">
                            <div className="w-6 h-6 bg-gradient-to-br from-slate-600 to-slate-700 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                              <span className="text-white text-xs font-bold">{idx + 1}</span>
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                                <h4 className="font-bold text-white text-base">{proc.name}</h4>
                                {code ? (
                                  <span className="px-2 py-0.5 bg-purple-500/20 border border-purple-400/30 rounded-md text-purple-300 text-xs font-mono">
                                    CPT {code}
                                  </span>
                                ) : (
                                  <span className="px-2 py-0.5 bg-white/5 border border-white/10 rounded-md text-white/30 text-xs italic">
                                    No CPT yet
                                  </span>
                                )}
                                <ConfidenceBadge
                                  confidence={proc.confidence}
                                  reviewStatus={effectiveStatus}
                                />
                              </div>
                              <div className="flex gap-3 mt-1 text-sm text-white/50">
                                {proc.date_performed && <span>Date: {proc.date_performed}</span>}
                                {proc.body_site && <span>Site: {proc.body_site}</span>}
                                {proc.outcome && <span>Outcome: {proc.outcome}</span>}
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </section>
              )}
            </>
          )}
        </div>

        {/* ── Footer ── */}
        <div className="border-t border-white/10 bg-black/20">
          {total > 1 && (
            <div className="px-6 py-4 flex justify-between items-center border-b border-white/10">
              <button
                onClick={prev}
                disabled={currentPage === 0}
                className={`px-5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 flex items-center gap-2 ${
                  currentPage === 0
                    ? "bg-white/5 text-white/30 cursor-not-allowed"
                    : "bg-white/10 text-white hover:bg-white/20 hover:scale-105"
                }`}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                </svg>
                Previous
              </button>
              <span className="px-3 py-1 bg-gradient-to-r from-slate-700/30 to-slate-600/30 border border-white/20 rounded-full text-white font-bold text-sm">
                {currentPage + 1} / {total}
              </span>
              <button
                onClick={next}
                disabled={currentPage === total - 1}
                className={`px-5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 flex items-center gap-2 ${
                  currentPage === total - 1
                    ? "bg-white/5 text-white/30 cursor-not-allowed"
                    : "bg-white/10 text-white hover:bg-white/20 hover:scale-105"
                }`}
              >
                Next
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          )}

          <div className="px-6 py-5">
            <button
              onClick={async () => {
                if (!current.reportId) return;
                setIsCreating(true);
                try {
                  const res = await fetch("/api/conversations/from-report", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ reportId: current.reportId }),
                  });
                  if (!res.ok) throw new Error("Failed to create chat");
                  const data = await res.json();
                  onClose();
                  router.push(`/chat?id=${data.id}`);
                } catch (e) {
                  console.error(e);
                } finally {
                  setIsCreating(false);
                }
              }}
              disabled={isCreating}
              className="w-full bg-gradient-to-r from-slate-700 to-slate-600 text-white px-6 py-4 rounded-xl font-bold text-lg shadow-lg hover:shadow-2xl hover:from-slate-600 hover:to-slate-500 transition-all duration-300 flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed hover:scale-[1.02] active:scale-[0.98]"
            >
              {isCreating ? (
                <>
                  <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Preparing your chat session…
                </>
              ) : (
                <>
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  Chat About Your Report
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportModal;
