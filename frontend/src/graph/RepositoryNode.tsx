import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { RepositoryFlowNode } from './layout';

export function RepositoryNode({ data, selected }: NodeProps<RepositoryFlowNode>) {
  const language = typeof data.metadata.language === 'string' ? data.metadata.language : null;
  const extension = data.path?.split('.').at(-1)?.toUpperCase();
  const badge = data.nodeType === 'external_package' ? 'PKG' : language?.slice(0, 3).toUpperCase() || extension || 'FILE';

  return (
    <div
      className={`repository-node repository-node-${data.nodeType} ${selected ? 'is-selected' : ''}`}
      title={data.path ?? data.label}
    >
      <Handle type="target" position={Position.Left} />
      <span className="node-kind">{badge}</span>
      <div className="node-copy">
        <strong>{data.label}</strong>
        <span>{data.path ?? 'External dependency'}</span>
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
