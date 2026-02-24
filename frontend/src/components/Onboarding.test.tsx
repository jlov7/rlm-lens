import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { Onboarding } from './Onboarding';
import {
  createCorpus,
  getDiagnostics,
  getIndexJob,
  listStarterCorpora,
  materializeStarterCorpus,
} from '../lib/api';

vi.mock('../lib/api', () => ({
  createCorpus: vi.fn(),
  getDiagnostics: vi.fn(),
  getIndexJob: vi.fn(),
  listStarterCorpora: vi.fn(),
  materializeStarterCorpus: vi.fn(),
}));

describe('Onboarding instant demo', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(getDiagnostics).mockResolvedValue({
      provider: { openai_api_key_present: true },
      environment: { docker_installed: true, docker_running: true },
    });

    vi.mocked(listStarterCorpora).mockResolvedValue([
      {
        id: 'fixture-small',
        name: 'Fixture Starter',
        description: 'Small deterministic starter corpus',
        size_label: '~2MB',
        approx_files: 18,
        source_type: 'local-copy',
        license: 'MIT',
        default_prompts: ['where retry policy'],
        network_required: false,
        installed: true,
        path: '../examples/sample_corpus',
      },
    ]);

    vi.mocked(materializeStarterCorpus).mockResolvedValue({
      pack_id: 'fixture-small',
      name: 'Fixture Starter',
      path: '../examples/sample_corpus',
      installed: true,
      already_present: true,
      files_total: 18,
      bytes_total: 12_000,
    });

    vi.mocked(createCorpus).mockResolvedValue({
      corpus_id: 'cor_demo',
      index_job_id: 'idx_demo',
    });

    vi.mocked(getIndexJob).mockResolvedValue({
      job_id: 'idx_demo',
      status: 'succeeded',
      progress: {
        files_total: 18,
        files_done: 18,
        current_path: 'done',
      },
      summary: {},
    });
  });

  it('runs instant demo setup and calls onReady', async () => {
    const onReady = vi.fn();
    render(<Onboarding onReady={onReady} />);

    await waitFor(() => {
      expect(listStarterCorpora).toHaveBeenCalled();
    });

    await userEvent.click(screen.getByRole('button', { name: /instant demo \(materialize \+ index\)/i }));

    await waitFor(() => {
      expect(onReady).toHaveBeenCalledWith(
        expect.objectContaining({
          corpusId: 'cor_demo',
        })
      );
    });

    expect(materializeStarterCorpus).toHaveBeenCalledWith('fixture-small');
    expect(createCorpus).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'Fixture Starter',
        path: '../examples/sample_corpus',
      })
    );
  });

  it('shows multiple provider options in model step', async () => {
    render(<Onboarding onReady={vi.fn()} />);

    await waitFor(() => {
      expect(listStarterCorpora).toHaveBeenCalled();
    });

    await userEvent.click(screen.getByRole('button', { name: /^Continue$/ }));
    expect(screen.getByRole('heading', { name: /provider and model/i })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: /OpenAI/i })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: /Anthropic/i })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: /OpenRouter/i })).toBeInTheDocument();
  });
});
