import { describe, expect, it } from 'vitest';

import { toGraph } from './traceGraph';

describe('TracePanel performance shaping', () => {
  it('creates graph data for 600 events without invalid geometry data', () => {
    const events = Array.from({ length: 600 }, (_, index) => ({
      type: index % 7 === 0 ? 'run.subcall' : 'run.iteration',
      timestamp: `2026-02-23T12:00:${String(index % 60).padStart(2, '0')}Z`,
      iteration: index,
    }));

    const graph = toGraph(events);
    expect(graph.nodes).toHaveLength(600);
    expect(graph.edges).toHaveLength(599);

    for (const node of graph.nodes) {
      expect(Number.isFinite(node.position.x)).toBe(true);
      expect(Number.isFinite(node.position.y)).toBe(true);
    }
  });
});
