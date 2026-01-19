import { useState } from "react";
import { ReportSummary } from "@/types/types";
import { useRouter } from "next/navigation";
interface ModalProps {
  open: boolean;
  onClose: () => void;
  contents: ReportSummary[];
}


const ReportModal: React.FC<ModalProps> = ({ open, onClose, contents }) => {
  const [currentPage, setCurrentPage] = useState(0);
  const [isCreating, setIsCreating] = useState(false);
  const router = useRouter();

  if (!open || contents.length === 0) return null;

  const total = contents.length;
  const current = contents[currentPage];

  const prev = () => setCurrentPage((p) => Math.max(p - 1, 0));
  const next = () => setCurrentPage((p) => Math.min(p + 1, total - 1));

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex justify-center items-center p-4 z-50 animate-in fade-in duration-200">
      <div className="bg-gradient-to-br from-slate-950/95 via-slate-900/95 to-slate-800/95 backdrop-blur-xl border border-white/20 rounded-3xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
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
                  <p className="text-sm text-white/60 mt-0.5">Medical Report Analysis</p>
                </div>
              </div>
            </div>
            <button 
              onClick={onClose} 
              className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-full bg-white/10 hover:bg-white/20 text-white/70 hover:text-white transition-all duration-200"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-grow overflow-y-auto px-6 py-6 space-y-6 scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent">
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

          {/* Medications Section */}
          {current.medications.length > 0 && (
            <section className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6 hover:bg-white/10 transition-all duration-300">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-8 h-8 bg-slate-700/30 rounded-lg flex items-center justify-center">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold text-white">Prescribed Medications</h3>
                <span className="ml-auto px-3 py-1 bg-slate-700/30 border border-slate-600/40 rounded-full text-slate-300 text-sm font-medium">
                  {current.medications.length} {current.medications.length === 1 ? 'medication' : 'medications'}
                </span>
              </div>
              <div className="grid gap-4">
                {current.medications.map((med, idx) => (
                  <div 
                    key={idx} 
                    className="bg-white/5 border border-white/10 rounded-xl p-4 hover:bg-white/10 hover:border-white/20 transition-all duration-200 group"
                  >
                    <div className="flex items-start gap-3">
                      <div className="w-6 h-6 bg-gradient-to-br from-slate-600 to-slate-700 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                        <span className="text-white text-xs font-bold">{idx + 1}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <h4 className="font-bold text-white text-lg mb-1 group-hover:text-slate-300 transition-colors">
                          {med.name}
                        </h4>
                        <p className="text-white/70 leading-relaxed">{med.purpose}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        {/* Footer / Pagination + Actions */}
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

              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-white/60">Report</span>
                <span className="px-3 py-1 bg-gradient-to-r from-slate-700/30 to-slate-600/30 border border-white/20 rounded-full text-white font-bold text-sm">
                  {currentPage + 1} / {total}
                </span>
              </div>

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
          
          {/* Chat Button */}
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
                  Preparing your chat session...
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