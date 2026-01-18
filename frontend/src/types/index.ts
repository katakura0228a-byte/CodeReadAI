export interface Repository {
  id: string;
  github_url: string;
  name: string;
  owner: string;
  default_branch: string;
  last_commit_hash: string | null;
  summary: string | null;
  created_at: string;
  updated_at: string;
}

export interface Directory {
  id: string;
  path: string;
  name: string;
  summary: string | null;
  created_at: string;
  updated_at: string;
  children?: Directory[];
  files?: File[];
}

export interface File {
  id: string;
  path: string;
  name: string;
  language: string | null;
  summary: string | null;
  line_count: number | null;
  created_at: string;
  updated_at: string;
  code_units?: CodeUnit[];
}

export interface CodeUnit {
  id: string;
  type: "function" | "class" | "method";
  name: string;
  start_line: number;
  end_line: number;
  signature: string | null;
  description: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  children?: CodeUnit[];
}

export interface TreeNode {
  id: string;
  name: string;
  path: string;
  type: "directory" | "file";
  summary: string | null;
  children?: TreeNode[];
  language?: string;
}

export interface AnalysisJob {
  id: string;
  repository_id: string;
  status: "pending" | "running" | "completed" | "failed";
  job_type: "full" | "incremental";
  progress: number;
  total_files: number | null;
  processed_files: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}
