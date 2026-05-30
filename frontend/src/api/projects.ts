import { api } from "./client";
import type {
  IngestEnqueued,
  Project,
  ProjectDetail,
  Question,
} from "../types";

export async function listProjects(): Promise<Project[]> {
  const { data } = await api.get<Project[]>("/api/projects");
  return data;
}

export async function getProject(id: string): Promise<ProjectDetail> {
  const { data } = await api.get<ProjectDetail>(`/api/projects/${id}`);
  return data;
}

export async function createProject(
  name: string,
  docsUrl?: string,
): Promise<ProjectDetail> {
  const { data } = await api.post<ProjectDetail>("/api/projects", {
    name,
    docs_url: docsUrl || null,
  });
  return data;
}

export async function deleteProject(id: string): Promise<void> {
  await api.delete(`/api/projects/${id}`);
}

export async function ingestMarkdown(
  id: string,
  content: string,
  defaultTitle = "Untitled",
): Promise<IngestEnqueued> {
  const { data } = await api.post<IngestEnqueued>(`/api/projects/${id}/ingest`, {
    type: "markdown",
    content,
    default_title: defaultTitle,
  });
  return data;
}

export async function ingestUrl(
  id: string,
  url: string,
  maxPages = 200,
): Promise<IngestEnqueued> {
  const { data } = await api.post<IngestEnqueued>(`/api/projects/${id}/ingest`, {
    type: "url",
    url,
    max_pages: maxPages,
  });
  return data;
}

export async function listQuestions(
  id: string,
  limit = 100,
): Promise<Question[]> {
  const { data } = await api.get<Question[]>(
    `/api/projects/${id}/questions`,
    { params: { limit } },
  );
  return data;
}
