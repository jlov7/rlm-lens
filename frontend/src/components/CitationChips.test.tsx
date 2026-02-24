import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { CitationChips } from './CitationChips';

describe('CitationChips', () => {
  it('calls onOpen when a chip is clicked', () => {
    const onOpen = vi.fn();
    render(
      <CitationChips
        citations={[
          {
            citation_id: 'cit_1',
            path: 'src/file.py',
            start_line: 10,
            end_line: 12,
            snippet: 'demo',
          },
        ]}
        onOpen={onOpen}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /src\/file\.py:L10-L12/i }));
    expect(onOpen).toHaveBeenCalledTimes(1);
  });
});
