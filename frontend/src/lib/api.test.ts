import { describe, expect, it } from 'vitest';
import { isPublicGitHubUrl, repositoryName } from './api';

describe('repository URL helpers', () => {
  it('accepts only exact public HTTPS GitHub repository URLs', () => {
    expect(isPublicGitHubUrl('https://github.com/owner/repository')).toBe(true);
    expect(isPublicGitHubUrl('http://github.com/owner/repository')).toBe(false);
    expect(isPublicGitHubUrl('https://github.com/owner/repository/tree/main')).toBe(false);
    expect(isPublicGitHubUrl('https://github.com/owner/repository?token=secret')).toBe(false);
    expect(isPublicGitHubUrl('https://gitlab.com/owner/repository')).toBe(false);
  });

  it('extracts a readable repository name', () => {
    expect(repositoryName('https://github.com/SystemLab/example/')).toBe('example');
  });
});
