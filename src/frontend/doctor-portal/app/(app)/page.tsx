"use client";

import { useState, useRef } from "react";
import { Badge } from "@qes-ui/components/Badge";
import { Button } from "@qes-ui/components/Button";
import { Card, CardHeader } from "@qes-ui/components/Card";
import { TextField } from "@qes-ui/components/TextField";
import { apiFetch, formatApiError } from "@qes-ui/lib/api";

interface PrescriptionItem {
  file: File;
  patientId: string;
  medicationName: string;
  dosage: string;
  idempotencyKey: string;
  status?: "pending" | "uploading" | "success" | "error";
  error?: string;
  result?: { prescription_id: string; verification_status: string };
}

interface ProgressStep {
  number: number;
  title: string;
  status: "completed" | "current" | "pending";
}

interface FileValidation {
  valid: boolean;
  error?: string;
}

export default function UploadPage() {
  const [files, setFiles] = useState<PrescriptionItem[]>([]);
  const [currentPrescription, setCurrentPrescription] = useState<Partial<PrescriptionItem>>({});
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [reviewIndex, setReviewIndex] = useState<number | null>(null);
  const [previewIndex, setPreviewIndex] = useState<number | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string>("");
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [fileValidation, setFileValidation] = useState<FileValidation | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Determine current step based on progress
  const getProgressSteps = (): ProgressStep[] => {
    const step1Completed = files.length > 0;
    const allFilesHaveDetails = files.length > 0 && files.every(f => f.patientId);
    const step3Completed = files.some(f => f.status === "success");

    let step1Status: "completed" | "current" | "pending" = "pending";
    let step2Status: "completed" | "current" | "pending" = "pending";
    let step3Status: "completed" | "current" | "pending" = "pending";

    // Determine which step is current
    if (!step1Completed) {
      step1Status = "current";
    } else if (!allFilesHaveDetails) {
      step2Status = "current";
    } else if (!step3Completed) {
      step3Status = "current";
    } else {
      step3Status = "completed";
    }

    // Mark completed steps
    if (step1Completed) step1Status = "completed";
    if (allFilesHaveDetails && step1Status === "completed") step2Status = "completed";

    return [
      { number: 1, title: "Select PDF(s)", status: step1Status },
      { number: 2, title: "Review Details", status: step2Status },
      { number: 3, title: "Upload & Verify", status: step3Status },
    ];
  };

  const steps = getProgressSteps();

  function validateFile(file: File): FileValidation {
    const maxSize = 50 * 1024 * 1024;
    if (!file.type.includes("pdf")) {
      return { valid: false, error: "File must be a PDF" };
    }
    if (file.size > maxSize) {
      return { valid: false, error: `File too large (${(file.size / 1024 / 1024).toFixed(1)}MB). Max 50MB.` };
    }
    if (file.size < 1024) {
      return { valid: false, error: "File too small. Upload a valid PDF." };
    }
    return { valid: true };
  }

  function handleDrag(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === "dragenter" || e.type === "dragover");
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    addFiles(Array.from(e.dataTransfer.files));
  }

  function addFiles(filesToAdd: File[]) {
    filesToAdd.forEach(file => {
      const validation = validateFile(file);
      if (!validation.valid) {
        setFileValidation(validation);
        return;
      }
      const newItem: PrescriptionItem = {
        file,
        patientId: "",
        medicationName: "",
        dosage: "",
        idempotencyKey: `upload-${Date.now()}-${Math.random()}`,
        status: "pending",
      };
      setFiles(prev => [...prev, newItem]);
      setFileValidation({ valid: true });
    });
  }

  function removePrescription(index: number) {
    setFiles(prev => prev.filter((_, i) => i !== index));
  }

  function openReviewModal(index: number) {
    setReviewIndex(index);
    setCurrentPrescription({ ...files[index] });
    setShowReviewModal(true);
  }

  function openPreview(index: number) {
    setPreviewIndex(index);
    const file = files[index].file;
    const url = URL.createObjectURL(file);
    setPdfUrl(url);
  }

  function closePreview() {
    if (pdfUrl) {
      URL.revokeObjectURL(pdfUrl);
    }
    setPreviewIndex(null);
    setPdfUrl("");
  }

  function saveReviewModal() {
    if (reviewIndex === null) return;
    const updated = [...files];
    updated[reviewIndex] = { ...updated[reviewIndex], ...currentPrescription };
    setFiles(updated);
    setShowReviewModal(false);
    setCurrentPrescription({});
  }

  async function uploadAll() {
    setUploading(true);
    setShowSuccess(false);
    let successCount = 0;

    for (let i = 0; i < files.length; i++) {
      if (!files[i].patientId) continue;
      const updated = [...files];
      updated[i].status = "uploading";
      setFiles(updated);

      const formData = new FormData();
      formData.append("file", files[i].file);
      formData.append(
        "metadata",
        JSON.stringify({
          patient_id: files[i].patientId,
          idempotency_key: files[i].idempotencyKey,
          medication_name: files[i].medicationName || undefined,
          dosage: files[i].dosage || undefined,
        }),
      );

      try {
        const res = await apiFetch("doctor", "/api/v1/prescriptions/upload", {
          method: "POST",
          body: formData,
        });

        if (res.ok) {
          const data = (await res.json()) as { prescription_id: string; verification_status?: string };
          updated[i].status = "success";
          updated[i].result = {
            prescription_id: data.prescription_id,
            verification_status: data.verification_status || "pending"
          };
          successCount++;
        } else {
          const err = (await res.json()) as { detail?: unknown };
          updated[i].status = "error";
          updated[i].error = formatApiError(err as { detail?: string });
        }
      } catch (e) {
        updated[i].status = "error";
        updated[i].error = "Network error";
      }
      setFiles(updated);
      await new Promise(resolve => setTimeout(resolve, 200));
    }

    setUploading(false);
    if (successCount > 0) {
      setShowSuccess(true);
      setTimeout(() => setShowSuccess(false), 5000);
    }
  }

  const completedCount = files.filter(f => f.status === "success").length;
  const canUpload = files.some(f => f.patientId && f.status === "pending");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Success Animation */}
      {showSuccess && (
        <div style={{
          padding: "1.5rem",
          background: "var(--color-success-50)",
          border: "2px solid var(--color-success-500)",
          borderRadius: "var(--radius-lg)",
          textAlign: "center",
          animation: "slideDown 0.3s ease-out",
        }}>
          <div style={{ fontSize: "2.5rem", marginBottom: "0.5rem" }}>✨</div>
          <div style={{ fontWeight: 600, color: "var(--color-success-700)" }}>
            {completedCount} prescription{completedCount !== 1 ? "s" : ""} uploaded successfully!
          </div>
          <div style={{ fontSize: "0.875rem", color: "var(--color-success-600)", marginTop: "0.25rem" }}>
            Pharmacy has been notified. Verification results will appear shortly.
          </div>
        </div>
      )}

      {/* Enhanced Progress Steps */}
      <Card padding="lg">
        <div style={{ display: "flex", gap: "2rem", alignItems: "center", flexWrap: "wrap" }}>
          {steps.map((step, idx) => {
            const isCompleted = step.status === "completed";
            const isCurrent = step.status === "current";
            const isPending = step.status === "pending";

            return (
              <div key={step.number} style={{
                display: "flex",
                alignItems: "center",
                gap: "0.75rem",
                opacity: isCurrent ? 1 : isPending ? 0.4 : 0.8,
                transition: "opacity 0.3s ease",
              }}>
                <div style={{
                  width: "44px",
                  height: "44px",
                  borderRadius: "50%",
                  background: isCurrent
                    ? "var(--color-primary-600)"
                    : isCompleted
                      ? "var(--color-success-600)"
                      : "var(--color-neutral-300)",
                  color: isCurrent || isCompleted ? "white" : "var(--color-neutral-600)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "1.125rem",
                  fontWeight: 700,
                  boxShadow: isCurrent ? "0 0 0 6px var(--color-primary-100)" : "none",
                  transition: "all 0.3s ease",
                }}>
                  {isCompleted ? "✓" : step.number}
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "0.125rem" }}>
                  <div style={{
                    fontSize: isCurrent ? "0.9375rem" : "0.875rem",
                    fontWeight: isCurrent ? 700 : 500,
                    color: isCurrent ? "var(--color-primary-600)" : "var(--color-neutral-900)",
                    transition: "all 0.3s ease",
                  }}>
                    {step.title}
                  </div>
                  {isCompleted && (
                    <div style={{ fontSize: "0.7rem", color: "var(--color-success-600)", fontWeight: 500 }}>✓ Completed</div>
                  )}
                  {isCurrent && (
                    <div style={{ fontSize: "0.7rem", color: "var(--color-primary-600)", fontWeight: 500 }}>● In progress</div>
                  )}
                </div>

                {idx < steps.length - 1 && (
                  <div style={{
                    width: "40px",
                    height: "2px",
                    background: isCompleted ? "var(--color-success-600)" : "var(--color-neutral-200)",
                    margin: "0 0.5rem 0 1.5rem",
                    transition: "background 0.3s ease",
                  }} />
                )}
              </div>
            );
          })}
        </div>
      </Card>

      {/* Main Card */}
      <Card padding="lg">
        <CardHeader
          title="Upload Signed Prescriptions"
          description="Digitally signed PDFs with QTSP verification. Supports batch uploads and previews."
          action={
            <a href="/prescription-template.pdf" download style={{ fontSize: "0.875rem", color: "var(--color-primary-600)", textDecoration: "none", fontWeight: 500 }}>
              📋 Download template
            </a>
          }
        />

        {/* Step 1: File Upload */}
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginBottom: "1.75rem" }}>
          <div>
            <h3 style={{ margin: "0 0 0.5rem", fontSize: "0.9375rem", fontWeight: 600, color: "var(--color-neutral-900)" }}>
              Step 1: Select prescription PDF(s)
            </h3>
            <p style={{ margin: 0, fontSize: "0.875rem", color: "var(--color-neutral-500)" }}>
              Drag & drop multiple files or click to browse. Max 50MB per file.
            </p>
          </div>

          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              padding: "2rem 1.5rem",
              border: `2px dashed ${dragActive ? "var(--color-primary-500)" : "var(--color-neutral-300)"}`,
              borderRadius: "var(--radius-lg)",
              background: dragActive ? "var(--color-primary-50)" : "var(--color-neutral-50)",
              textAlign: "center",
              cursor: "pointer",
              transition: "all 0.2s",
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="application/pdf"
              onChange={(e) => addFiles(Array.from(e.target.files || []))}
              style={{ display: "none" }}
            />
            <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>📤</div>
            <div style={{ fontWeight: 600, color: "var(--color-neutral-900)" }}>Drag & drop PDFs here or click to browse</div>
            <div style={{ fontSize: "0.875rem", color: "var(--color-neutral-500)", marginTop: "0.25rem" }}>
              Multiple files supported • PDF only • Max 50MB each
            </div>
          </div>

          {fileValidation && !fileValidation.valid && (
            <div className="qes-alert qes-alert--error">
              {fileValidation.error}
            </div>
          )}
        </div>

        {/* Step 2: File Queue */}
        {files.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", paddingBottom: "1.75rem", borderBottom: "1px solid var(--color-neutral-200)" }}>
            <div>
              <h3 style={{ margin: "0 0 0.5rem", fontSize: "0.9375rem", fontWeight: 600, color: "var(--color-neutral-900)" }}>
                Step 2: Review Prescriptions ({completedCount}/{files.length} completed)
              </h3>
              <p style={{ margin: 0, fontSize: "0.875rem", color: "var(--color-neutral-500)" }}>
                Click to preview, edit, or remove. Add patient details before uploading.
              </p>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {files.map((item, idx) => (
                <div key={idx} style={{
                  padding: "1rem 1.25rem",
                  border: "1px solid var(--color-neutral-200)",
                  borderRadius: "var(--radius-md)",
                  background: item.status === "success" ? "var(--color-success-50)" : "var(--color-neutral-50)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 500, color: "var(--color-neutral-900)" }}>
                      {item.file.name}
                    </div>
                    <div style={{ fontSize: "0.8125rem", color: "var(--color-neutral-500)", marginTop: "0.25rem" }}>
                      {(item.file.size / 1024 / 1024).toFixed(2)} MB • {item.patientId ? `✓ Patient: ${item.patientId.substring(0, 8)}...` : "⚠️ Patient: required"} • {item.medicationName || "—"}
                    </div>
                    {item.status === "success" && item.result && (
                      <div style={{ fontSize: "0.8125rem", color: "var(--color-success-600)", marginTop: "0.25rem" }}>
                        ✓ {item.result.verification_status} • ID: {item.result.prescription_id}
                      </div>
                    )}
                    {item.status === "error" && (
                      <div style={{ fontSize: "0.8125rem", color: "var(--color-danger-600)", marginTop: "0.25rem" }}>
                        ✗ {item.error}
                      </div>
                    )}
                  </div>

                  <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap", justifyContent: "flex-end" }}>
                    {item.status === "uploading" && <Badge tone="warning">⏳ Uploading</Badge>}
                    {item.status === "success" && <Badge tone="success">✓ Done</Badge>}
                    {item.status === "error" && <Badge tone="danger">✗ Failed</Badge>}

                    <Button variant="secondary" onClick={() => openPreview(idx)} style={{ padding: "0.5rem 0.75rem", fontSize: "0.8125rem" }}>
                      👁️ Preview
                    </Button>

                    {(item.status === "pending" || !item.patientId) && (
                      <>
                        <Button variant="secondary" onClick={() => openReviewModal(idx)} style={{ padding: "0.5rem 0.75rem", fontSize: "0.8125rem" }}>
                          {!item.patientId ? "Add details" : "Edit"}
                        </Button>
                        <Button variant="ghost" onClick={() => removePrescription(idx)} style={{ padding: "0.5rem 0.5rem", fontSize: "0.8125rem", color: "var(--color-danger-600)" }}>
                          ✕
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Step 3: Upload Button */}
        {files.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem", paddingTop: "1.75rem" }}>
            <div>
              <h3 style={{ margin: "0 0 0.5rem", fontSize: "0.9375rem", fontWeight: 600, color: "var(--color-neutral-900)" }}>
                Step 3: Upload & Verification
              </h3>
              <p style={{ margin: 0, fontSize: "0.875rem", color: "var(--color-neutral-500)" }}>
                Files will be scanned, validated, and verified. Pharmacy will be notified.
              </p>
            </div>

            <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
              <Button variant="primary" disabled={uploading || !canUpload} onClick={uploadAll} style={{ minWidth: "160px" }}>
                {uploading ? `Uploading (${completedCount}/${files.length})…` : `Upload ${files.length} Prescription${files.length !== 1 ? "s" : ""}`}
              </Button>
              {uploading && <Badge tone="warning">Processing...</Badge>}
            </div>

            <div style={{
              padding: "1rem 1.25rem",
              background: "var(--color-neutral-50)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--color-neutral-200)",
              fontSize: "0.8125rem",
              color: "var(--color-neutral-600)",
              lineHeight: 1.6,
            }}>
              <strong style={{ color: "var(--color-neutral-900)" }}>Processing steps:</strong>
              <ol style={{ margin: "0.5rem 0 0", paddingLeft: "1.5rem" }}>
                <li>🔍 ClamAV malware scan</li>
                <li>✍️ Digital signature verification (QTSP/Dokobit)</li>
                <li>📜 Certificate chain validation</li>
                <li>🔐 Secure storage with tenant isolation</li>
                <li>📧 Pharmacy notification</li>
              </ol>
            </div>
          </div>
        )}

        {files.length === 0 && (
          <div style={{ textAlign: "center", padding: "2rem", color: "var(--color-neutral-500)" }}>
            <div style={{ fontSize: "3rem", marginBottom: "0.5rem" }}>📄</div>
            <div style={{ fontSize: "0.9375rem", fontWeight: 500 }}>No files selected yet</div>
            <div style={{ fontSize: "0.8125rem", marginTop: "0.25rem" }}>Upload PDFs to get started</div>
          </div>
        )}
      </Card>

      {/* Review Modal */}
      {showReviewModal && reviewIndex !== null && (
        <div style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.5)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 1000,
        }} onClick={() => setShowReviewModal(false)}>
          <div style={{
            width: "90%",
            maxWidth: "500px",
            maxHeight: "90vh",
            overflow: "auto",
          }} onClick={(e: React.MouseEvent<HTMLDivElement>) => e.stopPropagation()}>
            <Card padding="lg">
            <CardHeader title={`Review: ${files[reviewIndex].file.name}`} />
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div style={{ padding: "1rem", background: "var(--color-neutral-50)", borderRadius: "var(--radius-md)", fontSize: "0.875rem" }}>
                <strong>File Details:</strong>
                <div style={{ marginTop: "0.5rem", color: "var(--color-neutral-600)" }}>
                  Size: {(files[reviewIndex].file.size / 1024 / 1024).toFixed(2)} MB
                  <br />
                  Modified: {new Date(files[reviewIndex].file.lastModified).toLocaleString()}
                </div>
              </div>
              <TextField label="Patient ID (UUID)" value={currentPrescription.patientId || ""} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCurrentPrescription({ ...currentPrescription, patientId: e.target.value })} placeholder="e.g., 66666666-6666-6666-6666-666666666666" required />
              <TextField label="Medication Name" value={currentPrescription.medicationName || ""} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCurrentPrescription({ ...currentPrescription, medicationName: e.target.value })} placeholder="e.g., Amoxicillin 500mg" />
              <TextField label="Dosage/Instructions" value={currentPrescription.dosage || ""} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCurrentPrescription({ ...currentPrescription, dosage: e.target.value })} placeholder="e.g., 1 tablet × 3 daily" />
              <TextField label="Idempotency Key" value={currentPrescription.idempotencyKey || ""} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCurrentPrescription({ ...currentPrescription, idempotencyKey: e.target.value })} hint="Auto-generated for deduplication" disabled />
              <div style={{ display: "flex", gap: "0.75rem", justifyContent: "flex-end", paddingTop: "1rem", borderTop: "1px solid var(--color-neutral-200)" }}>
                <Button variant="ghost" onClick={() => setShowReviewModal(false)}>Cancel</Button>
                <Button variant="primary" onClick={saveReviewModal} disabled={!currentPrescription.patientId}>Save Details</Button>
              </div>
            </div>
            </Card>
          </div>
        </div>
      )}

      {/* PDF Preview Modal */}
      {previewIndex !== null && pdfUrl && (
        <div style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.7)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 2000,
        }} onClick={closePreview}>
          <div style={{
            width: "90%",
            height: "90vh",
            maxWidth: "900px",
            background: "white",
            borderRadius: "var(--radius-lg)",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }} onClick={(e: React.MouseEvent<HTMLDivElement>) => e.stopPropagation()}>
            <div style={{ padding: "1rem 1.5rem", borderBottom: "1px solid var(--color-neutral-200)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h2 style={{ margin: 0, fontSize: "1rem", fontWeight: 600 }}>📄 PDF Preview</h2>
                <p style={{ margin: "0.25rem 0 0", fontSize: "0.875rem", color: "var(--color-neutral-500)" }}>
                  {files[previewIndex].file.name}
                </p>
              </div>
              <Button variant="ghost" onClick={closePreview} style={{ padding: "0.5rem 0.5rem" }}>✕</Button>
            </div>
            <div style={{ flex: 1, overflow: "auto", background: "var(--color-neutral-100)" }}>
              <iframe src={pdfUrl} style={{ width: "100%", height: "100%", border: "none" }} title="PDF Preview" />
            </div>
            <div style={{ padding: "1rem 1.5rem", borderTop: "1px solid var(--color-neutral-200)", background: "var(--color-neutral-50)", textAlign: "right" }}>
              <Button variant="secondary" onClick={closePreview}>Close Preview</Button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes slideDown {
          from { transform: translateY(-20px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
