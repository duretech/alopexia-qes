"use client";

import { useEffect, type ReactNode } from "react";
import { Button } from "./Button";

export function Modal({
  open,
  title,
  children,
  onClose,
  footer,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
  footer?: ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="qes-modal-root" role="dialog" aria-modal="true" aria-labelledby="qes-modal-title">
      <button type="button" className="qes-modal-backdrop" aria-label="Close dialog" onClick={onClose} />
      <div className="qes-modal">
        <div className="qes-modal__head">
          <h2 id="qes-modal-title" className="qes-modal__title">
            {title}
          </h2>
          <Button variant="ghost" className="qes-modal__close" onClick={onClose} aria-label="Close">
            ×
          </Button>
        </div>
        <div className="qes-modal__body">{children}</div>
        {footer && <div className="qes-modal__foot">{footer}</div>}
      </div>
    </div>
  );
}
