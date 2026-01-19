'use client'
import React, { useState } from "react";
import axios from "axios";
import { toast } from "react-toastify";
import ReportModal from "@/modals/ReportModal";
import { ReportSummary, UploadedFile } from "@/types/types";

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

const BrainIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23-.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232 1.232 3.233 0 4.465l-1.406 1.406c-1.232 1.232-3.233 1.232-4.465 0l-1.403-1.403M5 14.5l-1.57.393A9.065 9.065 0 0012 15a9.065 9.065 0 006.23-.693L19.8 15.3M5 14.5l-1.402 1.402c-1.232 1.232-1.232 3.233 0 4.465l1.406 1.406c1.232 1.232 3.233 1.232 4.465 0l1.403-1.403" />
  </svg>
);

const ChatIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
  </svg>
);

const ShieldIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
  </svg>
);

const LandingPage: React.FC = () => {
  const [showUpload, setShowUpload] = useState(false);
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

      const response = await axios.post("api/report", formData);

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

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  if (showUpload) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 flex justify-center items-center p-4">
        <div className="bg-white/10 backdrop-blur-xl shadow-2xl rounded-3xl p-8 w-full max-w-lg border border-white/20">
          <button
            onClick={() => setShowUpload(false)}
            className="mb-4 text-white/70 hover:text-white text-sm flex items-center gap-2 transition"
          >
            ← Back to Home
          </button>
          
          <h1 className="text-3xl font-extrabold text-white mb-2 text-center">
            Upload Your Reports
          </h1>
          <p className="text-sm text-white/70 text-center mb-6">
            Upload medical reports in PDF format (max 10MB)
          </p>

          <label className="border-2 border-dashed border-slate-500/50 rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer hover:bg-white/5 transition-all duration-300 group">
            <div className="text-slate-400 mb-3 group-hover:text-slate-300 transition">
              <UploadCloudIcon />
            </div>
            <span className="text-md font-semibold text-slate-400 mb-1 transition group-hover:text-slate-300">
              Drag & Drop Files Here
            </span>
            <span className="text-xs text-white/60">
              or Click to browse your device
            </span>
            <input
              type="file"
              className="hidden"
              disabled={isUploading}
              accept="application/pdf"
              multiple
              onChange={handleFileChange}
            />
          </label>

          <div className="mt-6 space-y-4">
            {files.length > 0 && (
              <h3 className="text-lg font-bold text-white border-b border-white/20 pb-2">
                Files Ready ({files.length})
              </h3>
            )}
            <div className="overflow-y-auto max-h-60 space-y-3">
              {files.map((item, idx) => (
                <div
                  key={idx}
                  className="flex items-center bg-white/5 border border-white/10 p-3 rounded-lg shadow-sm hover:bg-white/10 transition duration-200"
                >
                  <div className="w-10 h-10 rounded-full flex items-center justify-center mr-4 flex-shrink-0 bg-red-500/20">
                    <DocumentIcon />
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className="truncate text-sm font-medium text-white" title={item.file.name}>
                      {item.file.name}
                    </p>
                    <p className="text-xs text-white/50">{formatFileSize(item.file.size)}</p>
                  </div>

                  <button
                    onClick={() => removeFile(idx)}
                    className="ml-4 p-1 rounded-full text-white/50 hover:bg-red-500/20 hover:text-red-400 transition"
                    aria-label="Remove file"
                  >
                    <CloseIcon />
                  </button>
                </div>
              ))}
            </div>
          </div>

          <button
            disabled={files.length === 0 || isUploading}
            onClick={uploadToBackend}
            className={`mt-8 w-full py-3 font-bold rounded-xl transition-all duration-300 focus:outline-none focus:ring-4 focus:ring-blue-500/50 ${
              files.length === 0
                ? "bg-gray-600 text-gray-400 cursor-not-allowed"
                : isUploading
                ? "bg-blue-500 text-white cursor-wait"
                : "bg-gradient-to-r from-slate-700 to-slate-600 text-white hover:from-slate-600 hover:to-slate-500 shadow-lg hover:shadow-xl"
            }`}
          >
            {isUploading ? "Generating Report..." : `Generate ${files.length} Reports`}
          </button>
        </div>
        <ReportModal open={modalOpen} onClose={() => setModalOpen(false)} contents={reportSummaries} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 text-white overflow-hidden">
      {/* Hero Section */}
      <div className="relative">
        {/* Animated Background Elements */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-20 left-10 w-72 h-72 bg-slate-700/10 rounded-full blur-3xl animate-pulse"></div>
          <div className="absolute bottom-20 right-10 w-96 h-96 bg-slate-600/10 rounded-full blur-3xl animate-pulse delay-700"></div>
        </div>

        <nav className="relative z-10 container mx-auto px-6 py-6 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-slate-700 to-slate-600 rounded-lg flex items-center justify-center">
              <span className="text-2xl">🏥</span>
            </div>
            <span className="text-2xl font-bold bg-gradient-to-r from-slate-300 to-slate-400 bg-clip-text text-transparent">
              HealthBot
            </span>
          </div>
          <button
            onClick={() => setShowUpload(true)}
            className="px-6 py-2.5 bg-white/10 backdrop-blur-sm border border-white/20 rounded-full hover:bg-white/20 transition-all duration-300 font-medium"
          >
            Get Started
          </button>
        </nav>

        <div className="relative z-10 container mx-auto px-6 py-20 lg:py-32">
          <div className="max-w-4xl mx-auto text-center">
            <div className="inline-block mb-4 px-4 py-1.5 bg-slate-700/30 border border-slate-600/40 rounded-full text-slate-300 text-sm font-medium">
              AI-Powered Medical Analysis
            </div>
            <h1 className="text-5xl lg:text-7xl font-extrabold mb-6 leading-tight">
              Your Medical Reports,
              <span className="block bg-gradient-to-r from-slate-300 via-slate-400 to-slate-500 bg-clip-text text-transparent">
                Simplified & Intelligent
              </span>
            </h1>
            <p className="text-xl lg:text-2xl text-white/70 mb-10 max-w-2xl mx-auto leading-relaxed">
              Upload your medical reports and chat with an AI assistant that understands your health data using advanced RAG technology.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                onClick={() => setShowUpload(true)}
                className="px-8 py-4 bg-gradient-to-r from-slate-700 to-slate-600 rounded-full font-bold text-lg hover:shadow-2xl hover:scale-105 transition-all duration-300"
              >
                Upload Your Report
              </button>
              <button
                onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}
                className="px-8 py-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-full font-bold text-lg hover:bg-white/20 transition-all duration-300"
              >
                Learn More
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div id="features" className="relative py-20 lg:py-32">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl lg:text-5xl font-bold mb-4">
              Powerful Features
            </h2>
            <p className="text-xl text-white/70 max-w-2xl mx-auto">
              Advanced AI technology to help you understand your medical reports better
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            <div className="group bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-8 hover:bg-white/10 hover:border-white/20 transition-all duration-300 hover:scale-105">
              <div className="w-16 h-16 bg-gradient-to-br from-slate-700 to-slate-600 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <BrainIcon />
              </div>
              <h3 className="text-2xl font-bold mb-4">RAG Technology</h3>
              <p className="text-white/70 leading-relaxed">
                Retrieval-Augmented Generation ensures accurate, context-aware answers grounded in your specific medical reports.
              </p>
            </div>

            <div className="group bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-8 hover:bg-white/10 hover:border-white/20 transition-all duration-300 hover:scale-105">
              <div className="w-16 h-16 bg-gradient-to-br from-slate-600 to-slate-700 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <ChatIcon />
              </div>
              <h3 className="text-2xl font-bold mb-4">Natural Conversations</h3>
              <p className="text-white/70 leading-relaxed">
                Ask questions in plain language and get clear, professional explanations about your medical information.
              </p>
            </div>

            <div className="group bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-8 hover:bg-white/10 hover:border-white/20 transition-all duration-300 hover:scale-105">
              <div className="w-16 h-16 bg-gradient-to-br from-slate-600 to-slate-500 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <ShieldIcon />
              </div>
              <h3 className="text-2xl font-bold mb-4">Secure & Private</h3>
              <p className="text-white/70 leading-relaxed">
                Your medical data is processed securely with industry-standard encryption and privacy practices.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* How It Works Section */}
      <div className="relative py-20 lg:py-32 bg-white/5">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl lg:text-5xl font-bold mb-4">
              How It Works
            </h2>
            <p className="text-xl text-white/70 max-w-2xl mx-auto">
              Get insights from your medical reports in three simple steps
            </p>
          </div>

          <div className="max-w-4xl mx-auto space-y-12">
            <div className="flex flex-col md:flex-row gap-6 items-center">
              <div className="flex-shrink-0 w-16 h-16 bg-gradient-to-br from-slate-700 to-slate-600 rounded-full flex items-center justify-center text-2xl font-bold">
                1
              </div>
              <div className="flex-1 bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6">
                <h3 className="text-2xl font-bold mb-2">Upload Your Report</h3>
                <p className="text-white/70">
                  Upload your medical report in PDF format. Our AI will analyze and extract key information automatically.
                </p>
              </div>
            </div>

            <div className="flex flex-col md:flex-row gap-6 items-center">
              <div className="flex-shrink-0 w-16 h-16 bg-gradient-to-br from-slate-600 to-slate-700 rounded-full flex items-center justify-center text-2xl font-bold">
                2
              </div>
              <div className="flex-1 bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6">
                <h3 className="text-2xl font-bold mb-2">AI Processes Your Data</h3>
                <p className="text-white/70">
                  Advanced embeddings are created and stored securely, enabling intelligent retrieval and accurate responses.
                </p>
              </div>
            </div>

            <div className="flex flex-col md:flex-row gap-6 items-center">
              <div className="flex-shrink-0 w-16 h-16 bg-gradient-to-br from-slate-600 to-slate-500 rounded-full flex items-center justify-center text-2xl font-bold">
                3
              </div>
              <div className="flex-1 bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6">
                <h3 className="text-2xl font-bold mb-2">Chat & Get Answers</h3>
                <p className="text-white/70">
                  Ask questions about your report and receive clear, contextual answers powered by AI and your actual medical data.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="relative py-20 lg:py-32">
        <div className="container mx-auto px-6">
          <div className="max-w-4xl mx-auto text-center bg-gradient-to-br from-slate-800/30 to-slate-700/30 backdrop-blur-xl border border-white/20 rounded-3xl p-12">
            <h2 className="text-4xl lg:text-5xl font-bold mb-6">
              Ready to Get Started?
            </h2>
            <p className="text-xl text-white/70 mb-8 max-w-2xl mx-auto">
              Upload your first medical report and experience the power of AI-assisted health insights.
            </p>
            <button
              onClick={() => setShowUpload(true)}
              className="px-10 py-4 bg-gradient-to-r from-slate-700 to-slate-600 rounded-full font-bold text-lg hover:shadow-2xl hover:scale-105 transition-all duration-300"
            >
              Upload Report Now
            </button>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="relative py-8 border-t border-white/10">
        <div className="container mx-auto px-6 text-center text-white/50 text-sm">
          <p>© 2026 HealthBot RAG. Advanced AI medical assistant powered by RAG technology.</p>
        </div>
      </footer>

      <ReportModal open={modalOpen} onClose={() => setModalOpen(false)} contents={reportSummaries} />
    </div>
  );
};

export default LandingPage;