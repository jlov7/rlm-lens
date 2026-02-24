import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';

import App from './App';

describe('App operations deck', () => {
  afterEach(() => {
    window.history.pushState({}, '', '/');
  });

  it('renders advanced operations panels in deterministic test mode', async () => {
    window.history.pushState({}, '', '/?test_mode=1&static=1');
    render(<App />);

    await waitFor(() => {
      expect(window.__READY).toBe(true);
    });

    expect(screen.getByTestId('operations-deck')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /^Watch$/ }));
    expect(screen.getByTestId('watch-panel')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /^Security$/ }));
    expect(screen.getByTestId('security-panel')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /^Evals$/ }));
    expect(screen.getByTestId('eval-panel')).toBeInTheDocument();
  });

  it('opens and closes shortcut guide', async () => {
    window.history.pushState({}, '', '/?test_mode=1&static=1');
    render(<App />);

    await waitFor(() => {
      expect(window.__READY).toBe(true);
    });

    await userEvent.click(screen.getByRole('button', { name: /open keyboard shortcuts/i }));
    expect(screen.getByTestId('shortcuts-modal')).toBeInTheDocument();

    fireEvent.keyDown(window, { key: 'Escape' });
    await waitFor(() => {
      expect(screen.queryByTestId('shortcuts-modal')).not.toBeInTheDocument();
    });
  });
});
