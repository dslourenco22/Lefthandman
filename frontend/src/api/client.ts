import axios from "axios";
import type { Candidate, Job, ProcessingStatus, RankedCandidate } from "./types";

const api = axios.create({ baseURL: "/api" });

// Attach the JWT to every request if present.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export async function login(email: string, password: string) {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);
  const { data } = await api.post("/auth/login", form);
  localStorage.setItem("token", data.access_token);
  localStorage.setItem("role", data.role);
  localStorage.setItem("name", data.full_name);
  return data;
}

export function logout() {
  localStorage.removeItem("token");
  localStorage.removeItem("role");
  localStorage.removeItem("name");
}

export const isAuthed = () => !!localStorage.getItem("token");
export const currentRole = () => localStorage.getItem("role") || "";

export async function createUser(
  email: string, password: string, full_name: string, role: string,
) {
  const { data } = await api.post("/auth/users", { email, password, full_name, role });
  return data;
}

export async function createJob(title: string, raw_text: string, weights?: Record<string, number>) {
  const { data } = await api.post<Job>("/jobs", { title, raw_text, weights });
  return data;
}

export async function uploadJobFile(title: string, file: File) {
  const fd = new FormData();
  fd.set("title", title);
  fd.set("file", file);
  const { data } = await api.post<Job>("/jobs/upload", fd);
  return data;
}

export async function listJobs() {
  const { data } = await api.get<Job[]>("/jobs");
  return data;
}

export async function updateWeights(jobId: number, weights: Record<string, number>) {
  const { data } = await api.put<Job>(`/jobs/${jobId}/weights`, { weights });
  return data;
}

export async function updateSkills(
  jobId: number, required_skills: string[], preferred_skills: string[],
) {
  const { data } = await api.put<Job>(`/jobs/${jobId}/skills`, {
    required_skills, preferred_skills,
  });
  return data;
}

export async function uploadResumes(jobId: number, files: File[]) {
  const fd = new FormData();
  files.forEach((f) => fd.append("files", f));
  const { data } = await api.post<ProcessingStatus>(`/jobs/${jobId}/resumes`, fd);
  return data;
}

export async function getStatus(jobId: number) {
  const { data } = await api.get<ProcessingStatus>(`/jobs/${jobId}/resumes/status`);
  return data;
}

export async function getRanking(
  jobId: number,
  params: { sort_by?: string; search?: string; min_score?: number; recommendation?: string },
) {
  const { data } = await api.get<RankedCandidate[]>(`/jobs/${jobId}/ranking`, { params });
  return data;
}

export async function getResumeText(jobId: number, candidateId: number) {
  const { data } = await api.get<{ filename: string; content_type: string; text: string }>(
    `/jobs/${jobId}/candidates/${candidateId}/resume`,
  );
  return data;
}

export async function compareCandidates(jobId: number, ids: number[]) {
  const { data } = await api.get<Candidate[]>(`/jobs/${jobId}/compare`, {
    params: { ids },
    paramsSerializer: { indexes: null },
  });
  return data;
}

export function exportUrl(jobId: number, fmt: "csv" | "xlsx" | "pdf") {
  return `/api/jobs/${jobId}/export/${fmt}`;
}

export async function downloadExport(jobId: number, fmt: "csv" | "xlsx" | "pdf") {
  const { data } = await api.get(`/jobs/${jobId}/export/${fmt}`, { responseType: "blob" });
  const url = URL.createObjectURL(data);
  const a = document.createElement("a");
  a.href = url;
  a.download = `ranking_job_${jobId}.${fmt}`;
  a.click();
  URL.revokeObjectURL(url);
}

export default api;
