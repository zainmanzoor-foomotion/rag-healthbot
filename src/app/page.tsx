'use client'
import React, { useState } from "react";
import axios from "axios";
import { toast } from "react-toastify";
import ReportModal from "@/modals/ReportModal";
import { ReportSummary, UploadedFile } from "@/types/types";


// Icon Placeholders (Using inline SVGs for professional appearance)
const UploadCloudIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.885 2.162M18.885 18.162A4 4 0 0017 16m-7-5l3-3m0 0l3 3m-3-3v12" />
  </svg>
);

const DocumentIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

const CloseIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
  </svg>
);


const DocumentUpload: React.FC = () => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [reportSummaries, setReportSummaries] = useState<ReportSummary[]>([]);


  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files;
    if (!selected) return;

    const newFiles: UploadedFile[] = [];

    Array.from(selected).forEach((file) => {
      if (!["application/pdf"].includes(file.type)) {
        toast.error("Only PDF files are allowed.");
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        toast.error(`File "${file.name}" exceeds the maximum size of 10MB and was skipped.`);
        return;
      }


      const preview =
        file.type.includes("image") ? URL.createObjectURL(file) : null;

      newFiles.push({ file, preview });
    });

    setFiles((prev) => [...prev, ...newFiles]);
  };

  const removeFile = (index: number) => {
    // Revoke object URL to prevent memory leaks if it's an image preview
    const fileToRemove = files[index];
    if (fileToRemove.preview) {
      URL.revokeObjectURL(fileToRemove.preview);
    }
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const uploadToBackend = async () => {
    if (files.length === 0) return;

    setIsUploading(true);

    try {
      const formData = new FormData();
      files.forEach((item) => formData.append("file", item.file));

      const response = await axios.post(
        "api/report",
        formData,
        // { headers: { "Content-Type": "multipart/form-data" } }
      );

      console.log("Uploaded:", response.data);
      setReportSummaries(response.data.summaries || []);
      setModalOpen(true);
      setFiles([]);

    } catch (err) {
      console.error(err);
      toast.error("Upload failed.");
    } finally {
      setIsUploading(false);
    }
  };

  // Helper function to format file size
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div className="min-h-screen bg-gray-50 flex justify-center items-center p-4">
      <div className="bg-white shadow-2xl rounded-2xl p-8 w-full max-w-lg transition-all duration-300">
        <h1 className="text-3xl font-extrabold text-gray-800 mb-2 text-center">
          Document Submission Portal
        </h1>
        <p className="text-sm text-gray-500 text-center mb-6">
          Securely upload your medical reports in pdf format. max size : 10MB.
        </p>

        <label
          className="border-2 border-dashed border-indigo-300 rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer hover:bg-indigo-50 transition-all duration-300 group"
        >
          <div className="text-indigo-500 mb-3 group-hover:text-indigo-700 transition">
            <UploadCloudIcon />
          </div>
          <span className="text-md font-semibold text-indigo-600 mb-1 transition group-hover:text-indigo-800">
            Drag & Drop Files Here
          </span>
          <span className="text-xs text-gray-500">
            or Click to browse your device
          </span>
          <input
            type="file"
            className="hidden"
            disabled={isUploading}
            accept="application/pdf,image/png,image/jpeg"
            multiple
            onChange={handleFileChange}
          />
        </label>

        <div className="mt-6 space-y-4">
          {files.length > 0 && <h3 className="text-lg font-bold text-gray-700 border-b pb-2">Files Ready for Upload ({files.length})</h3>}
          <div className="overflow-y-auto max-h-50 space-y-4">

            {files.map((item, idx) => (
              <div
                key={idx}
                className="flex items-center bg-white border border-gray-200 p-3 rounded-lg shadow-sm hover:shadow-md transition duration-200"
              >
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center mr-4 flex-shrink-0"
                  style={{ backgroundColor: item.preview ? '#e0f2f1' : '#ffe4e6' }} // Subtle background colors
                >
                  {item.preview ? (
                    <img
                      src={item.preview}
                      alt="preview"
                      className="w-full h-full rounded-full object-cover"
                    />
                  ) : (
                    <DocumentIcon />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <p className="truncate text-sm font-medium text-gray-800" title={item.file.name}>{item.file.name}</p>
                  <p className="text-xs text-gray-400">{formatFileSize(item.file.size)}</p>
                </div>

                <button
                  onClick={() => removeFile(idx)}
                  className="ml-4 p-1 rounded-full text-gray-400 hover:bg-red-100 hover:text-red-600 transition"
                  aria-label="Remove file"
                >
                  <CloseIcon />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Upload Button (Professional Style) */}
        <button
          disabled={files.length === 0 || isUploading}
          onClick={uploadToBackend}
          className={`mt-8 w-full py-3 font-bold rounded-xl transition-all duration-300 focus:outline-none focus:ring-4 focus:ring-indigo-300 ${files.length === 0
            ? "bg-gray-200 text-gray-500 cursor-not-allowed"
            : isUploading
              ? "bg-indigo-400 text-white cursor-wait"
              : "bg-indigo-600 text-white hover:bg-indigo-700 shadow-lg hover:shadow-xl"
            }`}
        >
          {isUploading ? "Generating Report..." : `Generate ${files.length} Reports`}
        </button>
      </div>
      <ReportModal open={modalOpen} onClose={() => setModalOpen(false)} contents={reportSummaries} />
    </div>
  );
};

export default DocumentUpload;