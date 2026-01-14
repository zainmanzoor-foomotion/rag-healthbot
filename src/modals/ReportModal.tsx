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
    <div className="fixed inset-0 bg-gray-900 bg-opacity-60 flex justify-center items-center p-4 z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-2xl font-semibold text-gray-800">{current.filename}</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            ✕
          </button>
        </div>


        {/* Body */}
        <div className="p-6 flex-grow overflow-y-auto space-y-6">
          <section>
            <h3 className="text-xl font-semibold text-gray-800 mb-2">Summary</h3>
            <p className="text-gray-700 whitespace-pre-wrap">{current.summary}</p>
          </section>
          {current.medications.length > 0 &&
            <section>
              <h3 className="text-xl font-semibold text-gray-800 mb-2">Prescribed Medications</h3>
              <ul className="space-y-3">
                {current.medications.map((med, idx) => (
                  <li key={idx} className="p-4 border border-gray-200 rounded-lg">
                    <span className="font-semibold text-gray-900">{med.name}</span>
                    <p className="mt-1 text-gray-700">{med.purpose}</p>
                  </li>
                ))}
              </ul>
            </section>
          }
        </div>

        {/* Footer / Pagination */}
        <div className="border-t border-gray-200">
          {total > 1 && (
            <div className="px-4 py-3 flex justify-between items-center border-b border-gray-200">
              <button
                onClick={prev}
                disabled={currentPage === 0}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition ${currentPage === 0
                  ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                  : "bg-indigo-600 text-white hover:bg-indigo-700"
                  }`}
              >
                ← Previous
              </button>

              <span className="text-sm text-gray-600">
                {currentPage + 1} of {total}
              </span>

              <button
                onClick={next}
                disabled={currentPage === total - 1}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition ${currentPage === total - 1
                  ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                  : "bg-indigo-600 text-white hover:bg-indigo-700"
                  }`}
              >
                Next →
              </button>
            </div>
          )}
          
          {/* Chat Button */}
          <div className="px-4 py-4">
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
                  // Optionally show a toast
                  console.error(e);
                } finally {
                  setIsCreating(false);
                }
              }}
              disabled={isCreating}
              className="w-full bg-indigo-600 text-white px-6 py-3 rounded-lg font-semibold shadow-md hover:bg-indigo-700 hover:shadow-lg transition-all duration-300 flex items-center justify-center gap-2 disabled:opacity-60"
            >
              {isCreating ? "Preparing chat…" : (
                <>
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  Chat About Your Reports
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