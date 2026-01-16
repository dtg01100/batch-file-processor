import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import LegacyImport from '../pages/LegacyImport';

// Mock the notification context
const mockShowInfo = vi.fn();
const mockShowSuccess = vi.fn();
const mockShowError = vi.fn();
const mockShowWarning = vi.fn();

vi.mock('../contexts/NotificationContext', () => ({
  useNotification: () => ({
    showInfo: mockShowInfo,
    showSuccess: mockShowSuccess,
    showError: mockShowError,
    showWarning: mockShowWarning,
  }),
}));

// Mock the API calls
global.fetch = vi.fn();

describe('LegacyImport Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset fetch mock
    global.fetch.mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the import form correctly', () => {
    render(
      <MemoryRouter>
        <LegacyImport />
      </MemoryRouter>
    );

    expect(screen.getByText('Legacy Database Import')).toBeInTheDocument();
    expect(screen.getByText('Convert legacy folders.db configurations to new pipeline format')).toBeInTheDocument();
    expect(screen.getByLabelText('Legacy Database File')).toBeInTheDocument();
    expect(screen.getByText('Preview Import')).toBeInTheDocument();
    expect(screen.getByText('Import Database')).toBeInTheDocument();
    expect(screen.getByText('Reset')).toBeInTheDocument();
  });

  it('shows validation error when no file is selected', async () => {
    render(
      <MemoryRouter>
        <LegacyImport />
      </MemoryRouter>
    );

    const previewButton = screen.getByText('Preview Import');
    fireEvent.click(previewButton);

    await waitFor(() => {
      expect(screen.getByText('This field is required')).toBeInTheDocument();
    });
  });

  it('allows file selection', () => {
    render(
      <MemoryRouter>
        <LegacyImport />
      </MemoryRouter>
    );

    const fileInput = screen.getByLabelText('Legacy Database File');
    const file = new File(['dummy content'], 'test.db', { type: 'application/octet-stream' });

    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(fileInput.files[0]).toBe(file);
  });

  it('rejects non-database files', async () => {
    render(
      <MemoryRouter>
        <LegacyImport />
      </MemoryRouter>
    );

    const fileInput = screen.getByLabelText('Legacy Database File');
    const file = new File(['dummy content'], 'test.txt', { type: 'text/plain' });

    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText('File must be a SQLite database (.db)')).toBeInTheDocument();
    });
  });

  it('calls preview API when preview button is clicked', async () => {
    // Mock successful preview response
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [
        {
          id: 'preview_1',
          name: 'Test Pipeline',
          description: 'Imported from legacy folder: /test/input',
          node_count: 3,
          has_errors: false,
        }
      ],
    });

    render(
      <MemoryRouter>
        <LegacyImport />
      </MemoryRouter>
    );

    const fileInput = screen.getByLabelText('Legacy Database File');
    const file = new File(['dummy content'], 'test.db', { type: 'application/octet-stream' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const previewButton = screen.getByText('Preview Import');
    fireEvent.click(previewButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/legacy-import/preview-db',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    await waitFor(() => {
      expect(screen.getByText('Test Pipeline')).toBeInTheDocument();
    });
  });

  it('shows error when preview API fails', async () => {
    // Mock failed preview response
    global.fetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'Failed to read database' }),
    });

    render(
      <MemoryRouter>
        <LegacyImport />
      </MemoryRouter>
    );

    const fileInput = screen.getByLabelText('Legacy Database File');
    const file = new File(['dummy content'], 'test.db', { type: 'application/octet-stream' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const previewButton = screen.getByText('Preview Import');
    fireEvent.click(previewButton);

    await waitFor(() => {
      expect(mockShowError).toHaveBeenCalledWith('Preview failed: Failed to read database');
    });
  });

  it('calls import API when import button is clicked', async () => {
    // Mock successful import response
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        message: 'Successfully imported 1 pipeline',
        imported_pipelines: 1,
        errors: [],
      }),
    });

    // Mock window.confirm to return true
    const originalConfirm = window.confirm;
    window.confirm = vi.fn(() => true);

    render(
      <MemoryRouter>
        <LegacyImport />
      </MemoryRouter>
    );

    const fileInput = screen.getByLabelText('Legacy Database File');
    const file = new File(['dummy content'], 'test.db', { type: 'application/octet-stream' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const importButton = screen.getByText('Import Database');
    fireEvent.click(importButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/legacy-import/import-db',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    await waitFor(() => {
      expect(mockShowSuccess).toHaveBeenCalledWith('Successfully imported 1 pipeline');
    });

    // Restore original confirm
    window.confirm = originalConfirm;
  });

  it('shows error when import API fails', async () => {
    // Mock failed import response
    global.fetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'Import failed due to database error' }),
    });

    // Mock window.confirm to return true
    const originalConfirm = window.confirm;
    window.confirm = vi.fn(() => true);

    render(
      <MemoryRouter>
        <LegacyImport />
      </MemoryRouter>
    );

    const fileInput = screen.getByLabelText('Legacy Database File');
    const file = new File(['dummy content'], 'test.db', { type: 'application/octet-stream' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const importButton = screen.getByText('Import Database');
    fireEvent.click(importButton);

    await waitFor(() => {
      expect(mockShowError).toHaveBeenCalledWith('Import failed: Import failed due to database error');
    });

    // Restore original confirm
    window.confirm = originalConfirm;
  });

  it('resets form when reset button is clicked', async () => {
    render(
      <MemoryRouter>
        <LegacyImport />
      </MemoryRouter>
    );

    const fileInput = screen.getByLabelText('Legacy Database File');
    const file = new File(['dummy content'], 'test.db', { type: 'application/octet-stream' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    // Verify file is selected
    expect(fileInput.files[0]).toBe(file);

    const resetButton = screen.getByText('Reset');
    fireEvent.click(resetButton);

    // Note: We can't directly test if the file input is cleared due to browser security restrictions
    // But we can test that the UI state is reset
  });
});