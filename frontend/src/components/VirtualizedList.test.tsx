import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { VirtualizedList } from './VirtualizedList';

describe('VirtualizedList', () => {
  it('renders only a viewport subset initially', () => {
    const items = Array.from({ length: 200 }, (_, i) => `item-${i}`);

    render(
      <VirtualizedList
        items={items}
        itemHeight={32}
        height={128}
        renderItem={(item) => <div>{item}</div>}
      />
    );

    expect(screen.getByText('item-0')).toBeInTheDocument();
    expect(screen.getByText('item-5')).toBeInTheDocument();
    expect(screen.queryByText('item-80')).not.toBeInTheDocument();
  });
});
