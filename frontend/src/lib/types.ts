export type IndexConfig = {
  include_globs: string[];
  exclude_globs: string[];
  max_file_bytes: number;
};

export type Corpus = {
  id: string;
  name: string;
  path: string;
  last_indexed_at?: string | null;
  index_summary?: {
    files_total?: number;
    files_indexed?: number;
    files_skipped?: Record<string, number>;
  };
};

export type Citation = {
  citation_id: string;
  corpus_id?: string | null;
  path: string;
  start_line: number;
  end_line: number;
  snippet: string;
};

export type Run = {
  id: string;
  corpus_id: string;
  status: string;
  created_at: string;
  answer_preview: string;
  usage?: Record<string, unknown>;
};

export type RunDetail = {
  run_id: string;
  corpus_id: string;
  status: string;
  messages: { role: 'system' | 'user' | 'assistant'; content: string }[];
  final_answer: string | null;
  citations: Citation[];
  usage: {
    warnings?: string[];
    grounding?: {
      claims_total?: number;
      claims_grounded?: number;
      claims_ungrounded?: string[];
      grounding_score?: number;
    };
    [key: string]: unknown;
  };
};

export type RuntimeConfig = {
  provider: string;
  model: string;
  environment: 'docker' | 'local';
  max_depth: number;
  max_iterations: number;
  performance_mode?: boolean;
  target_corpora?: string[];
  corpus_weights?: Record<string, number>;
  retrieval?: {
    bm25_weight: number;
    vector_weight: number;
    rerank_weight: number;
    top_k: number;
  };
  budgets: {
    max_wall_time_s: number;
    max_subcalls: number;
    max_tokens?: number | null;
  };
};

export type TraceEvent = {
  type: string;
  timestamp: string;
  [key: string]: unknown;
};

export type Diagnostics = {
  provider: {
    openai_api_key_present: boolean;
  };
  environment: {
    docker_installed: boolean;
    docker_running: boolean;
  };
};

export type StarterCorpusPack = {
  id: string;
  name: string;
  description: string;
  size_label: string;
  approx_files: number;
  source_type: string;
  license: string;
  default_prompts: string[];
  network_required: boolean;
  installed: boolean;
  path?: string | null;
};

export type StarterCorpusMaterialized = {
  pack_id: string;
  name: string;
  path: string;
  installed: boolean;
  already_present: boolean;
  files_total: number;
  bytes_total: number;
};

export type WatchStatus = {
  corpus_id: string;
  status: string;
  poll_interval_s: number;
  last_checked_at?: string | null;
  last_change_at?: string | null;
  fingerprint?: string | null;
  error?: { message?: string } | null;
};

export type PolicyFinding = {
  id: string;
  path: string;
  line_no: number;
  category: string;
  severity: string;
  preview: string;
  found_at: string;
};

export type PolicySummary = {
  corpus_id: string;
  totals: Array<{ category: string; severity: string; count: number }>;
  total_findings: number;
};

export type EvalListItem = {
  eval_id: string;
  status: string;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  summary?: Record<string, unknown>;
};

export type EvalDetail = {
  eval_id: string;
  status: string;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  config: Record<string, unknown>;
  summary: Record<string, unknown>;
  details: {
    runs?: Array<{
      run_id: string;
      query: string;
      status: string;
      citations: number;
      grounding_score?: number | null;
      wall_time_s?: number | null;
      answer_preview?: string;
    }>;
  };
  error?: { message?: string } | null;
};

export type RunComparison = {
  left_run_id: string;
  right_run_id: string;
  left_status: string;
  right_status: string;
  left_citations: number;
  right_citations: number;
  overlap_paths: string[];
  overlap_ratio: number;
  left_grounding?: number | null;
  right_grounding?: number | null;
  left_wall_time_s?: number | null;
  right_wall_time_s?: number | null;
  left_answer_preview?: string;
  right_answer_preview?: string;
};

export type TraceSummary = {
  run_id: string;
  events_total: number;
  type_counts: Record<string, number>;
  iterations: number[];
  first_event_ts?: string | null;
  last_event_ts?: string | null;
  last_seq?: number | null;
};

export type TraceStep = {
  run_id: string;
  seq: number;
  timestamp: string;
  type: string;
  payload: Record<string, unknown>;
};
