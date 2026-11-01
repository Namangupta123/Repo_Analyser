import type { ApiErrorBody } from '../types/api';

export const API_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function parseResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as T;
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    const errorBody = body as ApiErrorBody | null;
    throw new ApiError(
      response.status,
      errorBody?.detail?.code ?? 'REQUEST_FAILED',
      errorBody?.detail?.message ?? `Request failed with status ${response.status}.`,
    );
  }

  return body as T;
}

export function repositoryName(url: string): string {
  const parts = url.replace(/\/$/, '').split('/');
  return parts.at(-1) ?? url;
}

export function isPublicGitHubUrl(value: string): boolean {
  try {
    const url = new URL(value);
    const parts = url.pathname.split('/').filter(Boolean);
    return (
      url.protocol === 'https:' &&
      url.hostname === 'github.com' &&
      parts.length === 2 &&
      !url.search &&
      !url.hash
    );
  } catch {
    return false;
  }
}
