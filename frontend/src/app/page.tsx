"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, GitBranch, Loader2, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import type { Repository } from "@/types";
import Link from "next/link";

export default function Home() {
  const [showAddModal, setShowAddModal] = useState(false);
  const [githubUrl, setGithubUrl] = useState("");
  const queryClient = useQueryClient();

  const { data: reposData, isLoading } = useQuery({
    queryKey: ["repositories"],
    queryFn: () => api.getRepositories(),
  });

  const createMutation = useMutation({
    mutationFn: (url: string) => api.createRepository(url),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["repositories"] });
      setShowAddModal(false);
      setGithubUrl("");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteRepository(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["repositories"] });
    },
  });

  const syncMutation = useMutation({
    mutationFn: (id: string) => api.syncRepository(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["repositories"] });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (githubUrl.trim()) {
      createMutation.mutate(githubUrl);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              <GitBranch className="w-8 h-8 text-primary-600" />
              <h1 className="text-2xl font-bold text-gray-900">CodeReadAI</h1>
            </div>
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
            >
              <Plus className="w-5 h-5" />
              リポジトリを追加
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h2 className="text-xl font-semibold text-gray-800 mb-6">
          登録済みリポジトリ
        </h2>

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          </div>
        ) : reposData?.repositories.length === 0 ? (
          <div className="bg-white rounded-lg border p-12 text-center">
            <GitBranch className="w-16 h-16 mx-auto text-gray-300 mb-4" />
            <p className="text-gray-500 mb-4">
              リポジトリがまだ登録されていません
            </p>
            <button
              onClick={() => setShowAddModal(true)}
              className="text-primary-600 hover:text-primary-700 font-medium"
            >
              最初のリポジトリを追加する
            </button>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {reposData?.repositories.map((repo: Repository) => (
              <div
                key={repo.id}
                className="bg-white rounded-lg border hover:shadow-md transition-shadow"
              >
                <Link href={`/repos/${repo.id}`} className="block p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-1">
                    {repo.owner}/{repo.name}
                  </h3>
                  <p className="text-sm text-gray-500 mb-4 line-clamp-2">
                    {repo.summary || "解析待ち..."}
                  </p>
                  <div className="flex items-center justify-between text-xs text-gray-400">
                    <span>{repo.default_branch}</span>
                    <span>
                      {new Date(repo.updated_at).toLocaleDateString("ja-JP")}
                    </span>
                  </div>
                </Link>
                <div className="px-6 pb-4 flex gap-2">
                  <button
                    onClick={() => syncMutation.mutate(repo.id)}
                    disabled={syncMutation.isPending}
                    className="flex-1 py-2 text-sm text-primary-600 hover:bg-primary-50 rounded transition-colors disabled:opacity-50"
                  >
                    {syncMutation.isPending ? "解析中..." : "再解析"}
                  </button>
                  <button
                    onClick={() => {
                      if (confirm("このリポジトリを削除しますか？")) {
                        deleteMutation.mutate(repo.id);
                      }
                    }}
                    className="p-2 text-red-500 hover:bg-red-50 rounded transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Add Repository Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
            <h2 className="text-xl font-semibold mb-4">リポジトリを追加</h2>
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label
                  htmlFor="github-url"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  GitHub URL
                </label>
                <input
                  id="github-url"
                  type="text"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  placeholder="https://github.com/owner/repo"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
              </div>
              {createMutation.isError && (
                <p className="text-red-500 text-sm mb-4">
                  エラー: リポジトリの追加に失敗しました
                </p>
              )}
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="flex-1 py-2 border rounded-lg hover:bg-gray-50 transition-colors"
                >
                  キャンセル
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending || !githubUrl.trim()}
                  className="flex-1 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {createMutation.isPending && (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  )}
                  追加
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
