import { useEffect, useMemo, useRef } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import type { Citation } from '../lib/types';

export function EvidenceViewer({
  open,
  citation,
  text,
  onClose,
  onPrev,
  onNext,
  onExpand,
  citationIndex,
  citationCount,
}: {
  open: boolean;
  citation: Citation | null;
  text: string;
  onClose: () => void;
  onPrev: () => void;
  onNext: () => void;
  onExpand: (delta: number) => void;
  citationIndex: number;
  citationCount: number;
}) {
  const shellRef = useRef<HTMLDivElement | null>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  const highlighted = useMemo(() => {
    if (!citation) return '';
    return `${citation.path}:L${citation.start_line}-L${citation.end_line}`;
  }, [citation]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
      if (event.key === 'ArrowRight' && (event.metaKey || event.ctrlKey)) {
        onNext();
      }
      if (event.key === 'ArrowLeft' && (event.metaKey || event.ctrlKey)) {
        onPrev();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose, onNext, onPrev, open]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const root = shellRef.current;
    if (!root) {
      return;
    }
    previousFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const focusables = root.querySelectorAll<HTMLElement>('button, [href], input, textarea, select, [tabindex]:not([tabindex="-1"])');
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    first?.focus();

    const trap = (event: KeyboardEvent) => {
      if (event.key !== 'Tab' || !first || !last) {
        return;
      }
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      }
      if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener('keydown', trap);
    return () => {
      window.removeEventListener('keydown', trap);
      previousFocusRef.current?.focus();
    };
  }, [open]);

  if (!open || !citation) return null;

  const lineRef = `${citation.path}:L${citation.start_line}-L${citation.end_line}`;
  const markdownRef = `- [${lineRef}](${citation.path}#L${citation.start_line})`;

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Evidence viewer" data-testid="evidence-modal">
      <div className="modal-shell" ref={shellRef}>
        <header className="modal-header">
          <div>
            <p className="eyebrow">Evidence viewer</p>
            <h3>{highlighted}</h3>
          </div>
          <button type="button" onClick={onClose} className="ghost-btn" aria-label="Close evidence modal">
            Close
          </button>
        </header>

        <div className="evidence-meta" aria-label="Citation metadata">
          <span className="status-pill">File {citation.path}</span>
          <span className="status-pill">Start L{citation.start_line}</span>
          <span className="status-pill">End L{citation.end_line}</span>
          <span className="status-pill">
            Citation {citationIndex + 1}/{citationCount}
          </span>
        </div>

        <div className="evidence-split">
          <aside className="evidence-claim" aria-label="Evidence claim context">
            <h4>Claim context</h4>
            <p>Cross-check this snippet against the answer claim before trusting derived conclusions.</p>
            <div className="ops-readout">
              <span className="status-pill">Deep link {lineRef}</span>
            </div>
            <div className="actions">
              <button type="button" className="ghost-btn small" onClick={() => onExpand(-10)}>
                -10 lines
              </button>
              <button type="button" className="ghost-btn small" onClick={() => onExpand(10)}>
                +10 lines
              </button>
            </div>
            <div className="actions">
              <button type="button" className="ghost-btn small" onClick={onPrev} disabled={citationIndex <= 0}>
                Previous citation
              </button>
              <button
                type="button"
                className="ghost-btn small"
                onClick={onNext}
                disabled={citationIndex >= citationCount - 1}
              >
                Next citation
              </button>
            </div>
          </aside>

          <CodeMirror value={text} editable={false} basicSetup={{ lineNumbers: true }} minHeight="260px" />
        </div>

        <div className="modal-actions">
          <button
            type="button"
            className="ghost-btn small"
            onClick={() => {
              void navigator.clipboard.writeText(text);
            }}
          >
            Copy raw snippet
          </button>
          <button
            type="button"
            className="ghost-btn small"
            onClick={() => {
              void navigator.clipboard.writeText(lineRef);
            }}
          >
            Copy line refs
          </button>
          <button
            type="button"
            className="primary-btn"
            onClick={() => {
              void navigator.clipboard.writeText(markdownRef);
            }}
          >
            Copy markdown citation
          </button>
        </div>
      </div>
    </div>
  );
}
