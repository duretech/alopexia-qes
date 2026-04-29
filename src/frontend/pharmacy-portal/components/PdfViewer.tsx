"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
  data: ArrayBuffer;
}

export function PdfViewer({ data }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [rendering, setRendering] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!data) return;

    let cancelled = false;
    setRendering(true);
    setError(null);

    (async () => {
      try {
        const pdfjsLib = await import("pdfjs-dist");
        pdfjsLib.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

        const loadingTask = pdfjsLib.getDocument({ data: data.slice(0) });
        const pdf = await loadingTask.promise;

        if (cancelled || !containerRef.current) return;
        containerRef.current.innerHTML = "";

        for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
          if (cancelled) break;

          const page = await pdf.getPage(pageNum);
          const viewport = page.getViewport({ scale: 1.5 });

          const canvas = document.createElement("canvas");
          const ctx = canvas.getContext("2d");
          if (!ctx) continue;

          canvas.width = viewport.width;
          canvas.height = viewport.height;
          canvas.style.display = "block";
          canvas.style.width = "100%";
          canvas.style.marginBottom = pageNum < pdf.numPages ? "8px" : "0";
          canvas.oncontextmenu = (e) => e.preventDefault();

          containerRef.current?.appendChild(canvas);
          await page.render({ canvasContext: ctx, viewport }).promise;
        }

        if (!cancelled) setRendering(false);
      } catch {
        if (!cancelled) {
          setError("Failed to render PDF.");
          setRendering(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [data]);

  return (
    <div style={{ width: "100%", height: "100%", overflow: "auto", position: "relative" }}>
      {rendering && !error && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "var(--color-neutral-100)",
          }}
        >
          <span style={{ color: "var(--color-neutral-500)", fontSize: "0.9375rem" }}>
            Rendering…
          </span>
        </div>
      )}
      {error && (
        <div style={{ padding: "2rem", textAlign: "center", color: "var(--color-danger-600)" }}>
          {error}
        </div>
      )}
      <div
        ref={containerRef}
        style={{ padding: "1rem", userSelect: "none", WebkitUserSelect: "none" }}
      />
    </div>
  );
}
