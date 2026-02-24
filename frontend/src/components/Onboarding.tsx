import { useEffect, useMemo, useState } from 'react';

import { createCorpus, getDiagnostics, getIndexJob, listStarterCorpora, materializeStarterCorpus } from '../lib/api';
import type { Diagnostics, RuntimeConfig, StarterCorpusPack } from '../lib/types';

type Step = 1 | 2 | 3 | 4;
type EntryMode = 'demo' | 'local' | 'resume';
type GoalPreset = 'speed' | 'balanced' | 'deep';

type PersistedOnboardingState = {
  step: Step;
  name: string;
  path: string;
  runtime: RuntimeConfig;
  goalPreset: GoalPreset;
};

const ONBOARDING_STORAGE_KEY = 'rlm_lens_onboarding_v3';

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
  max_iterations: 6,
  budgets: {
    max_wall_time_s: 90,
    max_subcalls: 40,
    max_tokens: null,
  },
  performance_mode: false,
  retrieval: DEFAULT_RETRIEVAL,
};

const DEFAULT_INDEX_CONFIG = {
  include_globs: ['**/*.md', '**/*.py', '**/*.sql', '**/*.ts', '**/*.tsx'],
  exclude_globs: ['**/.git/**', '**/node_modules/**'],
  max_file_bytes: 1_000_000,
};

const stepLabels = ['Corpus', 'Model', 'Budgets', 'Index'];

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
    // ignore storage write errors
  }
}

function removeStorage(key: string): void {
  try {
    if (typeof window === 'undefined' || typeof window.localStorage?.removeItem !== 'function') {
      return;
    }
    window.localStorage.removeItem(key);
  } catch {
    // ignore storage remove errors
  }
}

function applyPreset(runtime: RuntimeConfig, preset: GoalPreset): RuntimeConfig {
  if (preset === 'speed') {
    return {
      ...runtime,
      max_depth: 1,
      max_iterations: 4,
      performance_mode: true,
      budgets: {
        ...runtime.budgets,
        max_wall_time_s: 45,
        max_subcalls: 20,
      },
      retrieval: {
        bm25_weight: 0.6,
        vector_weight: 0.3,
        rerank_weight: 0.1,
        top_k: 4,
      },
    };
  }

  if (preset === 'deep') {
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
    max_iterations: 6,
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

export function Onboarding({
  onReady,
}: {
  onReady: (payload: { corpusId: string; runtime: RuntimeConfig }) => void;
}) {
  const [step, setStep] = useState<Step>(1);
  const [entryMode, setEntryMode] = useState<EntryMode>('demo');
  const [goalPreset, setGoalPreset] = useState<GoalPreset>('balanced');
  const [name, setName] = useState('Demo Corpus');
  const [path, setPath] = useState('../examples/sample_corpus');
  const [runtime, setRuntime] = useState<RuntimeConfig>(defaultRuntime);
  const [indexProgress, setIndexProgress] = useState('Waiting to start indexing...');
  const [indexDone, setIndexDone] = useState(0);
  const [indexTotal, setIndexTotal] = useState(0);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [diagnostics, setDiagnostics] = useState<Diagnostics | null>(null);
  const [starterPacks, setStarterPacks] = useState<StarterCorpusPack[]>([]);
  const [starterError, setStarterError] = useState<string | null>(null);
  const [materializingPackId, setMaterializingPackId] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const [diag, packs] = await Promise.all([getDiagnostics(), listStarterCorpora()]);
        setDiagnostics(diag);
        setStarterPacks(packs);
      } catch {
        setDiagnostics(null);
        setStarterError('Starter corpus catalog unavailable. You can still use a local path.');
      }
    })();
  }, []);

  useEffect(() => {
    try {
      const raw = readStorage(ONBOARDING_STORAGE_KEY);
      if (!raw) {
        return;
      }
      const parsed = JSON.parse(raw) as PersistedOnboardingState;
      if (!parsed || typeof parsed !== 'object') {
        return;
      }
      if (parsed.name && parsed.path && parsed.runtime) {
        setName(parsed.name);
        setPath(parsed.path);
        setRuntime({
          ...defaultRuntime,
          ...parsed.runtime,
          budgets: {
            ...defaultRuntime.budgets,
            ...(parsed.runtime.budgets ?? {}),
          },
          retrieval: {
            bm25_weight: parsed.runtime.retrieval?.bm25_weight ?? DEFAULT_RETRIEVAL.bm25_weight,
            vector_weight: parsed.runtime.retrieval?.vector_weight ?? DEFAULT_RETRIEVAL.vector_weight,
            rerank_weight: parsed.runtime.retrieval?.rerank_weight ?? DEFAULT_RETRIEVAL.rerank_weight,
            top_k: parsed.runtime.retrieval?.top_k ?? DEFAULT_RETRIEVAL.top_k,
          },
        });
        setStep(parsed.step ?? 1);
        setGoalPreset(parsed.goalPreset ?? 'balanced');
        setEntryMode('resume');
      }
    } catch {
      // Ignore local storage parse errors.
    }
  }, []);

  useEffect(() => {
    const payload: PersistedOnboardingState = {
      step,
      name,
      path,
      runtime,
      goalPreset,
    };
    writeStorage(ONBOARDING_STORAGE_KEY, JSON.stringify(payload));
  }, [goalPreset, name, path, runtime, step]);

  const canContinue = useMemo(() => {
    if (step === 1) return name.trim().length > 0 && path.trim().length > 0;
    return true;
  }, [name, path, step]);

  const indexRatio = indexTotal > 0 ? Math.min(1, indexDone / indexTotal) : 0;

  const corpusEstimate = useMemo(() => {
    const sample = path.includes('sample_corpus') || path.includes('fixtures');
    const files = sample ? 18 : 140;
    const sizeMb = sample ? 2.1 : 34;
    const minutes = Math.max(1, Math.round((files / 40) * (runtime.max_iterations / 6)));
    return {
      files,
      sizeMb,
      minutes,
    };
  }, [path, runtime.max_iterations]);

  const applyEntryMode = (nextMode: EntryMode) => {
    setEntryMode(nextMode);
    if (nextMode === 'demo') {
      setName('Fixture Corpus');
      setPath('../examples/sample_corpus');
      setGoalPreset('balanced');
      setRuntime((prev) => applyPreset(prev, 'balanced'));
      setStep(1);
      return;
    }

    if (nextMode === 'local') {
      setName((prev) => (prev === 'Fixture Corpus' ? 'My Corpus' : prev));
      setPath((prev) => (prev === '../examples/sample_corpus' ? '~/Documents' : prev));
      setStep(1);
      return;
    }

    try {
      const raw = readStorage(ONBOARDING_STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as PersistedOnboardingState;
      setStep(parsed.step ?? 1);
      setName(parsed.name ?? 'Demo Corpus');
      setPath(parsed.path ?? '../examples/sample_corpus');
      setRuntime({
        ...defaultRuntime,
        ...parsed.runtime,
        budgets: {
          ...defaultRuntime.budgets,
          ...(parsed.runtime?.budgets ?? {}),
        },
        retrieval: {
          bm25_weight: parsed.runtime?.retrieval?.bm25_weight ?? DEFAULT_RETRIEVAL.bm25_weight,
          vector_weight: parsed.runtime?.retrieval?.vector_weight ?? DEFAULT_RETRIEVAL.vector_weight,
          rerank_weight: parsed.runtime?.retrieval?.rerank_weight ?? DEFAULT_RETRIEVAL.rerank_weight,
          top_k: parsed.runtime?.retrieval?.top_k ?? DEFAULT_RETRIEVAL.top_k,
        },
      });
      setGoalPreset(parsed.goalPreset ?? 'balanced');
    } catch {
      // Ignore invalid cache.
    }
  };

  async function createAndWaitForIndex(corpusName: string, corpusPath: string, runtimeConfig: RuntimeConfig) {
    const created = await createCorpus({
      name: corpusName,
      path: corpusPath,
      index_config: DEFAULT_INDEX_CONFIG,
      start_index: true,
    });

    if (!created.index_job_id) {
      throw new Error('Index job was not created.');
    }

    for (let i = 0; i < 240; i += 1) {
      const job = await getIndexJob(created.index_job_id);
      const total = job.progress.files_total ?? 0;
      const done = job.progress.files_done ?? 0;
      setIndexDone(done);
      setIndexTotal(total);
      setIndexProgress(`Indexing ${done}/${total}: ${job.progress.current_path ?? 'finishing...'}`);

      if (job.status === 'succeeded') {
        setIndexProgress('Index complete. Ready to ask your first question.');
        setIndexDone(total || done);
        setIndexTotal(total || done || 1);
        onReady({ corpusId: created.corpus_id, runtime: runtimeConfig });
        removeStorage(ONBOARDING_STORAGE_KEY);
        return;
      }
      if (job.status === 'failed') {
        throw new Error('Indexing failed. Check backend logs.');
      }
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
    throw new Error('Indexing timed out.');
  }

  async function startIndex() {
    setIsBusy(true);
    setError(null);
    try {
      await createAndWaitForIndex(name, path, runtime);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unexpected onboarding error.');
    } finally {
      setIsBusy(false);
    }
  }

  async function runInstantDemo() {
    setIsBusy(true);
    setError(null);
    const preferredPack = starterPacks.find((pack) => pack.id === 'fixture-small') ?? starterPacks[0] ?? null;
    if (!preferredPack) {
      setIsBusy(false);
      setError('Starter corpus catalog unavailable. Use local mode or retry in a few seconds.');
      return;
    }

    setMaterializingPackId(preferredPack.id);
    try {
      const materialized = await materializeStarterCorpus(preferredPack.id);
      const demoRuntime = applyPreset(runtime, 'balanced');
      setName(materialized.name);
      setPath(materialized.path);
      setEntryMode('demo');
      setGoalPreset('balanced');
      setRuntime(demoRuntime);
      setStep(4);
      await createAndWaitForIndex(materialized.name, materialized.path, demoRuntime);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Failed to run instant demo.');
    } finally {
      setMaterializingPackId(null);
      setIsBusy(false);
    }
  }

  async function materializePack(packId: string) {
    setStarterError(null);
    setMaterializingPackId(packId);
    try {
      const result = await materializeStarterCorpus(packId);
      setName(result.name);
      setPath(result.path);
      setEntryMode('demo');
      const packs = await listStarterCorpora();
      setStarterPacks(packs);
    } catch (caught) {
      setStarterError(caught instanceof Error ? caught.message : 'Failed to materialize starter corpus.');
    } finally {
      setMaterializingPackId(null);
    }
  }

  return (
    <section className="onboarding-shell" aria-label="Workspace onboarding">
      <div className="onboarding-hero">
        <p className="eyebrow">RLM-Lens setup</p>
        <h1>Infinite context, auditable answers.</h1>
        <p>
          Configure a corpus, runtime, and budget profile. In under five minutes you will have a fully traced,
          evidence-backed answer pipeline.
        </p>
      </div>

      <section className="onboarding-entry" aria-label="Onboarding entry mode">
        <button
          type="button"
          className={entryMode === 'demo' ? 'entry-card active' : 'entry-card'}
          onClick={() => applyEntryMode('demo')}
        >
          <strong>Try demo corpus</strong>
          <span>Deterministic first run and known citations.</span>
        </button>
        <button
          type="button"
          className={entryMode === 'local' ? 'entry-card active' : 'entry-card'}
          onClick={() => applyEntryMode('local')}
        >
          <strong>Index local corpus</strong>
          <span>Use your own project for realistic retrieval behavior.</span>
        </button>
        <button
          type="button"
          className={entryMode === 'resume' ? 'entry-card active' : 'entry-card'}
          onClick={() => applyEntryMode('resume')}
        >
          <strong>Resume setup</strong>
          <span>Restore the previous onboarding state from this browser.</span>
        </button>
      </section>

      <ul className="step-track" aria-label="Onboarding steps">
        {stepLabels.map((label, index) => {
          const idx = index + 1;
          const state = step === idx ? 'active' : step > idx ? 'complete' : 'upcoming';
          return (
            <li key={label} className={`step-pill ${state}`}>
              <span>{idx}</span>
              {label}
            </li>
          );
        })}
      </ul>

      <div className="onboarding-grid">
        <div className="panel onboarding-panel">
          {step === 1 ? (
            <>
              <h2>Select corpus</h2>
              <p className="panel-copy">Choose a name and a root folder to index. Paths stay local-first.</p>
              <label>
                Corpus name
                <input value={name} onChange={(event) => setName(event.target.value)} />
              </label>
              <label>
                Corpus path
                <input value={path} onChange={(event) => setPath(event.target.value)} />
              </label>
              <div className="onboarding-estimate" aria-label="Corpus health estimate">
                <span className="status-pill">Estimated files {corpusEstimate.files}</span>
                <span className="status-pill">Estimated size {corpusEstimate.sizeMb} MB</span>
                <span className="status-pill">Index time {corpusEstimate.minutes} min</span>
              </div>
              <section className="starter-pack-grid" aria-label="Starter corpus packs">
                {starterPacks.map((pack) => (
                  <article key={pack.id} className="starter-pack-card">
                    <div className="panel-title-row">
                      <h3>{pack.name}</h3>
                      <span>{pack.size_label}</span>
                    </div>
                    <p className="panel-copy">{pack.description}</p>
                    <div className="ops-readout">
                      <span className="status-pill">Files ~{pack.approx_files}</span>
                      <span className="status-pill">{pack.network_required ? 'Needs internet' : 'Offline ready'}</span>
                    </div>
                    <small className="panel-copy">License: {pack.license}</small>
                    <button
                      type="button"
                      className="ghost-btn small"
                      onClick={() => void materializePack(pack.id)}
                      disabled={materializingPackId !== null}
                    >
                      {materializingPackId === pack.id
                        ? 'Preparing...'
                        : pack.installed
                          ? 'Use installed pack'
                          : 'Download / generate pack'}
                    </button>
                  </article>
                ))}
              </section>
              <section className="instant-demo-card" aria-label="Instant demo launcher">
                <div>
                  <h3>Instant demo</h3>
                  <p className="panel-copy">
                    One click setup for new users: materialize a starter corpus, build the index, and open the workspace.
                  </p>
                </div>
                <button
                  type="button"
                  className="primary-btn"
                  onClick={() => void runInstantDemo()}
                  disabled={isBusy || materializingPackId !== null}
                >
                  {isBusy ? 'Preparing demo…' : 'Instant demo (materialize + index)'}
                </button>
              </section>
              {starterError ? <p className="error-copy">{starterError}</p> : null}
              <button type="button" className="ghost-btn" onClick={() => setPath('../examples/sample_corpus')}>
                Use sample corpus
              </button>
            </>
          ) : null}

          {step === 2 ? (
            <>
              <h2>Provider and model</h2>
              <p className="panel-copy">Start with the default profile for repeatable demo behavior.</p>
              <label>
                Provider
                <select
                  value={runtime.provider}
                  onChange={(event) => setRuntime((prev) => ({ ...prev, provider: event.target.value }))}
                >
                  <option value="openai">OpenAI</option>
                </select>
              </label>
              <label>
                Model
                <input
                  value={runtime.model}
                  onChange={(event) => setRuntime((prev) => ({ ...prev, model: event.target.value }))}
                />
              </label>
              <label>
                Environment
                <select
                  value={runtime.environment}
                  onChange={(event) =>
                    setRuntime((prev) => ({ ...prev, environment: event.target.value as 'docker' | 'local' }))
                  }
                >
                  <option value="docker">Docker</option>
                  <option value="local">Local fallback</option>
                </select>
              </label>
            </>
          ) : null}

          {step === 3 ? (
            <>
              <h2>Budgets</h2>
              <p className="panel-copy">Tune runtime limits based on speed vs depth trade-offs.</p>
              <div className="preset-row" aria-label="Goal preset">
                <button
                  type="button"
                  className={goalPreset === 'speed' ? 'tiny-pill active' : 'tiny-pill'}
                  onClick={() => {
                    setGoalPreset('speed');
                    setRuntime((prev) => applyPreset(prev, 'speed'));
                  }}
                >
                  Speed
                </button>
                <button
                  type="button"
                  className={goalPreset === 'balanced' ? 'tiny-pill active' : 'tiny-pill'}
                  onClick={() => {
                    setGoalPreset('balanced');
                    setRuntime((prev) => applyPreset(prev, 'balanced'));
                  }}
                >
                  Balanced
                </button>
                <button
                  type="button"
                  className={goalPreset === 'deep' ? 'tiny-pill active' : 'tiny-pill'}
                  onClick={() => {
                    setGoalPreset('deep');
                    setRuntime((prev) => applyPreset(prev, 'deep'));
                  }}
                >
                  Deep investigation
                </button>
              </div>
              <label>
                Max wall time (s)
                <input
                  type="number"
                  value={runtime.budgets.max_wall_time_s}
                  min={1}
                  onChange={(event) =>
                    setRuntime((prev) => ({
                      ...prev,
                      budgets: { ...prev.budgets, max_wall_time_s: Number(event.target.value) },
                    }))
                  }
                />
              </label>
              <label>
                Max depth
                <input
                  type="number"
                  value={runtime.max_depth}
                  min={1}
                  onChange={(event) => setRuntime((prev) => ({ ...prev, max_depth: Number(event.target.value) }))}
                />
              </label>
              <label>
                Max iterations
                <input
                  type="number"
                  value={runtime.max_iterations}
                  min={1}
                  onChange={(event) => setRuntime((prev) => ({ ...prev, max_iterations: Number(event.target.value) }))}
                />
              </label>
              <label>
                Max subcalls
                <input
                  type="number"
                  value={runtime.budgets.max_subcalls}
                  min={1}
                  onChange={(event) =>
                    setRuntime((prev) => ({
                      ...prev,
                      budgets: { ...prev.budgets, max_subcalls: Number(event.target.value) },
                    }))
                  }
                />
              </label>
            </>
          ) : null}

          {step === 4 ? (
            <>
              <h2>Build index</h2>
              <p className="panel-copy">We’ll create a searchable local corpus and unlock query mode.</p>
              <p className="index-progress">{indexProgress}</p>
              <div
                className="index-meter"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={Math.round(indexRatio * 100)}
              >
                <span style={{ width: `${Math.round(indexRatio * 100)}%` }} />
              </div>
              <button type="button" className="primary-btn" onClick={() => void startIndex()} disabled={isBusy}>
                {isBusy ? 'Indexing…' : 'Start indexing'}
              </button>
              <div className="onboarding-success">
                <strong>After indexing:</strong>
                <p>Run the guided prompt cards and inspect evidence + trace before exporting your first bundle.</p>
              </div>
              {error ? <p className="error-copy">{error}</p> : null}
            </>
          ) : null}

          <div className="step-actions">
            <button
              type="button"
              className="ghost-btn"
              disabled={step === 1 || isBusy}
              onClick={() => setStep((prev) => (Math.max(1, prev - 1) as Step))}
            >
              Back
            </button>
            <button
              type="button"
              className="primary-btn"
              disabled={!canContinue || step === 4 || isBusy}
              onClick={() => setStep((prev) => (Math.min(4, prev + 1) as Step))}
            >
              Continue
            </button>
          </div>
        </div>

        <aside className="panel onboarding-side" aria-label="Setup checklist">
          <h3>Preflight checklist</h3>
          <ul>
            <li>
              API key: {diagnostics?.provider.openai_api_key_present ? 'ready' : 'missing'}
              <small> Set `OPENAI_API_KEY` in `.env` and restart services if missing.</small>
            </li>
            <li>
              Docker runtime: {diagnostics?.environment.docker_running ? 'ready' : 'not running'}
              <small> Start Docker Desktop for isolated REPL execution.</small>
            </li>
            <li>
              Corpus path: {path.trim().length > 0 ? 'ready' : 'missing'}
              <small> Use an absolute path for non-demo corpora.</small>
            </li>
            <li>
              Budget profile: {goalPreset}
              <small> Switch to Deep investigation for difficult repositories.</small>
            </li>
          </ul>
          <div className="onboarding-hint">
            <strong>Tip</strong>
            <p>Choose the sample corpus for deterministic first-run screenshots and reliable visual testing.</p>
          </div>
        </aside>
      </div>
    </section>
  );
}
