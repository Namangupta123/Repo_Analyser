import { useMemo, useState } from 'react';
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  type NodeMouseHandler,
} from '@xyflow/react';
import { layoutGraph, type RepositoryFlowNode } from '../graph/layout';
import { RepositoryNode } from '../graph/RepositoryNode';
import type { GraphEnvelope } from '../types/api';

const nodeTypes = { repositoryNode: RepositoryNode };

export function GraphExplorer({ graph }: { graph: GraphEnvelope }) {
  const [search, setSearch] = useState('');
  const [includeExternal, setIncludeExternal] = useState(true);
  const [selected, setSelected] = useState<RepositoryFlowNode | null>(null);
  const flow = useMemo(
    () => layoutGraph(graph, { includeExternal, search }),
    [graph, includeExternal, search],
  );

  const selectNode: NodeMouseHandler<RepositoryFlowNode> = (_, node) => setSelected(node);

  return (
    <div className="graph-workspace">
      <div className="graph-toolbar">
        <label className="graph-search">
          <span aria-hidden="true">⌕</span>
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Find a file or package"
            aria-label="Find a file or package"
          />
        </label>
        <label className="toggle-control">
          <input
            type="checkbox"
            checked={includeExternal}
            onChange={(event) => setIncludeExternal(event.target.checked)}
          />
          <span />
          External packages
        </label>
        <div className="graph-legend" aria-label="Graph legend">
          <span><i className="legend-file" /> File</span>
          <span><i className="legend-package" /> Package</span>
        </div>
      </div>

      <div className="graph-canvas">
        <ReactFlow
          nodes={flow.nodes}
          edges={flow.edges}
          nodeTypes={nodeTypes}
          onNodeClick={selectNode}
          onPaneClick={() => setSelected(null)}
          nodesDraggable
          nodesConnectable={false}
          elementsSelectable
          fitView
          fitViewOptions={{ padding: 0.22, maxZoom: 1.15 }}
          minZoom={0.12}
          maxZoom={1.8}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#263950" gap={24} size={1} variant={BackgroundVariant.Dots} />
          <Controls showInteractive={false} />
          <MiniMap
            pannable
            zoomable
            nodeColor={(node) =>
              (node as RepositoryFlowNode).data.nodeType === 'external_package' ? '#8e72e8' : '#2b9e91'
            }
            maskColor="rgba(4, 11, 20, 0.76)"
          />
        </ReactFlow>
      </div>

      {selected && (
        <aside className="node-inspector">
          <button className="inspector-close" type="button" onClick={() => setSelected(null)} aria-label="Close details">
            ×
          </button>
          <p className="eyebrow">{selected.data.nodeType.replace('_', ' ')}</p>
          <h3>{selected.data.label}</h3>
          <code>{selected.data.path ?? 'External dependency'}</code>
          <dl>
            {Object.entries(selected.data.metadata).map(([key, value]) => (
              <div key={key}>
                <dt>{key.replaceAll('_', ' ')}</dt>
                <dd>{formatMetadata(value)}</dd>
              </div>
            ))}
          </dl>
        </aside>
      )}
    </div>
  );
}

function formatMetadata(value: unknown): string {
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return JSON.stringify(value);
}
