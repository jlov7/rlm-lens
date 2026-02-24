import { useMemo, useState } from 'react';
import ReactFlow, { Background, Controls, type NodeMouseHandler } from 'reactflow';
import 'reactflow/dist/style.css';
import type { TraceEvent } from '../lib/types';
import { toGraph } from './traceGraph';

type TraceMode = 'graph' | 'timeline';

type Stage = 'retrieve' | 'reason' | 'subcall' | 'finalize' | 'error' | 'other';

function eventTone(type: string): string {
  if (type.includes('error')) return 'error';
  if (type.includes('subcall')) return 'subcall';
  if (type.includes('code')) return 'code';
  if (type.includes('complete')) return 'complete';
  return 'default';
}

function stageFor(type: string): Stage {
  if (type.includes('error')) return 'error';
  if (type.includes('subcall')) return 'subcall';
  if (type.includes('complete')) return 'finalize';
  if (type.includes('code')) return 'reason';
  if (type.includes('iteration') || type.includes('retrieve')) return 'retrieve';
  if (type.includes('metadata')) return 'other';
  return 'reason';
}

function narrative(events: TraceEvent[]): string {
  const stages = events.reduce<Record<Stage, number>>(
    (acc, event) => {
      const stage = stageFor(event.type);
      acc[stage] += 1;
      return acc;
    },
    {
      retrieve: 0,
      reason: 0,
      subcall: 0,
      finalize: 0,
      error: 0,
      other: 0,
    }
  );
  return `Retrieve ${stages.retrieve}, reason ${stages.reason}, subcalls ${stages.subcall}, finalize ${stages.finalize}, errors ${stages.error}.`;
}

export function TracePanel({ events }: { events: TraceEvent[] }) {
  const [mode, setMode] = useState<TraceMode>('graph');
  const [showErrorsOnly, setShowErrorsOnly] = useState(false);
  const [showSubcallsOnly, setShowSubcallsOnly] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);

  const filtered = useMemo(() => {
    return events.filter((event) => {
      if (showErrorsOnly && !event.type.includes('error')) {
        return false;
      }
      if (showSubcallsOnly && !event.type.includes('subcall')) {
        return false;
      }
      if (query.trim().length > 0 && !JSON.stringify(event).toLowerCase().includes(query.trim().toLowerCase())) {
        return false;
      }
      return true;
    });
  }, [events, query, showErrorsOnly, showSubcallsOnly]);

  const graph = useMemo(() => toGraph(filtered), [filtered]);
  const selectedEvent = filtered[selectedIndex] ?? null;
  const stageCounts = useMemo(() => {
    const counts: Record<Stage, number> = {
      retrieve: 0,
      reason: 0,
      subcall: 0,
      finalize: 0,
      error: 0,
      other: 0,
    };
    for (const event of filtered) {
      counts[stageFor(event.type)] += 1;
    }
    return counts;
  }, [filtered]);

  const onNodeClick: NodeMouseHandler = (_evt, node) => {
    const index = Number(node.id.replace('n-', ''));
    if (!Number.isNaN(index)) {
      setSelectedIndex(index);
    }
  };

  return (
    <aside className="trace-panel" data-testid="trace-panel" aria-label="Trace">
      <header className="trace-header">
        <div>
          <h3>Trace</h3>
          <p className="trace-subtitle">Recursive trajectory telemetry and event context.</p>
          <p className="trace-narrative">{narrative(filtered)}</p>
        </div>
        <div className="trace-summary" aria-label="Trace metrics">
          <span className="status-pill">Events {events.length}</span>
          <span className="status-pill">Visible {filtered.length}</span>
        </div>
      </header>

      <div className="trace-toolbar">
        <div className="trace-mode-tabs" aria-label="Trace mode">
          <button type="button" className={mode === 'graph' ? 'tab active' : 'tab'} onClick={() => setMode('graph')}>
            Graph
          </button>
          <button
            type="button"
            className={mode === 'timeline' ? 'tab active' : 'tab'}
            onClick={() => setMode('timeline')}
          >
            Timeline
          </button>
        </div>

        <div className="trace-filter-row">
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={showErrorsOnly}
              onChange={(event) => setShowErrorsOnly(event.target.checked)}
            />
            Errors only
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={showSubcallsOnly}
              onChange={(event) => setShowSubcallsOnly(event.target.checked)}
            />
            Subcalls only
          </label>
        </div>

        <div className="trace-stage-row" aria-label="Trace stage legend">
          <span className="status-pill">Retrieve {stageCounts.retrieve}</span>
          <span className="status-pill">Reason {stageCounts.reason}</span>
          <span className="status-pill">Subcall {stageCounts.subcall}</span>
          <span className="status-pill">Finalize {stageCounts.finalize}</span>
          <span className="status-pill">Errors {stageCounts.error}</span>
        </div>

        <div className="actions">
          <button
            type="button"
            className="ghost-btn small"
            onClick={() => {
              const idx = filtered.findIndex((event) => event.type.includes('error'));
              if (idx >= 0) {
                setMode('timeline');
                setSelectedIndex(idx);
              }
            }}
          >
            Jump to error
          </button>
          <button
            type="button"
            className="ghost-btn small"
            onClick={() => {
              const idx = filtered.findIndex((event) => event.type.includes('subcall') || event.type.includes('iteration'));
              if (idx >= 0) {
                setMode('timeline');
                setSelectedIndex(idx);
              }
            }}
          >
            Jump to hotspot
          </button>
        </div>
      </div>

      <label className="trace-search">
        Search trace events
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search trace"
          aria-label="Search trace events"
        />
      </label>

      {mode === 'graph' ? (
        <div className="trace-flow-wrap" data-testid="trace-graph" role="region" aria-label="Trace graph view">
          <ReactFlow nodes={graph.nodes} edges={graph.edges} fitView onNodeClick={onNodeClick}>
            <Background />
            <Controls />
          </ReactFlow>
        </div>
      ) : (
        <ul
          className="trace-timeline"
          aria-label="Trace timeline"
          tabIndex={0}
          onKeyDown={(event) => {
            if (event.key === 'ArrowDown') {
              setSelectedIndex((prev) => Math.min(prev + 1, Math.max(0, filtered.length - 1)));
            }
            if (event.key === 'ArrowUp') {
              setSelectedIndex((prev) => Math.max(0, prev - 1));
            }
          }}
        >
          {filtered.length === 0 ? <li className="trace-empty">No events match the active filters.</li> : null}
          {filtered.map((event, idx) => (
            <li
              key={`${event.type}-${idx}`}
              className={selectedIndex === idx ? 'trace-event-item selected' : 'trace-event-item'}
              onClick={() => setSelectedIndex(idx)}
              onKeyDown={(evt) => {
                if (evt.key === 'Enter') {
                  setSelectedIndex(idx);
                }
              }}
              role="button"
              tabIndex={0}
              aria-label={`Trace event ${event.type} ${idx + 1}`}
            >
              <div className="trace-event-head">
                <strong>{event.type}</strong>
                <div className="trace-stage-badges">
                  <span className="status-pill">{stageFor(event.type)}</span>
                  <span className={`event-tone ${eventTone(event.type)}`}>{eventTone(event.type)}</span>
                </div>
              </div>
              <pre>{JSON.stringify(event, null, 2)}</pre>
            </li>
          ))}
        </ul>
      )}

      <section className="trace-details" data-testid="trace-details" aria-live="polite">
        <h4>Node Details</h4>
        <pre>{selectedEvent ? JSON.stringify(selectedEvent, null, 2) : 'No trace event selected.'}</pre>
      </section>
    </aside>
  );
}
