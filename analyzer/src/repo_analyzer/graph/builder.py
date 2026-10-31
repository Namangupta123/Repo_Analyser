from __future__ import annotations

from repo_analyzer.core.models import FileRecord, GraphEdge, GraphNode, ResolvedImport
from repo_analyzer.core.status import RelationshipType, ResolutionKind
from repo_analyzer.scanner.scanner import stable_id


def build_graph(
    files: list[FileRecord],
    resolved_imports: list[ResolvedImport],
) -> tuple[list[GraphNode], list[GraphEdge]]:
    nodes: dict[str, GraphNode] = {
        record.file_id: GraphNode(
            id=record.file_id,
            type="file",
            name=record.relative_path.rsplit("/", 1)[-1],
            path=record.relative_path,
            metadata={
                "language": record.language,
                "content_hash": record.content_hash,
                "status": record.status.value,
            },
        )
        for record in files
    }
    edges: dict[str, GraphEdge] = {}

    for resolved in resolved_imports:
        if resolved.kind == ResolutionKind.UNRESOLVED:
            continue
        if resolved.kind == ResolutionKind.LOCAL:
            if resolved.target_file_id is None:
                continue
            target_id = resolved.target_file_id
            relationship = RelationshipType.IMPORTS
        else:
            if resolved.package_name is None or resolved.ecosystem is None:
                continue
            external_key = f"{resolved.ecosystem}:{resolved.package_name}"
            target_id = stable_id("external", external_key)
            relationship = RelationshipType.USES_EXTERNAL_PACKAGE
            nodes[target_id] = GraphNode(
                id=target_id,
                type="external_package",
                name=resolved.package_name,
                metadata={"ecosystem": resolved.ecosystem},
            )

        edge_key = ":".join((
            resolved.source_file_id,
            target_id,
            relationship.value,
            resolved.module,
            str(resolved.evidence.line),
            str(resolved.evidence.column),
        ))
        edge_id = stable_id("edge", edge_key)
        edges[edge_id] = GraphEdge(
            id=edge_id,
            source=resolved.source_file_id,
            target=target_id,
            relationship_type=relationship,
            confidence=resolved.confidence,
            evidence=resolved.evidence,
        )

    return (
        sorted(nodes.values(), key=lambda node: (node.type.value, node.path or "", node.name)),
        sorted(edges.values(), key=lambda edge: edge.id),
    )

