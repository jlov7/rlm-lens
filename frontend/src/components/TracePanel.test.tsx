import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { TracePanel } from './TracePanel';

describe('TracePanel', () => {
  it('renders timeline mode button', () => {
    render(<TracePanel events={[{ type: 'run.iteration', timestamp: '2026-02-23T00:00:00Z' }]} />);
    expect(screen.getByRole('button', { name: 'Timeline' })).toBeInTheDocument();
  });
});
