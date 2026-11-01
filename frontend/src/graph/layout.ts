import dagre from '@dagrejs/dagre';
import { MarkerType, type Edge, type Node } from '@xyflow/react';
import type { GraphEdge, GraphEnvelope, GraphNode } from '../types/api';

export interface RepositoryNodeData extends Record<string, unknown> {
  label: string;
  path: string | null;
  nodeType: GraphNode['type'];
  metadata: Record<string, unknown>;
  matched: boolean;
}

export type RepositoryFlowNode = Node<RepositoryNodeData, 'repositoryNode'>;

const NODE_WIDTH = 228;
const NODE_HEIGHT = 72;

export function layoutGraph(
  graph: GraphEnvelope,
  options: { includeExternal?: boolean; search?: string } = {},
): { nodes: RepositoryFlowNode[]; edges: Edge[] } {
  const includeExternal = options.includeExternal ?? true;
  const search = options.search?.trim().toLocaleLowerCase() ?? '';
  const sourceNodes = graph.nodes.filter((node) => includeExternal || node.type !== 'external_package');
  const visibleIds = new Set(sourceNodes.map((node) => node.id));
  const sourceEdges = graph.edges.filter(
    (edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target),
  );

  const layout = new dagre.graphlib.Graph();
  layout.setDefaultEdgeLabel(() => ({}));
  layout.setGraph({ rankdir: 'LR', ranksep: 90, nodesep: 30, marginx: 32, marginy: 32 });

  sourceNodes.forEach((node) => layout.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT }));
  sourceEdges.forEach((edge) => layout.setEdge(edge.source, edge.target));
  dagre.layout(layout);

  const nodes: RepositoryFlowNode[] = sourceNodes.map((node) => {
    const position = layout.node(node.id) as { x: number; y: number };
    const haystack = `${node.name} ${node.path ?? ''}`.toLocaleLowerCase();
    const matched = !search || haystack.includes(search);
    return {
      id: node.id,
      type: 'repositoryNode',
      position: {
        x: position.x - NODE_WIDTH / 2,
        y: position.y - NODE_HEIGHT / 2,
      },
      data: {
        label: node.name,
        path: node.path,
        nodeType: node.type,
        metadata: node.metadata,
        matched,
      },
      style: { opacity: matched ? 1 : 0.2 },
    };
  });

  const edges = sourceEdges.map(toFlowEdge);
  return { nodes, edges };
}

function toFlowEdge(edge: GraphEdge): Edge {
  const external = edge.relationship_type === 'USES_EXTERNAL_PACKAGE';
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    type: 'smoothstep',
    animated: false,
    label: external ? 'external' : undefined,
    markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14 },
    style: {
      stroke: external ? '#a98bff' : '#55d6be',
      strokeWidth: 1.5,
      strokeDasharray: external ? '5 4' : undefined,
    },
    data: {
      confidence: edge.confidence,
      evidence: edge.evidence,
      relationshipType: edge.relationship_type,
    },
  };
}
