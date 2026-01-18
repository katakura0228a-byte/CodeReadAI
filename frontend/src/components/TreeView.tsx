"use client";

import { useState } from "react";
import { ChevronRight, ChevronDown, Folder, FileCode } from "lucide-react";
import type { TreeNode } from "@/types";

interface TreeViewProps {
  nodes: TreeNode[];
  selectedPath: string | null;
  onSelect: (node: TreeNode) => void;
  level?: number;
}

export function TreeView({
  nodes,
  selectedPath,
  onSelect,
  level = 0,
}: TreeViewProps) {
  return (
    <div className="py-1">
      {nodes.map((node) => (
        <TreeNodeItem
          key={node.id}
          node={node}
          selectedPath={selectedPath}
          onSelect={onSelect}
          level={level}
        />
      ))}
    </div>
  );
}

interface TreeNodeItemProps {
  node: TreeNode;
  selectedPath: string | null;
  onSelect: (node: TreeNode) => void;
  level: number;
}

function TreeNodeItem({
  node,
  selectedPath,
  onSelect,
  level,
}: TreeNodeItemProps) {
  const [expanded, setExpanded] = useState(level < 2);
  const isSelected = selectedPath === node.path;
  const hasChildren = node.children && node.children.length > 0;
  const isDirectory = node.type === "directory";

  const handleClick = () => {
    if (isDirectory && hasChildren) {
      setExpanded(!expanded);
    }
    onSelect(node);
  };

  const getLanguageColor = (lang?: string) => {
    const colors: Record<string, string> = {
      python: "text-blue-500",
      javascript: "text-yellow-500",
      typescript: "text-blue-600",
      java: "text-orange-500",
      go: "text-cyan-500",
      rust: "text-orange-600",
      c: "text-gray-600",
      cpp: "text-pink-500",
    };
    return colors[lang || ""] || "text-gray-500";
  };

  return (
    <div>
      <button
        onClick={handleClick}
        className={`w-full flex items-center gap-1 py-1.5 px-2 hover:bg-gray-100 transition-colors text-sm ${
          isSelected ? "bg-primary-50 text-primary-700" : "text-gray-700"
        }`}
        style={{ paddingLeft: `${level * 16 + 8}px` }}
      >
        {isDirectory ? (
          hasChildren ? (
            expanded ? (
              <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
            )
          ) : (
            <span className="w-4" />
          )
        ) : (
          <span className="w-4" />
        )}

        {isDirectory ? (
          <Folder
            className={`w-4 h-4 flex-shrink-0 ${
              expanded ? "text-yellow-500" : "text-yellow-400"
            }`}
          />
        ) : (
          <FileCode
            className={`w-4 h-4 flex-shrink-0 ${getLanguageColor(node.language)}`}
          />
        )}

        <span className="truncate ml-1">{node.name}</span>

        {node.summary && (
          <span
            className="ml-auto text-xs text-gray-400 truncate max-w-[120px]"
            title={node.summary}
          >
            {node.summary.slice(0, 30)}...
          </span>
        )}
      </button>

      {isDirectory && expanded && hasChildren && (
        <TreeView
          nodes={node.children!}
          selectedPath={selectedPath}
          onSelect={onSelect}
          level={level + 1}
        />
      )}
    </div>
  );
}
