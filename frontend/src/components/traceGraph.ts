import type { Edge, Node } from 'reactflow';
import type { TraceEvent } from '../lib/types';

export type GraphData = {
  nodes: Node[];
  edges: Edge[];
};

export function toGraph(events: TraceEvent[]): GraphData {
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  let y = 20;

  events.forEach((event, idx) => {
    const id = `n-${idx}`;
    nodes.push({
      id,
      position: { x: 100 + (idx % 2) * 260, y },
      data: { label: `${event.type}` },
      style: {
        borderRadius: 12,
        border: '1px solid rgba(128, 210, 220, 0.5)',
        background: 'rgba(14, 29, 39, 0.85)',
        color: '#d9fcff',
        width: 170,
      },
      ariaLabel: `trace event ${event.type}`,
    });
    if (idx > 0) {
      edges.push({ id: `e-${idx - 1}-${idx}`, source: `n-${idx - 1}`, target: id, animated: true });
    }
    y += 90;
  });

  return { nodes, edges };
}
