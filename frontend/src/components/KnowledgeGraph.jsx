import { useState, useEffect, useRef } from "react";
import api from "../api/axios";

export default function KnowledgeGraph({ documentId, workspaceId }) {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [viewMode, setViewMode] = useState("graph");
  const canvasRef = useRef(null);

  useEffect(() => {
    fetchGraph();
  }, [documentId, workspaceId]);

  const fetchGraph = async () => {
    setIsLoading(true);
    try {
      const endpoint = documentId
        ? `/knowledge/graph/${documentId}`
        : workspaceId
        ? `/knowledge/graph/workspace/${workspaceId}`
        : "/knowledge/graph";
      
      const res = await api.get(endpoint);
      setNodes(res.data.nodes || []);
      setEdges(res.data.edges || []);
    } catch (err) {
      // Use mock data for demo
      setNodes(MOCK_NODES);
      setEdges(MOCK_EDGES);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="bg-slate-800 rounded-xl p-6">
        <div className="animate-pulse space-y-3">
          <div className="h-8 bg-slate-700 rounded w-1/4"></div>
          <div className="h-64 bg-slate-700 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-white">Knowledge Graph</h3>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">{nodes.length} nodes</span>
            <span className="text-xs text-slate-400">{edges.length} edges</span>
          </div>
        </div>
      </div>

      {/* View mode toggle */}
      <div className="p-3 border-b border-slate-700 flex gap-2">
        <button
          onClick={() => setViewMode("graph")}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
            viewMode === "graph"
              ? "bg-blue-600 text-white"
              : "bg-slate-700 text-slate-300 hover:bg-slate-600"
          }`}
        >
          🌐 Graph
        </button>
        <button
          onClick={() => setViewMode("list")}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
            viewMode === "list"
              ? "bg-blue-600 text-white"
              : "bg-slate-700 text-slate-300 hover:bg-slate-600"
          }`}
        >
          📋 List
        </button>
        <button
          onClick={fetchGraph}
          className="ml-auto px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-700 text-slate-300 hover:bg-slate-600 transition"
        >
          🔄 Refresh
        </button>
      </div>

      {/* Content */}
      <div className="h-96 overflow-hidden">
        {viewMode === "graph" ? (
          <GraphView
            nodes={nodes}
            edges={edges}
            selectedNode={selectedNode}
            onSelectNode={setSelectedNode}
            canvasRef={canvasRef}
          />
        ) : (
          <ListView
            nodes={nodes}
            edges={edges}
            selectedNode={selectedNode}
            onSelectNode={setSelectedNode}
          />
        )}
      </div>

      {/* Node detail panel */}
      {selectedNode && (
        <NodeDetail
          node={selectedNode}
          edges={edges.filter((e) => e.source === selectedNode.id || e.target === selectedNode.id)}
          allNodes={nodes}
          onClose={() => setSelectedNode(null)}
        />
      )}
    </div>
  );
}

function GraphView({ nodes, edges, selectedNode, onSelectNode, canvasRef }) {
  const [positions, setPositions] = useState({});
  const containerRef = useRef(null);

  // Simple force-directed layout
  useEffect(() => {
    if (nodes.length === 0) return;

    const newPositions = {};
    const centerX = 200;
    const centerY = 150;
    const radius = Math.min(150, nodes.length * 20);

    nodes.forEach((node, index) => {
      const angle = (2 * Math.PI * index) / nodes.length;
      newPositions[node.id] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      };
    });

    setPositions(newPositions);
  }, [nodes]);

  if (nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-500">
        <span className="text-4xl mb-2">🕸️</span>
        <p>No knowledge graph data</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="relative w-full h-full overflow-auto">
      <svg ref={canvasRef} className="w-full h-full min-w-[400px] min-h-[300px]">
        {/* Edges */}
        {edges.map((edge, index) => {
          const sourcePos = positions[edge.source];
          const targetPos = positions[edge.target];
          if (!sourcePos || !targetPos) return null;

          return (
            <g key={`edge-${index}`}>
              <line
                x1={sourcePos.x}
                y1={sourcePos.y}
                x2={targetPos.x}
                y2={targetPos.y}
                stroke="#4B5563"
                strokeWidth={1.5}
                markerEnd="url(#arrowhead)"
              />
              {edge.label && (
                <text
                  x={(sourcePos.x + targetPos.x) / 2}
                  y={(sourcePos.y + targetPos.y) / 2 - 5}
                  fill="#9CA3AF"
                  fontSize="10"
                  textAnchor="middle"
                >
                  {edge.label}
                </text>
              )}
            </g>
          );
        })}

        {/* Arrow marker */}
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#6B7280" />
          </marker>
        </defs>

        {/* Nodes */}
        {nodes.map((node) => {
          const pos = positions[node.id];
          if (!pos) return null;

          const isSelected = selectedNode?.id === node.id;
          const nodeColors = {
            concept: "#8B5CF6",
            entity: "#10B981",
            topic: "#3B82F6",
            keyword: "#F59E0B",
          };
          const color = nodeColors[node.type] || "#6B7280";

          return (
            <g
              key={node.id}
              onClick={() => onSelectNode(node)}
              className="cursor-pointer"
            >
              <circle
                cx={pos.x}
                cy={pos.y}
                r={isSelected ? 25 : 20}
                fill={color}
                stroke={isSelected ? "#FFFFFF" : "transparent"}
                strokeWidth={2}
                opacity={0.9}
              />
              <text
                x={pos.x}
                y={pos.y + 4}
                fill="#FFFFFF"
                fontSize="10"
                textAnchor="middle"
                fontWeight="medium"
              >
                {node.label?.substring(0, 2) || "?"}
              </text>
              <text
                x={pos.x}
                y={pos.y + 35}
                fill="#9CA3AF"
                fontSize="9"
                textAnchor="middle"
              >
                {node.label?.substring(0, 10)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function ListView({ nodes, edges, selectedNode, onSelectNode }) {
  const groupedNodes = nodes.reduce((acc, node) => {
    const type = node.type || "other";
    if (!acc[type]) acc[type] = [];
    acc[type].push(node);
    return acc;
  }, {});

  const nodeTypeIcons = {
    concept: "💡",
    entity: "🏷️",
    topic: "📚",
    keyword: "🔑",
    other: "📌",
  };

  return (
    <div className="p-4 space-y-4 h-full overflow-y-auto">
      {Object.entries(groupedNodes).map(([type, typeNodes]) => (
        <div key={type}>
          <div className="flex items-center gap-2 mb-2">
            <span>{nodeTypeIcons[type] || "📌"}</span>
            <h4 className="text-sm font-medium text-slate-300 capitalize">{type}s</h4>
            <span className="text-xs text-slate-500">({typeNodes.length})</span>
          </div>
          <div className="space-y-1">
            {typeNodes.map((node) => (
              <button
                key={node.id}
                onClick={() => onSelectNode(node)}
                className={`w-full text-left p-2 rounded-lg transition ${
                  selectedNode?.id === node.id
                    ? "bg-blue-900/30 border border-blue-500"
                    : "bg-slate-700/50 border border-transparent hover:bg-slate-700"
                }`}
              >
                <p className="text-sm font-medium text-white truncate">{node.label}</p>
                {node.description && (
                  <p className="text-xs text-slate-400 truncate mt-0.5">
                    {node.description}
                  </p>
                )}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function NodeDetail({ node, edges, allNodes, onClose }) {
  const connectedNodes = edges
    .filter((e) => e.source === node.id || e.target === node.id)
    .map((e) => {
      const otherId = e.source === node.id ? e.target : e.source;
      return allNodes.find((n) => n.id === otherId);
    })
    .filter(Boolean);

  return (
    <div className="p-4 border-t border-slate-700 bg-slate-900/50">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h4 className="font-semibold text-white">{node.label}</h4>
          <span className="text-xs px-2 py-0.5 bg-slate-700 rounded text-slate-400 capitalize">
            {node.type}
          </span>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-white">
          ✕
        </button>
      </div>

      {node.description && (
        <p className="text-sm text-slate-400 mb-3">{node.description}</p>
      )}

      <div className="grid grid-cols-2 gap-2 mb-3">
        {node.confidence !== undefined && (
          <div className="bg-slate-700/50 rounded p-2">
            <p className="text-xs text-slate-400">Confidence</p>
            <p className="text-sm font-medium text-green-400">
              {((node.confidence || 0.9) * 100).toFixed(0)}%
            </p>
          </div>
        )}
        {node.importance !== undefined && (
          <div className="bg-slate-700/50 rounded p-2">
            <p className="text-xs text-slate-400">Importance</p>
            <p className="text-sm font-medium text-blue-400">
              {((node.importance || 0.5) * 100).toFixed(0)}%
            </p>
          </div>
        )}
      </div>

      {connectedNodes.length > 0 && (
        <div>
          <p className="text-xs text-slate-400 mb-2">
            Connected ({connectedNodes.length})
          </p>
          <div className="flex flex-wrap gap-1">
            {connectedNodes.map((n) => (
              <span
                key={n.id}
                className="px-2 py-0.5 bg-slate-700 rounded text-xs text-slate-300"
              >
                {n.label}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Mock data for demo
const MOCK_NODES = [
  { id: "1", label: "Machine Learning", type: "topic", confidence: 0.95 },
  { id: "2", label: "Neural Networks", type: "concept", confidence: 0.9 },
  { id: "3", label: "Deep Learning", type: "concept", confidence: 0.88 },
  { id: "4", label: "Transformers", type: "concept", confidence: 0.85 },
  { id: "5", label: "NLP", type: "topic", confidence: 0.82 },
  { id: "6", label: "BERT", type: "entity", confidence: 0.8 },
  { id: "7", label: "GPT", type: "entity", confidence: 0.78 },
  { id: "8", label: "Attention", type: "concept", confidence: 0.75 },
];

const MOCK_EDGES = [
  { source: "1", target: "2", label: "includes" },
  { source: "2", target: "3", label: "part of" },
  { source: "3", target: "4", label: "uses" },
  { source: "4", target: "8", label: "based on" },
  { source: "5", target: "4", label: "uses" },
  { source: "6", target: "4", label: "implements" },
  { source: "7", target: "4", label: "implements" },
  { source: "1", target: "5", label: "subset" },
];
