import type { Citation } from '../lib/types';

export function CitationChips({
  citations,
  onOpen,
}: {
  citations: Citation[];
  onOpen: (citation: Citation, index: number) => void;
}) {
  return (
    <ul className="citation-grid" aria-label="Citations">
      {citations.map((citation, index) => (
        <li key={citation.citation_id}>
          <button type="button" className="citation-chip" onClick={() => onOpen(citation, index)}>
            {citation.path}:L{citation.start_line}-L{citation.end_line}
          </button>
        </li>
      ))}
    </ul>
  );
}
