import type {
  Corpus,
  Diagnostics,
  EvalDetail,
  EvalListItem,
  IndexConfig,
  PolicyFinding,
  PolicySummary,
  Run,
  RunComparison,
  RunDetail,
  RuntimeConfig,
  StarterCorpusMaterialized,
  StarterCorpusPack,
  TraceEvent,
  TraceStep,
  TraceSummary,
  WatchStatus,
} from './types';

const BASE_URL = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8765';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed ${res.status}`);
  }
  if (res.status === 204) {
    return {} as T;
  }
  return (await res.json()) as T;
}

export async function listCorpora(): Promise<Corpus[]> {
  return request<Corpus[]>('/api/corpora');
}

export async function getDiagnostics(): Promise<Diagnostics> {
  return request<Diagnostics>('/api/diagnostics');
}

export async function createCorpus(payload: {
  name: string;
  path: string;
  index_config: IndexConfig;
  start_index: boolean;
}): Promise<{ corpus_id: string; index_job_id: string | null }> {
  return request('/api/corpora', { method: 'POST', body: JSON.stringify(payload) });
}

export async function listStarterCorpora(): Promise<StarterCorpusPack[]> {
  return request('/api/starter-corpora');
}

export async function materializeStarterCorpus(
  packId: string,
  payload?: { force?: boolean }
): Promise<StarterCorpusMaterialized> {
  return request(`/api/starter-corpora/${encodeURIComponent(packId)}/materialize`, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export async function startIndex(corpusId: string): Promise<{ index_job_id: string }> {
  return request('/api/index', { method: 'POST', body: JSON.stringify({ corpus_id: corpusId }) });
}

export async function getIndexJob(jobId: string): Promise<{
  job_id: string;
  status: string;
  progress: { files_total: number; files_done: number; current_path?: string | null };
  summary: Record<string, unknown>;
}> {
  return request(`/api/index/${jobId}`);
}

export async function listRuns(corpusId?: string): Promise<Run[]> {
  const params = corpusId ? `?corpus_id=${encodeURIComponent(corpusId)}` : '';
  return request<Run[]>(`/api/runs${params}`);
}

export async function createRun(payload: {
  corpus_id: string;
  messages: { role: 'user'; content: string }[];
  runtime: RuntimeConfig;
}, options?: { providerKey?: string }): Promise<{ run_id: string; status: string }> {
  const providerKey = options?.providerKey?.trim();
  const headers = providerKey
    ? {
        'X-RLM-LENS-PROVIDER-KEY': providerKey,
      }
    : undefined;
  return request('/api/runs', { method: 'POST', headers, body: JSON.stringify(payload) });
}

export async function getRun(runId: string): Promise<RunDetail> {
  return request(`/api/runs/${runId}`);
}

export async function getRunTrace(runId: string): Promise<{ run_id: string; events: { payload: TraceEvent }[] }> {
  return request(`/api/runs/${runId}/trace`);
}

export async function getRunTraceSummary(runId: string): Promise<TraceSummary> {
  return request(`/api/runs/${runId}/trace/summary`);
}

export async function getRunTraceStep(runId: string, seq?: number): Promise<TraceStep> {
  const query = seq ? `?seq=${encodeURIComponent(String(seq))}` : '';
  return request(`/api/runs/${runId}/trace/step${query}`);
}

export async function exportRun(runId: string): Promise<{ export_id: string; zip_path: string }> {
  return request(`/api/runs/${runId}/export`, { method: 'POST' });
}

export async function replayRun(runId: string): Promise<{ run_id: string; status: string }> {
  return request(`/api/runs/${runId}/replay`, { method: 'POST' });
}

export async function compareRuns(leftRunId: string, rightRunId: string): Promise<{ compare_id: string; comparison: RunComparison }> {
  return request('/api/runs/compare', {
    method: 'POST',
    body: JSON.stringify({ left_run_id: leftRunId, right_run_id: rightRunId }),
  });
}

export async function getRunComparison(compareId: string): Promise<{ compare_id: string; comparison: RunComparison }> {
  return request(`/api/runs/compare/${compareId}`);
}

export async function getRunShare(runId: string): Promise<Record<string, unknown>> {
  return request(`/api/runs/${runId}/share`);
}

export async function getFileSlice(params: {
  corpus_id: string;
  path: string;
  start_line: number;
  end_line: number;
}): Promise<{ path: string; start_line: number; end_line: number; text: string; content_hash: string }> {
  const query = new URLSearchParams({
    corpus_id: params.corpus_id,
    path: params.path,
    start_line: String(params.start_line),
    end_line: String(params.end_line),
  });
  return request(`/api/files/slice?${query.toString()}`);
}

export async function startCorpusWatch(corpusId: string, pollIntervalS: number): Promise<WatchStatus> {
  return request(`/api/corpora/${corpusId}/watch/start`, {
    method: 'POST',
    body: JSON.stringify({ poll_interval_s: pollIntervalS }),
  });
}

export async function stopCorpusWatch(corpusId: string): Promise<WatchStatus> {
  return request(`/api/corpora/${corpusId}/watch/stop`, { method: 'POST' });
}

export async function getCorpusWatch(corpusId: string): Promise<WatchStatus> {
  return request(`/api/corpora/${corpusId}/watch`);
}

export async function listWatchers(): Promise<WatchStatus[]> {
  return request('/api/watchers');
}

export async function getPolicySummary(corpusId: string): Promise<PolicySummary> {
  return request(`/api/corpora/${corpusId}/policy/summary`);
}

export async function getPolicyFindings(corpusId: string, limit = 50): Promise<PolicyFinding[]> {
  return request(`/api/corpora/${corpusId}/policy/findings?limit=${encodeURIComponent(String(limit))}`);
}

export async function createEval(payload: {
  corpus_id: string;
  queries: string[];
  runtime: RuntimeConfig;
}): Promise<{ eval_id: string; status: string }> {
  return request('/api/evals', { method: 'POST', body: JSON.stringify(payload) });
}

export async function listEvals(limit = 20): Promise<EvalListItem[]> {
  return request(`/api/evals?limit=${encodeURIComponent(String(limit))}`);
}

export async function getEval(evalId: string): Promise<EvalDetail> {
  return request(`/api/evals/${evalId}`);
}

export function subscribeRunEvents(
  runId: string,
  onEvent: (event: TraceEvent) => void,
  onError?: (event: Event) => void
): () => void {
  const source = new EventSource(`${BASE_URL}/api/runs/${runId}/events`);
  source.onmessage = (msg) => {
    const parsed = JSON.parse(msg.data) as TraceEvent;
    onEvent(parsed);
  };
  source.onerror = (event) => {
    if (onError) {
      onError(event);
    }
  };
  return () => source.close();
}

export function subscribeIndexEvents(jobId: string, onEvent: (event: TraceEvent) => void): () => void {
  const source = new EventSource(`${BASE_URL}/api/index/${jobId}/events`);
  source.onmessage = (msg) => {
    const parsed = JSON.parse(msg.data) as TraceEvent;
    onEvent(parsed);
  };
  return () => source.close();
}
