import { type ReactNode, useMemo, useState } from 'react';

export function VirtualizedList<T>({
  items,
  itemHeight,
  height,
  overscan = 4,
  className,
  renderItem,
}: {
  items: T[];
  itemHeight: number;
  height: number;
  overscan?: number;
  className?: string;
  renderItem: (item: T, index: number) => ReactNode;
}) {
  const [scrollTop, setScrollTop] = useState(0);
  const totalHeight = items.length * itemHeight;

  const { start, end } = useMemo(() => {
    const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
    const endIndex = Math.min(items.length, Math.ceil((scrollTop + height) / itemHeight) + overscan);
    return { start: startIndex, end: endIndex };
  }, [height, itemHeight, items.length, overscan, scrollTop]);

  const visible = items.slice(start, end);

  return (
    <div
      className={className}
      style={{ height, overflowY: 'auto', position: 'relative' }}
      onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
      data-testid="virtualized-list"
    >
      <div style={{ height: totalHeight, position: 'relative' }}>
        <div style={{ position: 'absolute', top: start * itemHeight, left: 0, right: 0 }}>
          {visible.map((item, offset) => (
            <div key={start + offset} style={{ height: itemHeight }}>
              {renderItem(item, start + offset)}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
