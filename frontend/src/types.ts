export type ProjectStatus =
  | "pending"
  | "crawling"
  | "embedding"
  | "ready"
  | "failed";

export interface Project {
  id: string;
  name: string;
  docs_url: string | null;
  status: ProjectStatus;
  last_ingested_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectDetail extends Project {
  embed_snippet: string;
}

export interface IngestEnqueued {
  project_id: string;
  job_id: string;
  status: string;
  type: string;
}

export interface CitationRef {
  chunk_id: string;
  title: string | null;
  url: string | null;
}

export interface Question {
  id: string;
  question_text: string;
  answer_text: string;
  citations: CitationRef[];
  created_at: string;
}
