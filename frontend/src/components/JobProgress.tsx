"use client";

import type { AnalysisJob } from "@/types";

interface JobProgressProps {
  job: AnalysisJob;
}

export function JobProgress({ job }: JobProgressProps) {
  return (
    <div className="bg-primary-50 border-b border-primary-100">
      <div className="max-w-full mx-auto px-4 py-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-primary-700">
            {job.job_type === "full" ? "全体解析" : "増分更新"} 実行中...
          </span>
          <span className="text-sm text-primary-600">
            {job.processed_files}/{job.total_files || "?"} ファイル処理済み
          </span>
        </div>
        <div className="w-full bg-primary-200 rounded-full h-2">
          <div
            className="bg-primary-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${job.progress}%` }}
          />
        </div>
      </div>
    </div>
  );
}
