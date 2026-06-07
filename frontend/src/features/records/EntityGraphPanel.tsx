import { GitBranch } from "lucide-react";
import { Link } from "react-router-dom";

import { StatusBadge } from "../../components/StatusBadge";

export type EntityGraph = {
  nodes?: Array<{
    id: string | number;
    label?: string;
    title?: string;
    type?: string;
  }>;
  edges?: Array<{
    source?: string | number;
    target?: string | number;
    label?: string;
    type?: string;
  }>;
};

type EntityGraphPanelProps = {
  graph?: EntityGraph;
  isLoading?: boolean;
};

export function EntityGraphPanel({ graph, isLoading = false }: EntityGraphPanelProps) {
  const nodes = graph?.nodes ?? [];
  const edges = graph?.edges ?? [];

  return (
    <section className="table-panel detail-panel" aria-labelledby="entity-graph-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Relationships</p>
          <h2 id="entity-graph-title">Entity Graph</h2>
        </div>
        <StatusBadge tone={nodes.length ? "active" : "neutral"}>
          {isLoading ? "Loading" : `${nodes.length} Nodes`}
        </StatusBadge>
      </div>
      <div className="record-panel-body">
        {nodes.length === 0 ? (
          <p className="admin-muted">No relationships are recorded yet.</p>
        ) : (
          <div className="graph-list" role="list" aria-label="Entity graph nodes">
            {nodes.map((node) => (
              <div className="graph-node" role="listitem" key={node.id}>
                <GitBranch aria-hidden="true" size={16} />
                <div>
                  <strong>{node.label ?? node.title ?? node.id}</strong>
                  <span>{node.type ?? "entity"}</span>
                </div>
                {node.type === "record" && (
                  <Link to={`/records/${node.id}`} className="text-link">
                    Open
                  </Link>
                )}
              </div>
            ))}
          </div>
        )}
        {edges.length > 0 && (
          <div className="relationship-list" aria-label="Entity graph relationships">
            {edges.map((edge, index) => (
              <span key={`${edge.source}-${edge.target}-${index}`}>
                {edge.source} to {edge.target}: {edge.label ?? edge.type ?? "related"}
              </span>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
