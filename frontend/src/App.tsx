import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, ArrowUpRight, Download, Keyboard, RefreshCcw, Sparkles, Wifi, WifiOff } from 'lucide-react';

import {
  compareRuns,
  createEval,
  createRun,
  exportRun,
  getCorpusWatch,
  getDiagnostics,
  getEval,
  getFileSlice,
  getPolicyFindings,
  getPolicySummary,
  getRun,
  getRunComparison,
  getRunShare,
  getRunTrace,
  getRunTraceStep,
  getRunTraceSummary,
  listCorpora,
  listEvals,
  listRuns,
  listWatchers,
  replayRun,
  startCorpusWatch,
  stopCorpusWatch,
  subscribeRunEvents,
} from './lib/api';
import {
  FALLBACK_PROVIDER_OPTIONS,
  providerDefaultModel,
  providerEnvHint,
  providerKeyReady,
  providerLabel,
  providerOptionsFromDiagnostics,
} from './lib/providers';
import type {
  Citation,
  Corpus,
  Diagnostics,
  EvalDetail,
  EvalListItem,
  PolicyFinding,
  PolicySummary,
  Run,
  RunComparison,
  RuntimeConfig,
  TraceEvent,
  TraceStep,
  TraceSummary,
  WatchStatus,
} from './lib/types';
import { CitationChips } from './components/CitationChips';
import { EvidenceViewer } from './components/EvidenceViewer';
import { Onboarding } from './components/Onboarding';
import { TracePanel } from './components/TracePanel';
import { VirtualizedList } from './components/VirtualizedList';

declare global {
  interface Window {
    __READY?: boolean;
    __RLM_LENS_DEBUG?: () => unknown;
  }
}

function readStorage(key: string): string | null {
  try {
    if (typeof window === 'undefined' || typeof window.localStorage?.getItem !== 'function') {
      return null;
    }
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(key: string, value: string): void {
  try {
    if (typeof window === 'undefined' || typeof window.localStorage?.setItem !== 'function') {
      return;
    }
    window.localStorage.setItem(key, value);
  } catch {
    // Ignore storage failures in deterministic/test environments.
  }
}

const DEFAULT_RETRIEVAL = {
  bm25_weight: 0.55,
  vector_weight: 0.35,
  rerank_weight: 0.1,
  top_k: 6,
};

const defaultRuntime: RuntimeConfig = {
  provider: 'openai',
  model: 'gpt-5-nano',
  environment: 'docker',
  max_depth: 2,
  max_iterations: 8,
  budgets: {
    max_wall_time_s: 90,
    max_subcalls: 40,
    max_tokens: null,
  },
  performance_mode: false,
  target_corpora: [],
  corpus_weights: {},
  retrieval: DEFAULT_RETRIEVAL,
};

const guidedPrompts = [
  'Map the architecture in 5 bullets with citations.',
  'Locate the retry policy and cite exact lines.',
  'Explain where schema ownership lives and cite sources.',
];

type OperationsTab = 'compare' | 'watch' | 'security' | 'evals';
type WorkspaceMode = 'command' | 'evidence' | 'trace' | 'ops';
type QualityMode = 'speed' | 'balanced' | 'deep';

function applyQualityMode(runtime: RuntimeConfig, mode: QualityMode): RuntimeConfig {
  if (mode === 'speed') {
    return {
      ...runtime,
      max_depth: 1,
      max_iterations: 4,
      performance_mode: true,
      budgets: {
        ...runtime.budgets,
        max_wall_time_s: 45,
        max_subcalls: 18,
      },
      retrieval: {
        bm25_weight: 0.6,
        vector_weight: 0.3,
        rerank_weight: 0.1,
        top_k: 4,
      },
    };
  }

  if (mode === 'deep') {
    return {
      ...runtime,
      max_depth: 3,
      max_iterations: 10,
      performance_mode: false,
      budgets: {
        ...runtime.budgets,
        max_wall_time_s: 140,
        max_subcalls: 80,
      },
      retrieval: {
        bm25_weight: 0.45,
        vector_weight: 0.35,
        rerank_weight: 0.2,
        top_k: 10,
      },
    };
  }

  return {
    ...runtime,
    max_depth: 2,
    max_iterations: 8,
    performance_mode: false,
    budgets: {
      ...runtime.budgets,
      max_wall_time_s: 90,
      max_subcalls: 40,
    },
    retrieval: {
      bm25_weight: 0.55,
      vector_weight: 0.35,
      rerank_weight: 0.1,
      top_k: 6,
    },
  };
}

function lintQuery(question: string): string[] {
  const trimmed = question.trim();
  const warnings: string[] = [];
  if (trimmed.length < 22) {
    warnings.push('Question is brief. Add target files, modules, or behaviors for stronger evidence.');
  }
  if (!/[?.:]/.test(trimmed) && trimmed.split(' ').length < 8) {
    warnings.push('Question may be vague. Ask for output format and citation expectations.');
  }
  if (!/cite|citation|line|evidence/i.test(trimmed)) {
    warnings.push('Add a citation requirement to enforce auditable output.');
  }
  return warnings;
}

function budgetImpact(runtime: RuntimeConfig): { speed: string; cost: string; coverage: string } {
  const wall = runtime.budgets.max_wall_time_s;
  const subcalls = runtime.budgets.max_subcalls;
  const topK = runtime.retrieval?.top_k ?? 6;
  const intensity = wall + subcalls * 1.2 + topK * 6 + runtime.max_iterations * 5;

  if (intensity <= 170) {
    return { speed: 'Fast', cost: 'Low', coverage: 'Focused' };
  }
  if (intensity <= 310) {
    return { speed: 'Balanced', cost: 'Medium', coverage: 'Broad' };
  }
  return { speed: 'Slow', cost: 'High', coverage: 'Deep' };
}

function commandShortcut(question: string): { command: string; suggestion: string } | null {
  const trimmed = question.trim().toLowerCase();
  if (!trimmed.startsWith('/')) {
    return null;
  }
  if (trimmed.startsWith('/compare')) {
    return { command: '/compare', suggestion: 'Switch to Ops lab and compare two completed runs.' };
  }
  if (trimmed.startsWith('/evaluate')) {
    return { command: '/evaluate', suggestion: 'Switch to evals tab and run a benchmark query set.' };
  }
  if (trimmed.startsWith('/watch')) {
    return { command: '/watch', suggestion: 'Switch to watch tab and start corpus watcher.' };
  }
  return { command: trimmed.split(' ')[0], suggestion: 'Unknown command. Try /compare, /evaluate, or /watch.' };
}

function parseAnswerSections(answer: string): { summary: string; details: string[]; raw: string } {
  const lines = answer.split('\n').map((line) => line.trim());
  const summaryLines: string[] = [];
  const detailLines: string[] = [];
  let inSummary = false;
  let inDetails = false;

  for (const line of lines) {
    const lower = line.toLowerCase();
    if (lower.startsWith('## summary')) {
      inSummary = true;
      inDetails = false;
      continue;
    }
    if (lower.startsWith('## evidence')) {
      inSummary = false;
      inDetails = true;
      continue;
    }
    if (line.startsWith('## ')) {
      inSummary = false;
      inDetails = false;
      continue;
    }
    if (!line) continue;
    if (inSummary) summaryLines.push(line);
    if (inDetails) detailLines.push(line.replace(/^-+\s*/, ''));
  }

  return {
    summary: summaryLines.join(' '),
    details: detailLines,
    raw: answer,
  };
}

function followUpSuggestions(question: string, details: string[]): string[] {
  const suggestions = [
    'List risky assumptions and cite where each assumption appears.',
    'Explain what evidence is missing and which files should be inspected next.',
    'Compare this answer with the previous run and show citation overlap.',
  ];
  if (/schema|database|migration/i.test(question)) {
    suggestions.unshift('Trace schema ownership and quote exact migration files.');
  }
  if (details.length === 0) {
    suggestions.unshift('Expand this answer into 5 bullet points with exact line citations.');
  }
  return suggestions.slice(0, 3);
}

function fixtureEvents(seed: number): TraceEvent[] {
  return [
    {
      type: 'run.metadata',
      timestamp: '2026-02-23T12:00:00Z',
      root_model: 'gpt-5-nano',
      max_depth: 2,
      seed,
    },
    {
      type: 'run.iteration',
      timestamp: '2026-02-23T12:00:01Z',
      iteration: 1,
      prompt: 'Search for retry policy',
      response: 'Reading files...',
    },
    {
      type: 'run.code_block',
      timestamp: '2026-02-23T12:00:02Z',
      iteration: 1,
      code: "lens.read('src/retry_policy.py', 1, 40)",
    },
    {
      type: 'run.subcall',
      timestamp: '2026-02-23T12:00:03Z',
      iteration: 1,
      prompt: 'Summarize retry semantics',
      response: 'Policy found in RetryPolicy dataclass and with_retries.',
    },
    {
      type: 'run.complete',
      timestamp: '2026-02-23T12:00:04Z',
      status: 'succeeded',
    },
  ];
}

function fixtureCitations(): Citation[] {
  return [
    {
      citation_id: 'cit_fixture_1',
      path: 'src/retry_policy.py',
      start_line: 12,
      end_line: 28,
      snippet: 'class RetryPolicy:\n    max_attempts: int = 5\n',
    },
    {
      citation_id: 'cit_fixture_2',
      path: 'src/api.py',
      start_line: 15,
      end_line: 22,
      snippet: 'return with_retries(lambda: client.charge(...), DEFAULT_RETRY_POLICY)\n',
    },
  ];
}

function testDiagnostics(simulateNoKey: boolean, simulateDockerMissing: boolean): Diagnostics {
  const available = FALLBACK_PROVIDER_OPTIONS.map((provider) => ({
    ...provider,
    key_present: provider.id === 'openai' ? !simulateNoKey : false,
  }));
  const keysPresent = Object.fromEntries(available.map((provider) => [provider.id, provider.key_present]));
  return {
    provider: {
      openai_api_key_present: !simulateNoKey,
      selected: 'openai',
      keys_present: keysPresent,
      available,
      byok_header_supported: true,
      byok_header_name: 'X-RLM-LENS-PROVIDER-KEY',
      session_key_storage: 'ephemeral_request_header_only',
    },
    environment: {
      docker_installed: !simulateDockerMissing,
      docker_running: !simulateDockerMissing,
    },
  };
}

function fixtureWatchStatus(corpusId: string, disconnected: boolean): WatchStatus {
  return {
    corpus_id: corpusId,
    status: disconnected ? 'error' : 'running',
    poll_interval_s: 12,
    last_checked_at: '2026-02-23T12:00:05Z',
    last_change_at: '2026-02-23T12:00:04Z',
    fingerprint: 'sha256:fixture',
    error: disconnected ? { message: 'Watcher heartbeat delayed.' } : null,
  };
}

function fixturePolicySummary(corpusId: string): PolicySummary {
  return {
    corpus_id: corpusId,
    total_findings: 3,
    totals: [
      { category: 'email', severity: 'medium', count: 1 },
      { category: 'openai_key', severity: 'critical', count: 1 },
      { category: 'phone', severity: 'low', count: 1 },
    ],
  };
}

function fixturePolicyFindings(): PolicyFinding[] {
  return [
    {
      id: 'pii_fixture_1',
      path: 'src/config.md',
      line_no: 42,
      category: 'openai_key',
      severity: 'critical',
      preview: 'OPENAI_API_KEY=sk-...masked...',
      found_at: '2026-02-23T12:00:05Z',
    },
    {
      id: 'pii_fixture_2',
      path: 'docs/contacts.md',
      line_no: 12,
      category: 'email',
      severity: 'medium',
      preview: 'Contact support@example.com',
      found_at: '2026-02-23T12:00:04Z',
    },
  ];
}

function fixtureEvalList(): EvalListItem[] {
  return [
    {
      eval_id: 'eval_fixture_1',
      status: 'succeeded',
      created_at: '2026-02-23T12:00:00Z',
      started_at: '2026-02-23T12:00:01Z',
      finished_at: '2026-02-23T12:00:04Z',
      summary: {
        total_runs: 3,
        success_rate: 1,
        avg_grounding: 0.91,
      },
    },
  ];
}

function fixtureEvalDetail(): EvalDetail {
  return {
    eval_id: 'eval_fixture_1',
    status: 'succeeded',
    created_at: '2026-02-23T12:00:00Z',
    started_at: '2026-02-23T12:00:01Z',
    finished_at: '2026-02-23T12:00:04Z',
    config: {},
    summary: {
      total_runs: 3,
      success_rate: 1,
      avg_grounding: 0.91,
      avg_citations: 2.7,
      avg_wall_time_s: 1.2,
    },
    details: {
      runs: [
        {
          run_id: 'run_fixture_a',
          query: 'where retry policy',
          status: 'succeeded',
          citations: 2,
          grounding_score: 0.9,
          wall_time_s: 1.1,
        },
      ],
    },
  };
}

function groundingLabel(score: number | null): string {
  if (score === null) return 'Pending grounding';
  return `Grounding ${Math.round(score * 100)}%`;
}

function groundingTone(score: number | null): 'high' | 'mid' | 'low' {
  if (score === null) return 'mid';
  if (score >= 0.85) return 'high';
  if (score >= 0.7) return 'mid';
  return 'low';
}

function App() {
  const queryParams = useMemo(() => new URLSearchParams(window.location.search), []);
  const isDemoMode = queryParams.get('demo') === '1';
  const isTestMode = queryParams.get('test_mode') === '1';
  const isStaticMode = queryParams.get('static') === '1';
  const debugMode = queryParams.get('debug') === '1';
  const simulateNoKey = queryParams.get('simulate_no_key') === '1';
  const simulateDockerMissing = queryParams.get('simulate_docker_missing') === '1';
  const simulateDisconnect = queryParams.get('simulate_disconnect') === '1';
  const testSeed = Number(queryParams.get('seed') ?? '42');

  const initialPrompt = isDemoMode
    ? 'Find the retry policy and cite exact line ranges.'
    : 'Summarize the architecture and cite top files.';

  const [corpora, setCorpora] = useState<Corpus[]>([]);
  const [selectedCorpusId, setSelectedCorpusId] = useState<string | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [question, setQuestion] = useState(initialPrompt);
  const [answer, setAnswer] = useState<string>('');
  const [citations, setCitations] = useState<Citation[]>([]);
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [runtime, setRuntime] = useState<RuntimeConfig>(defaultRuntime);
  const [busy, setBusy] = useState(false);
  const [runStatus, setRunStatus] = useState<string>('idle');
  const [error, setError] = useState<string | null>(null);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [activeCitationIndex, setActiveCitationIndex] = useState(-1);
  const [evidencePadding, setEvidencePadding] = useState(5);
  const [evidenceText, setEvidenceText] = useState('');
  const [lastExportPath, setLastExportPath] = useState<string | null>(null);
  const [runtimeWarnings, setRuntimeWarnings] = useState<string[]>([]);
  const [groundingScore, setGroundingScore] = useState<number | null>(null);
  const [groundingClaimsTotal, setGroundingClaimsTotal] = useState<number | null>(null);
  const [groundingUngroundedClaims, setGroundingUngroundedClaims] = useState<string[]>([]);
  const [diagnostics, setDiagnostics] = useState<Diagnostics | null>(null);
  const [connectionState, setConnectionState] = useState<'idle' | 'connected' | 'disconnected'>('idle');
  const [operationsTab, setOperationsTab] = useState<OperationsTab>('security');
  const [workspaceMode, setWorkspaceMode] = useState<WorkspaceMode>('command');
  const [qualityMode, setQualityMode] = useState<QualityMode>('balanced');
  const [showAdvancedComposer, setShowAdvancedComposer] = useState(false);
  const [compareLeftRunId, setCompareLeftRunId] = useState<string | null>(null);
  const [compareRightRunId, setCompareRightRunId] = useState<string | null>(null);
  const [comparisonId, setComparisonId] = useState<string | null>(null);
  const [comparison, setComparison] = useState<RunComparison | null>(null);
  const [savedComparisons, setSavedComparisons] = useState<Array<{ id: string; left: string; right: string; note: string }>>(
    []
  );
  const [watchStatus, setWatchStatus] = useState<WatchStatus | null>(null);
  const [watchers, setWatchers] = useState<WatchStatus[]>([]);
  const [watchPollInterval, setWatchPollInterval] = useState(20);
  const [policySummary, setPolicySummary] = useState<PolicySummary | null>(null);
  const [policyFindings, setPolicyFindings] = useState<PolicyFinding[]>([]);
  const [findingState, setFindingState] = useState<Record<string, 'new' | 'accepted' | 'resolved'>>({});
  const [evalQueries, setEvalQueries] = useState('where retry policy\nsummarize architecture');
  const [evalPreset, setEvalPreset] = useState<'smoke' | 'regression' | 'deep'>('smoke');
  const [evals, setEvals] = useState<EvalListItem[]>([]);
  const [activeEval, setActiveEval] = useState<EvalDetail | null>(null);
  const [traceSummary, setTraceSummary] = useState<TraceSummary | null>(null);
  const [traceStep, setTraceStep] = useState<TraceStep | null>(null);
  const [sharePreview, setSharePreview] = useState<Record<string, unknown> | null>(null);
  const [runAnnouncement, setRunAnnouncement] = useState('Idle');
  const [showShortcutHelp, setShowShortcutHelp] = useState(false);
  const [sessionProviderKeys, setSessionProviderKeys] = useState<Record<string, string>>({});

  useEffect(() => {
    window.__READY = false;
    if (isTestMode) {
      const corpus: Corpus = {
        id: 'cor_fixture',
        name: 'Fixture Corpus',
        path: '/fixtures/sample',
      };
      const run: Run = {
        id: 'run_fixture',
        corpus_id: corpus.id,
        status: 'succeeded',
        created_at: '2026-02-23T12:00:00Z',
        answer_preview: 'Retry policy is defined in src/retry_policy.py and used in src/api.py',
      };
      setCorpora([corpus]);
      setSelectedCorpusId(corpus.id);
      setRuns([run]);
      setSelectedRunId(run.id);
      setCitations(fixtureCitations());
      setEvents(fixtureEvents(testSeed));
      setRunStatus('succeeded');
      setGroundingScore(0.92);
      setGroundingClaimsTotal(4);
      setGroundingUngroundedClaims(['Payment timeout behavior for third-party provider is inferred.']);
      setRuntimeWarnings(
        simulateDisconnect ? ['Event stream disconnected. Click reconnect to refresh trace stream.'] : []
      );
      setDiagnostics(testDiagnostics(simulateNoKey, simulateDockerMissing));
      setConnectionState(simulateDisconnect ? 'disconnected' : 'connected');
      setCompareLeftRunId(run.id);
      setCompareRightRunId(run.id);
      setComparison({
        left_run_id: run.id,
        right_run_id: run.id,
        left_status: 'succeeded',
        right_status: 'succeeded',
        left_citations: 2,
        right_citations: 2,
        overlap_paths: ['cor_fixture:src/retry_policy.py'],
        overlap_ratio: 1,
        left_grounding: 0.92,
        right_grounding: 0.92,
      });
      setComparisonId('cmp_fixture');
      setWatchStatus(fixtureWatchStatus(corpus.id, simulateDisconnect));
      setWatchers([fixtureWatchStatus(corpus.id, simulateDisconnect)]);
      setPolicySummary(fixturePolicySummary(corpus.id));
      setPolicyFindings(fixturePolicyFindings());
      setEvals(fixtureEvalList());
      setActiveEval(fixtureEvalDetail());
      setTraceSummary({
        run_id: run.id,
        events_total: 5,
        type_counts: { metadata: 1, iteration: 1, complete: 1 },
        iterations: [1],
        first_event_ts: '2026-02-23T12:00:00Z',
        last_event_ts: '2026-02-23T12:00:04Z',
        last_seq: 3,
      });
      setTraceStep({
        run_id: run.id,
        seq: 3,
        timestamp: '2026-02-23T12:00:04Z',
        type: 'complete',
        payload: { status: 'succeeded' },
      });
      setAnswer(
        '## Summary\nRetry policy is implemented in `src/retry_policy.py` and consumed in `src/api.py`.\n\n' +
          '## Evidence-backed details\n- Retry behavior is configured by `RetryPolicy` dataclass.\n' +
          '- Payment calls are wrapped with `with_retries(...)`.\n'
      );
      queueMicrotask(() => {
        window.__READY = true;
      });
      return;
    }

    void (async () => {
      const [items, diag] = await Promise.all([listCorpora(), getDiagnostics()]);
      setCorpora(items);
      setDiagnostics(diag);
      if (items.length > 0) {
        setSelectedCorpusId(items[0].id);
      }
      window.__READY = true;
    })();
  }, [isTestMode, simulateDisconnect, simulateDockerMissing, simulateNoKey, testSeed]);

  useEffect(() => {
    if (isTestMode || !selectedCorpusId) {
      return;
    }

    void (async () => {
      const data = await listRuns(selectedCorpusId);
      setRuns(data);
      if (!selectedRunId && data.length > 0) {
        setSelectedRunId(data[0].id);
      }
      if (!compareLeftRunId && data.length > 0) {
        setCompareLeftRunId(data[0].id);
      }
      if (!compareRightRunId && data.length > 1) {
        setCompareRightRunId(data[1].id);
      } else if (!compareRightRunId && data.length > 0) {
        setCompareRightRunId(data[0].id);
      }
    })();
  }, [compareLeftRunId, compareRightRunId, isTestMode, selectedCorpusId, selectedRunId]);

  useEffect(() => {
    if (isTestMode || !selectedCorpusId) {
      return;
    }
    void (async () => {
      const [watch, watcherItems, policy, findings, evalItems] = await Promise.all([
        getCorpusWatch(selectedCorpusId),
        listWatchers(),
        getPolicySummary(selectedCorpusId),
        getPolicyFindings(selectedCorpusId, 40),
        listEvals(20),
      ]);
      setWatchStatus(watch);
      setWatchers(watcherItems);
      setPolicySummary(policy);
      setPolicyFindings(findings);
      setEvals(evalItems);
    })();
  }, [isTestMode, selectedCorpusId]);

  useEffect(() => {
    if (isTestMode || !selectedRunId) {
      return;
    }

    void (async () => {
      const [trace, detail] = await Promise.all([getRunTrace(selectedRunId), getRun(selectedRunId)]);
      setEvents(trace.events.map((item) => item.payload));
      setAnswer(detail.final_answer ?? 'No answer saved for this run.');
      setCitations(detail.citations);
      setRunStatus(detail.status);
      setRuntimeWarnings(Array.isArray(detail.usage.warnings) ? (detail.usage.warnings as string[]) : []);
      const score = detail.usage.grounding?.grounding_score;
      setGroundingScore(typeof score === 'number' ? score : null);
      const claimsTotal = detail.usage.grounding?.claims_total;
      setGroundingClaimsTotal(typeof claimsTotal === 'number' ? claimsTotal : null);
      const ungrounded = detail.usage.grounding?.claims_ungrounded;
      setGroundingUngroundedClaims(Array.isArray(ungrounded) ? ungrounded : []);
      setConnectionState('connected');
      try {
        const summary = await getRunTraceSummary(selectedRunId);
        setTraceSummary(summary);
      } catch {
        setTraceSummary(null);
      }
      try {
        const step = await getRunTraceStep(selectedRunId);
        setTraceStep(step);
      } catch {
        setTraceStep(null);
      }
      setSharePreview(null);
    })();
  }, [isTestMode, selectedRunId]);

  useEffect(() => {
    try {
      const savedRaw = readStorage('rlm_lens_saved_comparisons');
      if (savedRaw) {
        const parsed = JSON.parse(savedRaw) as Array<{ id: string; left: string; right: string; note: string }>;
        if (Array.isArray(parsed)) {
          setSavedComparisons(parsed.slice(0, 10));
        }
      }
      const findingRaw = readStorage('rlm_lens_finding_state');
      if (findingRaw) {
        const parsed = JSON.parse(findingRaw) as Record<string, 'new' | 'accepted' | 'resolved'>;
        if (parsed && typeof parsed === 'object') {
          setFindingState(parsed);
        }
      }
    } catch {
      // Ignore cache parse failures.
    }
  }, []);

  useEffect(() => {
    writeStorage('rlm_lens_saved_comparisons', JSON.stringify(savedComparisons.slice(0, 10)));
  }, [savedComparisons]);

  useEffect(() => {
    writeStorage('rlm_lens_finding_state', JSON.stringify(findingState));
  }, [findingState]);

  useEffect(() => {
    window.__RLM_LENS_DEBUG = () => ({
      isTestMode,
      isStaticMode,
      runStatus,
      corpusCount: corpora.length,
      runCount: runs.length,
      citationCount: citations.length,
      eventCount: events.length,
      runtimeWarnings,
      groundingScore,
      groundingClaimsTotal,
      groundingUngroundedClaims,
      diagnostics,
      provider: runtime.provider,
      providerLabel: providerLabel(runtime.provider, diagnostics),
      providerKeyReady:
        providerKeyReady(runtime.provider, diagnostics) || (sessionProviderKeys[runtime.provider] ?? '').trim().length > 0,
      connectionState,
      operationsTab,
      workspaceMode,
      qualityMode,
      comparisonId,
      savedComparisonCount: savedComparisons.length,
      watchStatus,
      policySummary,
      policyFindingsCount: policyFindings.length,
      findingStateCount: Object.keys(findingState).length,
      evalCount: evals.length,
      evalPreset,
      traceSummary,
      traceStepType: traceStep?.type,
      question,
      selectedCorpusId,
      selectedRunId,
    });
  }, [
    citations.length,
    connectionState,
    corpora.length,
    diagnostics,
    events.length,
    groundingScore,
    groundingClaimsTotal,
    groundingUngroundedClaims,
    isStaticMode,
    isTestMode,
    runtime.provider,
    operationsTab,
    workspaceMode,
    qualityMode,
    comparisonId,
    savedComparisons.length,
    watchStatus,
    policySummary,
    policyFindings.length,
    findingState,
    evals.length,
    evalPreset,
    traceSummary,
    traceStep?.type,
    question,
    runStatus,
    runs.length,
    runtimeWarnings,
    sessionProviderKeys,
    selectedCorpusId,
    selectedRunId,
  ]);

  useEffect(() => {
    if (runStatus === 'running') {
      setRunAnnouncement('Run started. Trace stream active.');
      return;
    }
    if (runStatus === 'succeeded') {
      setRunAnnouncement('Run completed successfully. Evidence is ready.');
      return;
    }
    if (runStatus === 'failed') {
      setRunAnnouncement('Run failed. Review warnings and trace errors.');
      return;
    }
    if (runStatus === 'partial_budget_exceeded') {
      setRunAnnouncement('Run ended at budget limits. Increase limits or narrow query.');
      return;
    }
    setRunAnnouncement('Idle');
  }, [runStatus]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const isFormTarget =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement ||
        target?.isContentEditable === true;
      if (event.key === '?' && !event.metaKey && !event.ctrlKey && !event.altKey && !isFormTarget) {
        event.preventDefault();
        setShowShortcutHelp((prev) => !prev);
        return;
      }
      if (event.key === 'Escape') {
        setShowShortcutHelp(false);
      }
      const isRunShortcut = (event.metaKey || event.ctrlKey) && event.key === 'Enter';
      if (!isRunShortcut || busy || !selectedCorpusId) {
        return;
      }
      event.preventDefault();
      if (event.shiftKey) {
        setRuntime((prev) => ({
          ...prev,
          performance_mode: true,
          budgets: { ...prev.budgets, max_wall_time_s: Math.max(30, Math.min(prev.budgets.max_wall_time_s, 60)) },
        }));
      }
      void runQuery();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  });

  const selectedCorpus = useMemo(
    () => corpora.find((corpus) => corpus.id === selectedCorpusId) ?? null,
    [corpora, selectedCorpusId]
  );

  const completedRuns = useMemo(() => runs.filter((run) => run.status === 'succeeded').length, [runs]);
  const selectedRun = useMemo(() => runs.find((run) => run.id === selectedRunId) ?? null, [runs, selectedRunId]);
  const queryWarnings = useMemo(() => lintQuery(question), [question]);
  const impact = useMemo(() => budgetImpact(runtime), [runtime]);
  const shortcut = useMemo(() => commandShortcut(question), [question]);
  const providerOptions = useMemo(() => providerOptionsFromDiagnostics(diagnostics), [diagnostics]);
  const selectedProviderLabel = useMemo(() => providerLabel(runtime.provider, diagnostics), [diagnostics, runtime.provider]);
  const selectedProviderEnvHint = useMemo(() => providerEnvHint(runtime.provider, diagnostics), [diagnostics, runtime.provider]);
  const selectedProviderKeyReady = useMemo(() => providerKeyReady(runtime.provider, diagnostics), [diagnostics, runtime.provider]);
  const sessionProviderKey = useMemo(() => sessionProviderKeys[runtime.provider] ?? '', [runtime.provider, sessionProviderKeys]);
  const runtimeProviderKeyReady = useMemo(
    () => selectedProviderKeyReady || sessionProviderKey.trim().length > 0,
    [selectedProviderKeyReady, sessionProviderKey]
  );
  const parsedAnswer = useMemo(() => parseAnswerSections(answer), [answer]);
  const nextPrompts = useMemo(() => followUpSuggestions(question, parsedAnswer.details), [parsedAnswer.details, question]);
  const completeness = useMemo(() => {
    if (!groundingClaimsTotal || groundingClaimsTotal <= 0) {
      return null;
    }
    const grounded = groundingClaimsTotal - groundingUngroundedClaims.length;
    return Math.max(0, Math.min(1, grounded / groundingClaimsTotal));
  }, [groundingClaimsTotal, groundingUngroundedClaims.length]);
  const previousRun = useMemo(() => {
    if (!selectedRunId) return null;
    const index = runs.findIndex((run) => run.id === selectedRunId);
    if (index <= 0) return null;
    return runs[index - 1] ?? null;
  }, [runs, selectedRunId]);

  const openCitation = async (citation: Citation, index?: number, padding = 5) => {
    if (isTestMode) {
      setEvidenceText(citation.snippet);
      setActiveCitation(citation);
      setActiveCitationIndex(typeof index === 'number' ? index : citations.findIndex((item) => item.citation_id === citation.citation_id));
      setEvidencePadding(padding);
      setEvidenceOpen(true);
      setWorkspaceMode('evidence');
      return;
    }

    setEvidenceText(citation.snippet || 'Loading file slice...');
    setActiveCitation(citation);
    setActiveCitationIndex(typeof index === 'number' ? index : citations.findIndex((item) => item.citation_id === citation.citation_id));
    setEvidencePadding(padding);
    setEvidenceOpen(true);
    setWorkspaceMode('evidence');

    const citationCorpusId = citation.corpus_id || selectedCorpusId;
    if (!citationCorpusId) return;
    try {
      const slice = await getFileSlice({
        corpus_id: citationCorpusId,
        path: citation.path,
        start_line: Math.max(1, citation.start_line - padding),
        end_line: citation.end_line + padding + 7,
      });
      setEvidenceText(slice.text);
    } catch {
      setEvidenceText(citation.snippet || 'Unable to load file slice. Showing citation snippet fallback.');
    }
  };

  const moveCitation = (direction: -1 | 1) => {
    if (citations.length === 0) {
      return;
    }
    const currentIndex = activeCitationIndex >= 0 ? activeCitationIndex : 0;
    const nextIndex = Math.max(0, Math.min(citations.length - 1, currentIndex + direction));
    const citation = citations[nextIndex];
    if (citation) {
      void openCitation(citation, nextIndex, evidencePadding);
    }
  };

  const expandCitation = (delta: number) => {
    if (!activeCitation) {
      return;
    }
    const nextPadding = Math.max(2, Math.min(80, evidencePadding + delta));
    void openCitation(activeCitation, activeCitationIndex, nextPadding);
  };

  const reconnectTrace = async () => {
    if (!selectedRunId) {
      return;
    }
    if (isTestMode) {
      setConnectionState('connected');
      setRuntimeWarnings((prev) => prev.filter((warning) => !warning.includes('disconnected')));
      return;
    }
    const trace = await getRunTrace(selectedRunId);
    setEvents(trace.events.map((item) => item.payload));
    setConnectionState('connected');
    setRuntimeWarnings((prev) => prev.filter((warning) => !warning.includes('disconnected')));
  };

  const runQuery = async () => {
    if (!selectedCorpusId) return;
    if (shortcut?.command === '/compare') {
      setWorkspaceMode('ops');
      setOperationsTab('compare');
      return;
    }
    if (shortcut?.command === '/evaluate') {
      setWorkspaceMode('ops');
      setOperationsTab('evals');
      return;
    }
    if (shortcut?.command === '/watch') {
      setWorkspaceMode('ops');
      setOperationsTab('watch');
      return;
    }

    setBusy(true);
    setWorkspaceMode('trace');
    setError(null);
    setAnswer('');
    setCitations([]);
    setEvents([]);
    setRunStatus('running');
    setRuntimeWarnings([]);
    setGroundingClaimsTotal(null);
    setGroundingUngroundedClaims([]);
    setConnectionState('idle');

    try {
      if (isTestMode) {
        const syntheticEvents = fixtureEvents(testSeed + 1);
        if (!isStaticMode) {
          for (const event of syntheticEvents) {
            setEvents((prev) => [...prev, event]);
            await new Promise((resolve) => setTimeout(resolve, 20));
          }
        } else {
          setEvents(syntheticEvents);
        }

        setCitations(fixtureCitations());
        setAnswer(
          `## Summary\nTest-mode answer for: ${question}\n\n` +
            '## Evidence-backed details\n- This response is deterministic for visual verification.\n'
        );
        setGroundingScore(0.88);
        setGroundingClaimsTotal(3);
        setGroundingUngroundedClaims(['Database ownership remains partially inferred.']);
        setRunStatus('succeeded');
        setWorkspaceMode('evidence');
        setConnectionState(simulateDisconnect ? 'disconnected' : 'connected');
        if (simulateDisconnect) {
          setRuntimeWarnings(['Event stream disconnected. Click reconnect to refresh trace stream.']);
        }
        return;
      }

      const run = await createRun({
        corpus_id: selectedCorpusId,
        messages: [{ role: 'user', content: question }],
        runtime,
      }, {
        providerKey: sessionProviderKey.trim().length > 0 ? sessionProviderKey : undefined,
      });
      setSelectedRunId(run.run_id);

      const unsubscribe = subscribeRunEvents(
        run.run_id,
        (event) => {
          setEvents((prev) => [...prev, event]);
          setConnectionState('connected');
        },
        () => {
          setConnectionState('disconnected');
          setRuntimeWarnings((prev) =>
            prev.includes('Event stream disconnected. Click reconnect to refresh trace stream.')
              ? prev
              : [...prev, 'Event stream disconnected. Click reconnect to refresh trace stream.']
          );
        }
      );

      for (let i = 0; i < 320; i += 1) {
        const detail = await getRun(run.run_id);
        if (detail.final_answer) {
          setAnswer(detail.final_answer);
        }
        setCitations(detail.citations);
        setRunStatus(detail.status);
        setRuntimeWarnings(Array.isArray(detail.usage.warnings) ? (detail.usage.warnings as string[]) : []);
        const score = detail.usage.grounding?.grounding_score;
        setGroundingScore(typeof score === 'number' ? score : null);
        const claimsTotal = detail.usage.grounding?.claims_total;
        setGroundingClaimsTotal(typeof claimsTotal === 'number' ? claimsTotal : null);
        const ungrounded = detail.usage.grounding?.claims_ungrounded;
        setGroundingUngroundedClaims(Array.isArray(ungrounded) ? ungrounded : []);

        if (
          detail.status === 'succeeded' ||
          detail.status === 'partial_budget_exceeded' ||
          detail.status === 'failed'
        ) {
          if (detail.status === 'succeeded' || detail.status === 'partial_budget_exceeded') {
            setWorkspaceMode('evidence');
          }
          break;
        }
        await new Promise((resolve) => setTimeout(resolve, 250));
      }

      unsubscribe();
      const freshRuns = await listRuns(selectedCorpusId);
      setRuns(freshRuns);
      try {
        const summary = await getRunTraceSummary(run.run_id);
        setTraceSummary(summary);
      } catch {
        setTraceSummary(null);
      }
      try {
        const step = await getRunTraceStep(run.run_id);
        setTraceStep(step);
      } catch {
        setTraceStep(null);
      }
      if (!compareLeftRunId) {
        setCompareLeftRunId(run.run_id);
      } else if (!compareRightRunId) {
        setCompareRightRunId(run.run_id);
      }
    } catch (caught) {
      setRunStatus('failed');
      setError(caught instanceof Error ? caught.message : 'Run failed unexpectedly');
    } finally {
      setBusy(false);
    }
  };

  const exportCurrentRun = async () => {
    if (!selectedRunId) return;
    const result = await exportRun(selectedRunId);
    setLastExportPath(result.zip_path);
  };

  const replayCurrentRun = async () => {
    if (!selectedRunId) return;
    const replay = await replayRun(selectedRunId);
    setSelectedRunId(replay.run_id);
  };

  const compareSelectedRuns = async () => {
    if (!compareLeftRunId || !compareRightRunId) {
      return;
    }
    if (isTestMode) {
      setComparison({
        left_run_id: compareLeftRunId,
        right_run_id: compareRightRunId,
        left_status: 'succeeded',
        right_status: 'succeeded',
        left_citations: 2,
        right_citations: 2,
        overlap_paths: ['cor_fixture:src/retry_policy.py'],
        overlap_ratio: 1,
      });
      setComparisonId('cmp_fixture');
      return;
    }
    const result = await compareRuns(compareLeftRunId, compareRightRunId);
    setComparisonId(result.compare_id);
    setComparison(result.comparison);
  };

  const saveComparisonSession = () => {
    if (!compareLeftRunId || !compareRightRunId) {
      return;
    }
    const id = comparisonId ?? `cmp_${Date.now()}`;
    const note = comparison ? `Overlap ${Math.round(comparison.overlap_ratio * 100)}%` : 'Saved compare pair';
    setSavedComparisons((prev) => [{ id, left: compareLeftRunId, right: compareRightRunId, note }, ...prev].slice(0, 10));
  };

  const reloadComparison = async () => {
    if (!comparisonId || isTestMode) {
      return;
    }
    const result = await getRunComparison(comparisonId);
    setComparison(result.comparison);
  };

  const openSharePreview = async () => {
    if (!selectedRunId) {
      return;
    }
    if (isTestMode) {
      setSharePreview({ run_id: selectedRunId, mode: 'fixture' });
      return;
    }
    const payload = await getRunShare(selectedRunId);
    setSharePreview(payload);
  };

  const startWatch = async () => {
    if (!selectedCorpusId) {
      return;
    }
    if (isTestMode) {
      const status = fixtureWatchStatus(selectedCorpusId, false);
      setWatchStatus(status);
      setWatchers([status]);
      return;
    }
    const status = await startCorpusWatch(selectedCorpusId, watchPollInterval);
    const items = await listWatchers();
    setWatchStatus(status);
    setWatchers(items);
  };

  const stopWatch = async () => {
    if (!selectedCorpusId) {
      return;
    }
    if (isTestMode) {
      setWatchStatus((prev) =>
        prev
          ? {
              ...prev,
              status: 'stopped',
            }
          : {
              corpus_id: selectedCorpusId,
              status: 'stopped',
              poll_interval_s: watchPollInterval,
            }
      );
      return;
    }
    const status = await stopCorpusWatch(selectedCorpusId);
    const items = await listWatchers();
    setWatchStatus(status);
    setWatchers(items);
  };

  const refreshPolicy = async () => {
    if (!selectedCorpusId) {
      return;
    }
    if (isTestMode) {
      setPolicySummary(fixturePolicySummary(selectedCorpusId));
      setPolicyFindings(fixturePolicyFindings());
      return;
    }
    const [summary, findings] = await Promise.all([
      getPolicySummary(selectedCorpusId),
      getPolicyFindings(selectedCorpusId, 80),
    ]);
    setPolicySummary(summary);
    setPolicyFindings(findings);
  };

  const runEvaluation = async () => {
    if (!selectedCorpusId) {
      return;
    }
    const presetQueries =
      evalPreset === 'regression'
        ? ['where retry policy', 'summarize architecture', 'find schema ownership']
        : evalPreset === 'deep'
          ? ['map architecture with citations', 'explain retrieval tuning tradeoffs', 'list unresolved risks']
          : ['where retry policy', 'summarize architecture'];
    const source = evalQueries.trim().length > 0 ? evalQueries : presetQueries.join('\n');
    const queries = source
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line.length > 0);
    if (queries.length === 0) {
      return;
    }
    if (isTestMode) {
      const fixture = fixtureEvalDetail();
      setActiveEval(fixture);
      setEvals(fixtureEvalList());
      return;
    }
    const created = await createEval({ corpus_id: selectedCorpusId, queries, runtime });
    for (let i = 0; i < 240; i += 1) {
      const detail = await getEval(created.eval_id);
      setActiveEval(detail);
      if (detail.status === 'succeeded' || detail.status === 'failed') {
        break;
      }
      await new Promise((resolve) => setTimeout(resolve, 300));
    }
    const items = await listEvals(20);
    setEvals(items);
  };

  const setQualityPreset = (mode: QualityMode) => {
    setQualityMode(mode);
    setRuntime((prev) => applyQualityMode(prev, mode));
  };

  if (!selectedCorpus) {
    return (
      <main className="app-shell" data-testid="app-shell">
        <Onboarding
          onReady={({ corpusId, runtime: runtimeFromOnboarding }) => {
            setRuntime({
              ...defaultRuntime,
              ...runtimeFromOnboarding,
              budgets: {
                ...defaultRuntime.budgets,
                ...runtimeFromOnboarding.budgets,
              },
              retrieval: {
                bm25_weight: runtimeFromOnboarding.retrieval?.bm25_weight ?? DEFAULT_RETRIEVAL.bm25_weight,
                vector_weight: runtimeFromOnboarding.retrieval?.vector_weight ?? DEFAULT_RETRIEVAL.vector_weight,
                rerank_weight: runtimeFromOnboarding.retrieval?.rerank_weight ?? DEFAULT_RETRIEVAL.rerank_weight,
                top_k: runtimeFromOnboarding.retrieval?.top_k ?? DEFAULT_RETRIEVAL.top_k,
              },
            });
            setSelectedCorpusId(corpusId);
            void listCorpora().then((items) => setCorpora(items));
          }}
        />
      </main>
    );
  }

  return (
    <main
      className={`app-shell workspace-shell mode-${workspaceMode} ${isStaticMode ? 'static-mode' : ''}`}
      data-testid="app-shell"
      data-test-mode={isTestMode ? '1' : '0'}
    >
      <nav className="skip-links" aria-label="Skip links">
        <a href="#command-panel">Skip to command</a>
        <a href="#answer-panel">Skip to answer</a>
        <a href="#trace-panel">Skip to trace</a>
        <a href="#ops-panel">Skip to operations</a>
      </nav>
      <p className="sr-only" aria-live="polite">
        {runAnnouncement}
      </p>
      <header className="topbar command-header" data-testid="topbar">
        <div className="brand-block">
          <p className="kicker">RLM Lens</p>
          <h1>{selectedCorpus.name}</h1>
          <p className="status-label">Ask once. Verify with line-level evidence.</p>
          <p className="breadcrumb-copy">
            Workspace / {selectedCorpus.name} / {selectedRunId ?? 'No run selected'}
          </p>
        </div>

        <div className="top-metrics">
          <div className="metric-card">
            <span>Run</span>
            <strong className="capitalize">{runStatus}</strong>
          </div>
          <div className="metric-card">
            <span>Grounding</span>
            <strong>{groundingLabel(groundingScore)}</strong>
          </div>
          <div className="metric-card">
            <span>Successful runs</span>
            <strong>{completedRuns}</strong>
          </div>
        </div>
      </header>

      <section className="status-grid status-ribbon" aria-label="Runtime status">
        <span className="status-pill">Provider {selectedProviderLabel}</span>
        <span className="status-pill">Model {runtime.model}</span>
        <span className="status-pill">Budget {runtime.budgets.max_wall_time_s}s</span>
        <span className="status-pill">Subcalls {runtime.budgets.max_subcalls}</span>
        <span className="status-pill">Corpus {selectedCorpus.path}</span>
        <span className="status-pill connection-pill">
          {connectionState === 'disconnected' ? <WifiOff size={14} /> : <Wifi size={14} />}
          {connectionState}
        </span>
        {traceSummary ? <span className="status-pill">Trace events {traceSummary.events_total}</span> : null}
        {traceStep ? <span className="status-pill">Latest {traceStep.type}</span> : null}
      </section>

      <section className="workspace-mode-strip panel" aria-label="Workspace focus mode">
        <div className="panel-title-row">
          <h3>Focus mode</h3>
          <div className="mode-actions">
            <span>{workspaceMode}</span>
            <button
              type="button"
              className="ghost-btn small shortcuts-trigger"
              onClick={() => setShowShortcutHelp(true)}
              aria-label="Open keyboard shortcuts"
            >
              <Keyboard size={14} />
              Shortcuts
            </button>
          </div>
        </div>
        <div className="ops-tabs">
          <button
            type="button"
            className={workspaceMode === 'command' ? 'tab active' : 'tab'}
            onClick={() => setWorkspaceMode('command')}
          >
            Command
          </button>
          <button
            type="button"
            className={workspaceMode === 'evidence' ? 'tab active' : 'tab'}
            onClick={() => setWorkspaceMode('evidence')}
          >
            Evidence
          </button>
          <button
            type="button"
            className={workspaceMode === 'trace' ? 'tab active' : 'tab'}
            onClick={() => setWorkspaceMode('trace')}
          >
            Trace
          </button>
          <button
            type="button"
            className={workspaceMode === 'ops' ? 'tab active' : 'tab'}
            onClick={() => setWorkspaceMode('ops')}
          >
            Ops
          </button>
        </div>
      </section>

      <section className="banner-stack" aria-live="polite">
        {!runtimeProviderKeyReady ? (
          <div className="banner warning" data-testid="missing-key-banner">
            <AlertTriangle size={16} />
            {selectedProviderEnvHint} is missing for {selectedProviderLabel}. Runs will use fallback behavior.
          </div>
        ) : null}

        {!diagnostics?.environment.docker_running ? (
          <div className="banner warning" data-testid="docker-fallback-banner">
            <AlertTriangle size={16} />
            Docker sandbox unavailable. Runtime will fallback to local environment.
          </div>
        ) : null}

        {groundingScore !== null && groundingScore < 0.7 ? (
          <div className="banner warning" data-testid="grounding-warning-banner">
            <AlertTriangle size={16} />
            Low grounding score ({groundingScore}). Review citations before trusting this answer.
          </div>
        ) : null}

        {runtimeWarnings.map((warning) => (
          <div key={warning} className="banner warning runtime-warning">
            <span className="banner-copy">
              <AlertTriangle size={16} />
              {warning}
            </span>
            {warning.includes('disconnected') ? (
              <button type="button" className="ghost-btn small" onClick={() => void reconnectTrace()}>
                Reconnect
              </button>
            ) : null}
          </div>
        ))}
      </section>

      <section className="workspace-grid" data-testid="workspace-grid" data-focus-mode={workspaceMode}>
        <aside className="left-rail" data-testid="left-rail">
          <section className="context-rail panel" aria-label="Session context">
            <div className="panel-title-row">
              <h3>Session</h3>
              <span>{workspaceMode}</span>
            </div>
            <p className="panel-note">Active corpus, run pointer, and deterministic state.</p>
            <div className="ops-readout">
              <span className="status-pill">Corpus {selectedCorpus.name}</span>
              <span className="status-pill">Run {selectedRunId ?? 'none'}</span>
              <span className="status-pill">Status {runStatus}</span>
              <span className="status-pill">Events {events.length}</span>
            </div>
            <div className="context-actions">
              <button type="button" className="ghost-btn small" onClick={() => setWorkspaceMode('command')}>
                Open command
              </button>
              <button type="button" className="ghost-btn small" onClick={() => setWorkspaceMode('evidence')}>
                Open evidence
              </button>
            </div>
          </section>

          <div className="panel-title-row">
            <h3>Corpora</h3>
            <span>{corpora.length}</span>
          </div>
          {corpora.length === 0 ? <p className="panel-note">No corpora yet. Create one from onboarding.</p> : null}
          <ul className="rail-list">
            {corpora.map((corpus) => (
              <li key={corpus.id}>
                <button
                  type="button"
                  className={selectedCorpusId === corpus.id ? 'rail-btn active' : 'rail-btn'}
                  onClick={() => setSelectedCorpusId(corpus.id)}
                >
                  <span>{corpus.name}</span>
                  <small>{corpus.path}</small>
                </button>
              </li>
            ))}
          </ul>

          <div className="panel-title-row">
            <h3>Runs</h3>
            <span>{runs.length}</span>
          </div>
          {runs.length === 0 ? <p className="panel-note">No runs yet. Execute a query to start trace capture.</p> : null}
          <VirtualizedList
            items={runs}
            itemHeight={80}
            height={360}
            className="runs-scroll"
            renderItem={(run) => (
              <button
                type="button"
                className={selectedRunId === run.id ? 'rail-btn run-btn active' : 'rail-btn run-btn'}
                onClick={() => setSelectedRunId(run.id)}
                aria-label={`Run ${run.id} ${run.status}`}
              >
                <div className="run-line">
                  <span className="capitalize">{run.status}</span>
                  <small>{run.created_at.slice(0, 10)}</small>
                </div>
                <small>{run.answer_preview || 'No answer yet'}</small>
              </button>
            )}
          />
        </aside>

        <section className="center-pane" data-testid="center-pane">
          <section
            id="command-panel"
            className={`composer-card question-bar ${workspaceMode === 'command' ? 'focus-active' : 'focus-dim'}`}
          >
            <div className="composer-head">
              <h2>Ask with evidence</h2>
              <p>Frame the question, set the budget, and run a deterministic trace.</p>
            </div>

            <ul className="guided-prompts" aria-label="Guided prompts">
              {guidedPrompts.map((prompt) => (
                <li key={prompt}>
                  <button type="button" className="prompt-card" onClick={() => setQuestion(prompt)}>
                    {prompt}
                  </button>
                </li>
              ))}
            </ul>

            <label className="question-input-wrap">
              Question
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                rows={4}
                placeholder="Ask about architecture, policy, risks, or behavior."
                aria-label="Question input"
              />
            </label>

            {shortcut ? (
              <div className="composer-hint-card" aria-label="Command shortcut hint">
                <strong>Shortcut {shortcut.command}</strong>
                <p>{shortcut.suggestion}</p>
              </div>
            ) : null}

            {queryWarnings.length > 0 ? (
              <ul className="lint-list" aria-label="Query lint warnings">
                {queryWarnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            ) : null}

            <div className="quality-row" aria-label="Quality presets">
              <span>Quality mode</span>
              <button
                type="button"
                className={qualityMode === 'speed' ? 'tiny-pill active' : 'tiny-pill'}
                onClick={() => setQualityPreset('speed')}
              >
                Speed
              </button>
              <button
                type="button"
                className={qualityMode === 'balanced' ? 'tiny-pill active' : 'tiny-pill'}
                onClick={() => setQualityPreset('balanced')}
              >
                Balanced
              </button>
              <button
                type="button"
                className={qualityMode === 'deep' ? 'tiny-pill active' : 'tiny-pill'}
                onClick={() => setQualityPreset('deep')}
              >
                Deep investigation
              </button>
            </div>

            <div className="budget-row" aria-label="Budget controls">
              <label>
                Wall time
                <input
                  type="number"
                  min={1}
                  value={runtime.budgets.max_wall_time_s}
                  onChange={(event) =>
                    setRuntime((prev) => ({
                      ...prev,
                      budgets: { ...prev.budgets, max_wall_time_s: Number(event.target.value) },
                    }))
                  }
                />
              </label>
              <label>
                Subcalls
                <input
                  type="number"
                  min={1}
                  value={runtime.budgets.max_subcalls}
                  onChange={(event) =>
                    setRuntime((prev) => ({
                      ...prev,
                      budgets: { ...prev.budgets, max_subcalls: Number(event.target.value) },
                    }))
                  }
                />
              </label>
              <label>
                Iterations
                <input
                  type="number"
                  min={1}
                  value={runtime.max_iterations}
                  onChange={(event) => setRuntime((prev) => ({ ...prev, max_iterations: Number(event.target.value) }))}
                />
              </label>
              <label>
                Top K
                <input
                  type="number"
                  min={1}
                  value={runtime.retrieval?.top_k ?? 6}
                  onChange={(event) =>
                    setRuntime((prev) => ({
                      ...prev,
                      retrieval: {
                        bm25_weight: prev.retrieval?.bm25_weight ?? 0.55,
                        vector_weight: prev.retrieval?.vector_weight ?? 0.35,
                        rerank_weight: prev.retrieval?.rerank_weight ?? 0.1,
                        top_k: Number(event.target.value),
                      },
                    }))
                  }
                />
              </label>
            </div>

            <div className="ops-readout" aria-label="Budget impact">
              <span className="status-pill">Speed {impact.speed}</span>
              <span className="status-pill">Cost {impact.cost}</span>
              <span className="status-pill">Coverage {impact.coverage}</span>
            </div>

            <div className="composer-advanced-toggle">
              <button
                type="button"
                className="ghost-btn small"
                onClick={() => setShowAdvancedComposer((prev) => !prev)}
              >
                {showAdvancedComposer ? 'Hide advanced controls' : 'Show advanced controls'}
              </button>
              <p className="hint-copy">
                Use advanced controls for retrieval tuning and multi-corpus targeting. Keyboard: Cmd/Ctrl+Enter to run,
                Shift+Cmd/Ctrl+Enter for fast profile run.
              </p>
            </div>

            {showAdvancedComposer ? (
              <>
                <div className="budget-row" aria-label="Retrieval blend">
                  <label>
                    BM25
                    <input
                      type="number"
                      min={0}
                      max={1}
                      step={0.05}
                      value={runtime.retrieval?.bm25_weight ?? 0.55}
                      onChange={(event) =>
                        setRuntime((prev) => ({
                          ...prev,
                          retrieval: {
                            bm25_weight: Number(event.target.value),
                            vector_weight: prev.retrieval?.vector_weight ?? 0.35,
                            rerank_weight: prev.retrieval?.rerank_weight ?? 0.1,
                            top_k: prev.retrieval?.top_k ?? 6,
                          },
                        }))
                      }
                    />
                  </label>
                  <label>
                    Vector
                    <input
                      type="number"
                      min={0}
                      max={1}
                      step={0.05}
                      value={runtime.retrieval?.vector_weight ?? 0.35}
                      onChange={(event) =>
                        setRuntime((prev) => ({
                          ...prev,
                          retrieval: {
                            bm25_weight: prev.retrieval?.bm25_weight ?? 0.55,
                            vector_weight: Number(event.target.value),
                            rerank_weight: prev.retrieval?.rerank_weight ?? 0.1,
                            top_k: prev.retrieval?.top_k ?? 6,
                          },
                        }))
                      }
                    />
                  </label>
                  <label>
                    Rerank
                    <input
                      type="number"
                      min={0}
                      max={1}
                      step={0.05}
                      value={runtime.retrieval?.rerank_weight ?? 0.1}
                      onChange={(event) =>
                        setRuntime((prev) => ({
                          ...prev,
                          retrieval: {
                            bm25_weight: prev.retrieval?.bm25_weight ?? 0.55,
                            vector_weight: prev.retrieval?.vector_weight ?? 0.35,
                            rerank_weight: Number(event.target.value),
                            top_k: prev.retrieval?.top_k ?? 6,
                          },
                        }))
                      }
                    />
                  </label>
                </div>

                <div className="target-corpora" aria-label="Target corpora">
                  <label className="checkbox-row">
                    <input
                      type="checkbox"
                      checked={Boolean(runtime.performance_mode)}
                      onChange={(event) => setRuntime((prev) => ({ ...prev, performance_mode: event.target.checked }))}
                    />
                    Performance mode
                  </label>
                  <div className="target-pills">
                    {corpora.map((corpus) => {
                      const selected = runtime.target_corpora?.includes(corpus.id) ?? false;
                      return (
                        <button
                          key={corpus.id}
                          type="button"
                          className={selected ? 'tiny-pill active' : 'tiny-pill'}
                          onClick={() =>
                            setRuntime((prev) => {
                              const current = prev.target_corpora ?? [];
                              const next = selected ? current.filter((id) => id !== corpus.id) : [...current, corpus.id];
                              return { ...prev, target_corpora: next };
                            })
                          }
                        >
                          {corpus.name}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </>
            ) : null}

            <div className="budget-row" aria-label="Provider controls">
              <label>
                Provider
                <select
                  value={runtime.provider}
                  onChange={(event) =>
                    setRuntime((prev) => ({
                      ...prev,
                      provider: event.target.value,
                      model: providerDefaultModel(event.target.value, diagnostics),
                    }))
                  }
                >
                  {providerOptions.map((provider) => (
                    <option key={provider.id} value={provider.id}>
                      {provider.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Model
                <input
                  value={runtime.model}
                  onChange={(event) => setRuntime((prev) => ({ ...prev, model: event.target.value }))}
                />
              </label>
            </div>

            <div className="session-key-card" aria-label="Session key vault">
              <label>
                Session API key
                <input
                  type="password"
                  autoComplete="off"
                  value={sessionProviderKey}
                  onChange={(event) =>
                    setSessionProviderKeys((prev) => ({
                      ...prev,
                      [runtime.provider]: event.target.value,
                    }))
                  }
                  placeholder={`Optional ${selectedProviderLabel} key for this browser session`}
                  aria-label="Session API key"
                />
              </label>
              <p className="hint-copy">
                Stored in memory only and sent only when you run a query. The key is never written to local files or run
                records.
              </p>
              <div className="session-key-actions">
                <span className="status-pill">
                  {sessionProviderKey.trim().length > 0
                    ? `Session key loaded for ${selectedProviderLabel}`
                    : `Using ${selectedProviderEnvHint} from backend env`}
                </span>
                <button
                  type="button"
                  className="ghost-btn small"
                  onClick={() =>
                    setSessionProviderKeys((prev) => ({
                      ...prev,
                      [runtime.provider]: '',
                    }))
                  }
                  disabled={sessionProviderKey.trim().length === 0}
                >
                  Clear session key
                </button>
              </div>
            </div>

            <div className="actions">
              <button type="button" className="primary-btn" onClick={() => void runQuery()} disabled={busy}>
                <ArrowUpRight size={16} />
                {busy ? 'Running…' : 'Run with trace'}
              </button>
              <button type="button" className="ghost-btn" onClick={() => void replayCurrentRun()} disabled={!selectedRunId}>
                <RefreshCcw size={16} />
                Replay
              </button>
              <button type="button" className="ghost-btn" onClick={() => void exportCurrentRun()} disabled={!selectedRunId}>
                <Download size={16} />
                Export
              </button>
              <button type="button" className="ghost-btn" onClick={() => void openSharePreview()} disabled={!selectedRunId}>
                Share preview
              </button>
            </div>
          </section>

          <section
            id="ops-panel"
            className={`panel operations-deck ${workspaceMode === 'ops' ? 'focus-active' : 'focus-dim'}`}
            data-testid="operations-deck"
          >
            <div className="panel-title-row">
              <h3>Ops Lab</h3>
              <span>{operationsTab}</span>
            </div>
            <p className="panel-note">Task workflows for compare, watcher automation, security triage, and evaluations.</p>
            <div className="ops-tabs" aria-label="Operations tabs">
              <button
                type="button"
                className={operationsTab === 'compare' ? 'tab active' : 'tab'}
                onClick={() => {
                  setOperationsTab('compare');
                  setWorkspaceMode('ops');
                }}
              >
                Compare
              </button>
              <button
                type="button"
                className={operationsTab === 'watch' ? 'tab active' : 'tab'}
                onClick={() => {
                  setOperationsTab('watch');
                  setWorkspaceMode('ops');
                }}
              >
                Watch
              </button>
              <button
                type="button"
                className={operationsTab === 'security' ? 'tab active' : 'tab'}
                onClick={() => {
                  setOperationsTab('security');
                  setWorkspaceMode('ops');
                }}
              >
                Security
              </button>
              <button
                type="button"
                className={operationsTab === 'evals' ? 'tab active' : 'tab'}
                onClick={() => {
                  setOperationsTab('evals');
                  setWorkspaceMode('ops');
                }}
              >
                Evals
              </button>
            </div>

            {operationsTab === 'compare' ? (
              <div className="ops-panel" data-testid="compare-panel">
                <div className="ops-grid">
                  <label>
                    Baseline run
                    <select value={compareLeftRunId ?? ''} onChange={(event) => setCompareLeftRunId(event.target.value)}>
                      <option value="" disabled>
                        Select run
                      </option>
                      {runs.map((run) => (
                        <option key={`left-${run.id}`} value={run.id}>
                          {run.id}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Candidate run
                    <select value={compareRightRunId ?? ''} onChange={(event) => setCompareRightRunId(event.target.value)}>
                      <option value="" disabled>
                        Select run
                      </option>
                      {runs.map((run) => (
                        <option key={`right-${run.id}`} value={run.id}>
                          {run.id}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                <div className="actions">
                  <button type="button" className="primary-btn" onClick={() => void compareSelectedRuns()}>
                    Compare runs
                  </button>
                  <button type="button" className="ghost-btn" onClick={() => void reloadComparison()} disabled={!comparisonId}>
                    Refresh compare
                  </button>
                  <button
                    type="button"
                    className="ghost-btn"
                    onClick={saveComparisonSession}
                    disabled={!compareLeftRunId || !compareRightRunId}
                  >
                    Save session
                  </button>
                </div>
                {comparison ? (
                  <div className="ops-readout">
                    <span className="status-pill">Overlap {Math.round(comparison.overlap_ratio * 100)}%</span>
                    <span className="status-pill">Left citations {comparison.left_citations}</span>
                    <span className="status-pill">Right citations {comparison.right_citations}</span>
                  </div>
                ) : null}
                {savedComparisons.length > 0 ? (
                  <ul className="ops-list">
                    {savedComparisons.slice(0, 3).map((item) => (
                      <li key={item.id}>
                        <button
                          type="button"
                          className="ghost-btn small"
                          onClick={() => {
                            setCompareLeftRunId(item.left);
                            setCompareRightRunId(item.right);
                          }}
                        >
                          {item.note}
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ) : null}

            {operationsTab === 'watch' ? (
              <div className="ops-panel" data-testid="watch-panel">
                <div className="ops-grid">
                  <label>
                    Poll interval (seconds)
                    <input
                      type="number"
                      min={3}
                      value={watchPollInterval}
                      onChange={(event) => setWatchPollInterval(Number(event.target.value))}
                    />
                  </label>
                  <div className="ops-readout">
                    <span className="status-pill">Status {watchStatus?.status ?? 'stopped'}</span>
                    <span className="status-pill">Watchers {watchers.length}</span>
                  </div>
                </div>
                <div className="actions">
                  <button type="button" className="primary-btn" onClick={() => void startWatch()}>
                    Start watcher
                  </button>
                  <button type="button" className="ghost-btn" onClick={() => void stopWatch()}>
                    Stop watcher
                  </button>
                </div>
              </div>
            ) : null}

            {operationsTab === 'security' ? (
              <div className="ops-panel" data-testid="security-panel">
                <div className="ops-readout">
                  <span className="status-pill">Findings {policySummary?.total_findings ?? 0}</span>
                  {policySummary?.totals.slice(0, 2).map((item) => (
                    <span key={`${item.category}-${item.severity}`} className="status-pill">
                      {item.category} {item.count}
                    </span>
                  ))}
                </div>
                <div className="actions">
                  <button type="button" className="primary-btn" onClick={() => void refreshPolicy()}>
                    Refresh scan
                  </button>
                </div>
                <ul className="ops-list">
                  {policyFindings.slice(0, 4).map((finding) => (
                    <li key={finding.id}>
                      <div className="finding-row">
                        <strong>{finding.category}</strong> {finding.path}:L{finding.line_no}
                      </div>
                      <div className="finding-row">
                        <span className="status-pill">State {findingState[finding.id] ?? 'new'}</span>
                        <button
                          type="button"
                          className="ghost-btn small"
                          onClick={() => setFindingState((prev) => ({ ...prev, [finding.id]: 'accepted' }))}
                        >
                          Accept
                        </button>
                        <button
                          type="button"
                          className="ghost-btn small"
                          onClick={() => setFindingState((prev) => ({ ...prev, [finding.id]: 'resolved' }))}
                        >
                          Resolve
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {operationsTab === 'evals' ? (
              <div className="ops-panel" data-testid="eval-panel">
                <div className="preset-row" aria-label="Evaluation presets">
                  <button
                    type="button"
                    className={evalPreset === 'smoke' ? 'tiny-pill active' : 'tiny-pill'}
                    onClick={() => {
                      setEvalPreset('smoke');
                      setEvalQueries('where retry policy\\nsummarize architecture');
                    }}
                  >
                    Smoke
                  </button>
                  <button
                    type="button"
                    className={evalPreset === 'regression' ? 'tiny-pill active' : 'tiny-pill'}
                    onClick={() => {
                      setEvalPreset('regression');
                      setEvalQueries('where retry policy\\nfind schema ownership\\nlist unresolved risks');
                    }}
                  >
                    Regression
                  </button>
                  <button
                    type="button"
                    className={evalPreset === 'deep' ? 'tiny-pill active' : 'tiny-pill'}
                    onClick={() => {
                      setEvalPreset('deep');
                      setEvalQueries('map architecture with citations\\nexplain retrieval tuning tradeoffs');
                    }}
                  >
                    Deep
                  </button>
                </div>
                <label>
                  Evaluation queries (one per line)
                  <textarea
                    value={evalQueries}
                    rows={3}
                    onChange={(event) => setEvalQueries(event.target.value)}
                    aria-label="Eval queries"
                  />
                </label>
                <div className="actions">
                  <button type="button" className="primary-btn" onClick={() => void runEvaluation()}>
                    Run evaluation
                  </button>
                </div>
                <div className="ops-readout">
                  <span className="status-pill">Eval runs {evals.length}</span>
                  <span className="status-pill">Latest {activeEval?.status ?? evals[0]?.status ?? 'none'}</span>
                  <span className="status-pill">
                    Trend {Math.round(
                      ((evals
                        .slice(0, 3)
                        .filter((item) => item.status === 'succeeded').length /
                        Math.max(1, Math.min(3, evals.length))) *
                        100)
                    )}
                    %
                  </span>
                </div>
              </div>
            ) : null}
          </section>

          {runStatus === 'partial_budget_exceeded' ? (
            <p className="warn-copy">Budget exceeded. Increase limits or narrow the query for a complete answer.</p>
          ) : null}
          {error ? <p className="error-copy">{error}</p> : null}

          <article
            id="answer-panel"
            className={`answer-panel ${workspaceMode === 'evidence' ? 'focus-active' : 'focus-dim'}`}
            aria-live="polite"
            data-testid="answer-panel"
          >
            <div className="answer-head">
              <h2>Answer</h2>
              <span className={`score-pill ${groundingTone(groundingScore)}`}>
                <Sparkles size={14} />
                {groundingLabel(groundingScore)}
              </span>
            </div>

            <section className="answer-cards" aria-label="Answer quality cards">
              <article className="answer-card">
                <h3>Summary</h3>
                <p>{parsedAnswer.summary || 'Run a query to generate a structured answer with linked evidence.'}</p>
              </article>
              <article className="answer-card">
                <h3>Confidence</h3>
                <p>{groundingScore !== null ? `${Math.round(groundingScore * 100)}% grounded` : 'Pending'}</p>
                <div className="ops-readout">
                  <span className="status-pill">Citations {citations.length}</span>
                  <span className="status-pill">
                    Completeness {completeness !== null ? `${Math.round(completeness * 100)}%` : 'Pending'}
                  </span>
                </div>
              </article>
              <article className="answer-card">
                <h3>Why this answer</h3>
                <p>
                  {traceSummary
                    ? `Built from ${traceSummary.events_total} trace events across ${traceSummary.iterations.length || 1} iteration(s).`
                    : 'Trace summary unavailable for this run.'}
                </p>
              </article>
            </section>

            {parsedAnswer.details.length > 0 ? (
              <section className="details-list" aria-label="Evidence-backed details">
                <h3>Evidence-backed details</h3>
                <ul>
                  {parsedAnswer.details.map((line) => (
                    <li key={line}>
                      <span>{line}</span>
                      <span className={`inline-badge ${groundingUngroundedClaims.some((claim) => line.includes(claim)) ? 'warn' : 'ok'}`}>
                        {groundingUngroundedClaims.some((claim) => line.includes(claim)) ? 'weak' : 'grounded'}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : (
              <pre>{answer || 'Run a query to generate a structured answer with linked evidence.'}</pre>
            )}

            {groundingUngroundedClaims.length > 0 ? (
              <section className="weak-claims" aria-label="Unsupported claims">
                <h3>Needs review</h3>
                <ul>
                  {groundingUngroundedClaims.map((claim) => (
                    <li key={claim}>{claim}</li>
                  ))}
                </ul>
              </section>
            ) : null}

            <section className="delta-card" aria-label="Run delta summary">
              <h3>What changed since previous run</h3>
              <p>
                {previousRun
                  ? `Previous run ${previousRun.id} was ${previousRun.status} with preview: ${previousRun.answer_preview || 'n/a'}.`
                  : 'No previous run available for delta comparison.'}
              </p>
            </section>

            <div className="evidence-head">
              <h3>Evidence</h3>
              <p>{selectedRun ? `Run ${selectedRun.id}` : 'Select a run to inspect citations and snippets.'}</p>
            </div>
            <CitationChips citations={citations} onOpen={(citation, index) => void openCitation(citation, index)} />

            <div className="followup-row" aria-label="Follow-up prompts">
              {nextPrompts.map((prompt) => (
                <button key={prompt} type="button" className="ghost-btn small" onClick={() => setQuestion(prompt)}>
                  {prompt}
                </button>
              ))}
            </div>

            <div className="actions">
              <button
                type="button"
                className="ghost-btn small"
                onClick={() => {
                  void navigator.clipboard.writeText(parsedAnswer.summary || answer);
                }}
              >
                Copy summary
              </button>
              <button
                type="button"
                className="ghost-btn small"
                onClick={() => {
                  void navigator.clipboard.writeText(citations.map((c) => `${c.path}:L${c.start_line}-${c.end_line}`).join('\n'));
                }}
              >
                Copy citations
              </button>
            </div>
            {lastExportPath ? <p className="export-copy">Exported to: {lastExportPath}</p> : null}
            {sharePreview ? <p className="export-copy">Share payload loaded ({Object.keys(sharePreview).length} keys).</p> : null}
          </article>
        </section>

        <div id="trace-panel" className={workspaceMode === 'trace' ? 'focus-active' : 'focus-dim'}>
          <TracePanel events={events} />
        </div>
      </section>

      <EvidenceViewer
        open={evidenceOpen}
        citation={activeCitation}
        text={evidenceText}
        onClose={() => setEvidenceOpen(false)}
        onPrev={() => moveCitation(-1)}
        onNext={() => moveCitation(1)}
        onExpand={(delta) => expandCitation(delta)}
        citationIndex={activeCitationIndex >= 0 ? activeCitationIndex : 0}
        citationCount={citations.length}
      />

      {showShortcutHelp ? (
        <div className="modal-backdrop" onClick={() => setShowShortcutHelp(false)}>
          <section
            className="modal-shell shortcuts-modal"
            role="dialog"
            aria-modal="true"
            aria-label="Keyboard and command shortcuts"
            data-testid="shortcuts-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <p className="kicker">Power user guide</p>
                <h3>Keyboard and command shortcuts</h3>
              </div>
              <button type="button" className="ghost-btn small" onClick={() => setShowShortcutHelp(false)}>
                Close
              </button>
            </div>
            <div className="shortcuts-grid" aria-label="Shortcut reference">
              <article className="shortcuts-card">
                <h4>Keyboard</h4>
                <ul>
                  <li>
                    <code>Cmd/Ctrl + Enter</code> Run current question
                  </li>
                  <li>
                    <code>Shift + Cmd/Ctrl + Enter</code> Fast profile run
                  </li>
                  <li>
                    <code>?</code> Toggle this guide
                  </li>
                  <li>
                    <code>Esc</code> Close open modal
                  </li>
                </ul>
              </article>
              <article className="shortcuts-card">
                <h4>Slash commands</h4>
                <ul>
                  <li>
                    <code>/compare</code> Jump to compare runs
                  </li>
                  <li>
                    <code>/watch</code> Jump to corpus watcher controls
                  </li>
                  <li>
                    <code>/evaluate</code> Jump to eval workflows
                  </li>
                </ul>
              </article>
              <article className="shortcuts-card">
                <h4>Workflow tips</h4>
                <ul>
                  <li>Use starter corpora for deterministic demos.</li>
                  <li>Run compare after retrieval tuning changes.</li>
                  <li>Export + share preview before stakeholder reviews.</li>
                </ul>
              </article>
            </div>
          </section>
        </div>
      ) : null}

      {debugMode ? (
        <pre className="debug-panel" data-testid="debug-panel">
          {JSON.stringify(window.__RLM_LENS_DEBUG?.() ?? {}, null, 2)}
        </pre>
      ) : null}
    </main>
  );
}

export default App;
