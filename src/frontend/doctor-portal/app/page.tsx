"use client";

import { useState, useCallback } from "react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FileUpload } from "@/components/ui/file-upload";
import { useToast } from "@/components/ui/toast";
import { Send, FileSignature, Clock, CheckCircle2 } from "lucide-react";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [patientId, setPatientId] = useState("");
  const [idempotencyKey, setIdempotencyKey] = useState("");
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<{ id: string } | null>(null);
  const { toast } = useToast();

  const handleUpload = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!file) return;

      setUploading(true);
      setResult(null);
      const formData = new FormData();
      formData.append("file", file);
      formData.append(
        "metadata",
        JSON.stringify({
          patient_id: patientId,
          idempotency_key: idempotencyKey || `upload-${Date.now()}`,
        })
      );

      try {
        const res = await fetch("/api/v1/prescriptions/upload", {
          method: "POST",
          body: formData,
        });
        if (res.ok) {
          const data = await res.json();
          setResult({ id: data.prescription_id });
          toast("success", "Prescription uploaded successfully");
          setFile(null);
          setPatientId("");
          setIdempotencyKey("");
        } else {
          const err = await res.json().catch(() => ({}));
          toast("error", err.detail?.message || err.detail || "Upload failed");
        }
      } catch {
        toast("error", "Network error — is the API running?");
      } finally {
        setUploading(false);
      }
    },
    [file, patientId, idempotencyKey, toast]
  );

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Upload Prescription</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Upload a digitally signed PDF for QES verification and pharmacy dispensing.
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="flex items-center gap-3 bg-surface rounded-xl border border-border p-4">
          <div className="h-10 w-10 rounded-lg bg-blue-50 flex items-center justify-center">
            <FileSignature className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <p className="text-xs text-text-tertiary">QES Verification</p>
            <p className="text-sm font-semibold text-text-primary">Automatic</p>
          </div>
        </div>
        <div className="flex items-center gap-3 bg-surface rounded-xl border border-border p-4">
          <div className="h-10 w-10 rounded-lg bg-amber-50 flex items-center justify-center">
            <Clock className="h-5 w-5 text-amber-600" />
          </div>
          <div>
            <p className="text-xs text-text-tertiary">Processing Time</p>
            <p className="text-sm font-semibold text-text-primary">&lt; 30 seconds</p>
          </div>
        </div>
        <div className="flex items-center gap-3 bg-surface rounded-xl border border-border p-4">
          <div className="h-10 w-10 rounded-lg bg-emerald-50 flex items-center justify-center">
            <CheckCircle2 className="h-5 w-5 text-emerald-600" />
          </div>
          <div>
            <p className="text-xs text-text-tertiary">Retention</p>
            <p className="text-sm font-semibold text-text-primary">5 years WORM</p>
          </div>
        </div>
      </div>

      {/* Upload form */}
      <Card>
        <CardHeader>
          <CardTitle>Prescription Details</CardTitle>
          <CardDescription>All fields are required unless noted otherwise.</CardDescription>
        </CardHeader>

        <form onSubmit={handleUpload} className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <Input
              label="Patient ID"
              type="text"
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              placeholder="550e8400-e29b-41d4-a716-446655440000"
              hint="UUID format"
              required
            />
            <Input
              label="Idempotency Key"
              type="text"
              value={idempotencyKey}
              onChange={(e) => setIdempotencyKey(e.target.value)}
              placeholder="Auto-generated if empty"
              hint="Optional — prevents duplicate uploads"
            />
          </div>

          <FileUpload
            label="Signed Prescription PDF"
            accept="application/pdf"
            onFileSelect={setFile}
            maxSizeMB={25}
          />

          <div className="flex items-center justify-between pt-2">
            <p className="text-xs text-text-tertiary">
              Uploaded files are scanned for malware and verified against QTSP.
            </p>
            <Button type="submit" loading={uploading} disabled={!file || !patientId} icon={<Send className="h-4 w-4" />}>
              Upload
            </Button>
          </div>
        </form>
      </Card>

      {/* Success result */}
      {result && (
        <div className="flex items-start gap-3 px-4 py-3 rounded-xl bg-emerald-50 border border-emerald-200">
          <CheckCircle2 className="h-5 w-5 text-emerald-600 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-emerald-800">Prescription uploaded successfully</p>
            <p className="text-xs text-emerald-700 mt-0.5 font-mono">ID: {result.id}</p>
          </div>
        </div>
      )}
    </div>
  );
}
