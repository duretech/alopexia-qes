"use client";

import { useCallback, useState } from "react";
import { Upload, File, X } from "lucide-react";

interface FileUploadProps {
  accept?: string;
  onFileSelect: (file: File | null) => void;
  maxSizeMB?: number;
  label?: string;
}

export function FileUpload({ accept = "application/pdf", onFileSelect, maxSizeMB = 25, label = "Upload file" }: FileUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback(
    (f: File) => {
      setError(null);
      if (f.size > maxSizeMB * 1024 * 1024) {
        setError(`File too large. Maximum size is ${maxSizeMB}MB.`);
        return;
      }
      if (accept && !accept.split(",").some((t) => f.type.match(t.trim()))) {
        setError("Invalid file type. Please upload a PDF.");
        return;
      }
      setFile(f);
      onFileSelect(f);
    },
    [accept, maxSizeMB, onFileSelect]
  );

  const clear = () => {
    setFile(null);
    setError(null);
    onFileSelect(null);
  };

  return (
    <div className="space-y-1.5">
      <label className="block text-sm font-medium text-text-primary">{label}</label>
      {file ? (
        <div className="flex items-center gap-3 px-4 py-3 rounded-lg border border-primary-200 bg-primary-50">
          <File className="h-5 w-5 text-primary-600 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-text-primary truncate">{file.name}</p>
            <p className="text-xs text-text-secondary">{(file.size / 1024).toFixed(0)} KB</p>
          </div>
          <button onClick={clear} className="text-text-tertiary hover:text-text-primary p-1 cursor-pointer">
            <X className="h-4 w-4" />
          </button>
        </div>
      ) : (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragActive(false);
            const f = e.dataTransfer.files[0];
            if (f) handleFile(f);
          }}
          className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-8 transition-colors cursor-pointer ${
            dragActive ? "border-primary-400 bg-primary-50" : "border-border hover:border-border-strong hover:bg-surface-tertiary/50"
          }`}
        >
          <Upload className={`h-8 w-8 mb-2 ${dragActive ? "text-primary-500" : "text-text-tertiary"}`} />
          <p className="text-sm text-text-secondary">
            <span className="font-medium text-primary-600">Click to upload</span> or drag and drop
          </p>
          <p className="text-xs text-text-tertiary mt-1">PDF up to {maxSizeMB}MB</p>
          <input
            type="file"
            accept={accept}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFile(f);
            }}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          />
        </div>
      )}
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  );
}
