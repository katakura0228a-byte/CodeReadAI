"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  GitBranch,
  Loader2,
  ArrowLeft,
  RefreshCw,
  FolderOpen,
  FileCode,
} from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { TreeNode, File, CodeUnit } from "@/types";
import { TreeView } from "@/components/TreeView";
import { JobProgress } from "@/components/JobProgress";

export default function RepositoryPage() {
  const params = useParams();
  const repoId = params.id as string;
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<"directory" | "file" | null>(
    null
  );

  const { data: repo, isLoading: repoLoading } = useQuery({
    queryKey: ["repository", repoId],
    queryFn: () => api.getRepository(repoId),
  });

  const { data: tree, isLoading: treeLoading } = useQuery({
    queryKey: ["tree", repoId],
    queryFn: () => api.getRepositoryTree(repoId),
  });

  const { data: jobs } = useQuery({
    queryKey: ["jobs", repoId],
    queryFn: () => api.getJobs(repoId),
    refetchInterval: 5000,
  });

  const { data: fileDetail, isLoading: fileLoading } = useQuery({
    queryKey: ["file", repoId, selectedPath],
    queryFn: () => api.getFile(repoId, selectedPath!),
    enabled: !!selectedPath && selectedType === "file",
  });

  const { data: dirDetail, isLoading: dirLoading } = useQuery({
    queryKey: ["directory", repoId, selectedPath],
    queryFn: () => api.getDirectory(repoId, selectedPath!),
    enabled: !!selectedPath && selectedType === "directory",
  });

  const activeJob = jobs?.jobs.find(
    (j) => j.status === "running" || j.status === "pending"
  );

  const handleNodeSelect = (node: TreeNode) => {
    setSelectedPath(node.path);
    setSelectedType(node.type);
  };

  if (repoLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  if (!repo) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-500">リポジトリが見つかりません</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-full mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="flex items-center gap-3">
              <GitBranch className="w-6 h-6 text-primary-600" />
              <div>
                <h1 className="text-xl font-bold text-gray-900">
                  {repo.owner}/{repo.name}
                </h1>
                <p className="text-sm text-gray-500">{repo.default_branch}</p>
              </div>
            </div>
            {activeJob && (
              <div className="ml-auto flex items-center gap-2 text-sm text-primary-600">
                <RefreshCw className="w-4 h-4 animate-spin" />
                解析中 ({activeJob.progress}%)
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Progress Bar */}
      {activeJob && <JobProgress job={activeJob} />}

      {/* Main Content */}
      <div className="flex h-[calc(100vh-65px)]">
        {/* Left: Tree View */}
        <div className="w-80 border-r bg-white overflow-auto">
          <div className="p-4 border-b">
            <h2 className="font-semibold text-gray-700">ファイルツリー</h2>
          </div>
          {treeLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
            </div>
          ) : tree && tree.length > 0 ? (
            <TreeView
              nodes={tree}
              selectedPath={selectedPath}
              onSelect={handleNodeSelect}
            />
          ) : (
            <div className="p-4 text-center text-gray-500">
              <p>ファイルがありません</p>
              <p className="text-sm mt-2">
                解析が完了するとファイルツリーが表示されます
              </p>
            </div>
          )}
        </div>

        {/* Right: Detail Panel */}
        <div className="flex-1 overflow-auto">
          {!selectedPath ? (
            // Repository Overview
            <div className="p-8">
              <div className="max-w-3xl">
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  リポジトリ概要
                </h2>
                {repo.summary ? (
                  <div className="bg-white rounded-lg border p-6 markdown-content">
                    <p className="whitespace-pre-wrap">{repo.summary}</p>
                  </div>
                ) : (
                  <div className="bg-gray-100 rounded-lg p-6 text-center text-gray-500">
                    <p>解析が完了するとリポジトリの概要が表示されます</p>
                  </div>
                )}
              </div>
            </div>
          ) : selectedType === "file" ? (
            // File Detail
            <FileDetail file={fileDetail} loading={fileLoading} />
          ) : (
            // Directory Detail
            <DirectoryDetail
              directory={dirDetail}
              loading={dirLoading}
              path={selectedPath}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function FileDetail({ file, loading }: { file?: File; loading: boolean }) {
  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
      </div>
    );
  }

  if (!file) {
    return (
      <div className="p-8 text-center text-gray-500">
        ファイルが見つかりません
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="max-w-4xl">
        <div className="flex items-center gap-3 mb-4">
          <FileCode className="w-6 h-6 text-primary-600" />
          <div>
            <h2 className="text-xl font-bold text-gray-900">{file.name}</h2>
            <p className="text-sm text-gray-500">{file.path}</p>
          </div>
        </div>

        <div className="flex gap-4 mb-6 text-sm text-gray-500">
          {file.language && (
            <span className="px-2 py-1 bg-gray-100 rounded">{file.language}</span>
          )}
          {file.line_count && <span>{file.line_count} 行</span>}
        </div>

        {/* File Summary */}
        {file.summary && (
          <div className="bg-white rounded-lg border p-6 mb-6">
            <h3 className="font-semibold text-gray-700 mb-3">ファイル概要</h3>
            <p className="whitespace-pre-wrap text-gray-600">{file.summary}</p>
          </div>
        )}

        {/* Code Units */}
        {file.code_units && file.code_units.length > 0 && (
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-700">
              関数・クラス ({file.code_units.length})
            </h3>
            {file.code_units.map((unit) => (
              <CodeUnitCard key={unit.id} unit={unit} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function DirectoryDetail({
  directory,
  loading,
  path,
}: {
  directory?: any;
  loading: boolean;
  path: string;
}) {
  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
      </div>
    );
  }

  if (!directory) {
    return (
      <div className="p-8 text-center text-gray-500">
        ディレクトリが見つかりません
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="max-w-3xl">
        <div className="flex items-center gap-3 mb-6">
          <FolderOpen className="w-6 h-6 text-yellow-500" />
          <div>
            <h2 className="text-xl font-bold text-gray-900">{directory.name}</h2>
            <p className="text-sm text-gray-500">{path}</p>
          </div>
        </div>

        {directory.summary ? (
          <div className="bg-white rounded-lg border p-6">
            <h3 className="font-semibold text-gray-700 mb-3">ディレクトリ概要</h3>
            <p className="whitespace-pre-wrap text-gray-600">
              {directory.summary}
            </p>
          </div>
        ) : (
          <div className="bg-gray-100 rounded-lg p-6 text-center text-gray-500">
            <p>解析が完了するとディレクトリの概要が表示されます</p>
          </div>
        )}
      </div>
    </div>
  );
}

function CodeUnitCard({ unit }: { unit: CodeUnit }) {
  const [expanded, setExpanded] = useState(false);

  const typeLabel = {
    function: "関数",
    class: "クラス",
    method: "メソッド",
  };

  const typeColor = {
    function: "bg-blue-100 text-blue-700",
    class: "bg-purple-100 text-purple-700",
    method: "bg-green-100 text-green-700",
  };

  return (
    <div className="bg-white rounded-lg border overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 text-left hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span
            className={`px-2 py-1 text-xs font-medium rounded ${typeColor[unit.type]}`}
          >
            {typeLabel[unit.type]}
          </span>
          <span className="font-mono font-medium">{unit.name}</span>
          <span className="text-xs text-gray-400 ml-auto">
            L{unit.start_line}-{unit.end_line}
          </span>
        </div>
        {unit.signature && (
          <pre className="mt-2 text-sm text-gray-600 font-mono whitespace-pre-wrap">
            {unit.signature}
          </pre>
        )}
      </button>
      {expanded && unit.description && (
        <div className="px-4 pb-4 border-t bg-gray-50">
          <div className="pt-4 markdown-content">
            <p className="whitespace-pre-wrap text-sm text-gray-600">
              {unit.description}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
