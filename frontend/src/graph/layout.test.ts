import { describe, expect, it } from 'vitest';
import type { GraphEnvelope } from '../types/api';
import { layoutGraph } from './layout';

const graph: GraphEnvelope = {
  schema_version: '1.0.0',
  analyzer_version: '0.1.0',
  repository: {
    source: 'https://github.com/owner/repository',
    repository_url: 'https://github.com/owner/repository',
    commit_sha: 'abc123',
  },
  nodes: [
    { id: 'app', type: 'file', name: 'App.tsx', path: 'src/App.tsx', metadata: {} },
    { id: 'orders', type: 'file', name: 'Orders.tsx', path: 'src/Orders.tsx', metadata: {} },
    { id: 'react', type: 'external_package', name: 'react', path: null, metadata: {} },
  ],
  edges: [
    {
      id: 'app-orders', source: 'app', target: 'orders', relationship_type: 'IMPORTS', confidence: 1,
      evidence: { module: './Orders', line: 1, column: 0 },
    },
    {
      id: 'app-react', source: 'app', target: 'react', relationship_type: 'USES_EXTERNAL_PACKAGE', confidence: 1,
      evidence: { module: 'react', line: 2, column: 0 },
    },
  ],
};

describe('layoutGraph', () => {
  it('maps analyzer nodes and edges without changing stable IDs', () => {
    const result = layoutGraph(graph);
    expect(result.nodes.map((node) => node.id)).toEqual(['app', 'orders', 'react']);
    expect(result.edges.map((edge) => edge.id)).toEqual(['app-orders', 'app-react']);
    expect(result.nodes.every((node) => Number.isFinite(node.position.x))).toBe(true);
  });

  it('removes external nodes and their edges when filtered', () => {
    const result = layoutGraph(graph, { includeExternal: false });
    expect(result.nodes.map((node) => node.id)).toEqual(['app', 'orders']);
    expect(result.edges.map((edge) => edge.id)).toEqual(['app-orders']);
  });

  it('marks search matches while retaining graph context', () => {
    const result = layoutGraph(graph, { search: 'orders' });
    expect(result.nodes.find((node) => node.id === 'orders')?.data.matched).toBe(true);
    expect(result.nodes.find((node) => node.id === 'app')?.data.matched).toBe(false);
  });
});
