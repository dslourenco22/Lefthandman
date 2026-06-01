export interface Score {
  overall: number;
  breakdown: Record<string, number | string>;
  matched_skills: string[];
  missing_skills: string[];
  strengths: string[];
  weaknesses: string[];
  recommendation: string;
  recommendation_reason: string;
  summary: string;
}

export interface Candidate {
  id: number;
  job_id: number;
  name: string;
  email: string;
  phone: string;
  linkedin: string;
  github: string;
  location: string;
  years_experience: number;
  summary: string;
  certifications: string[];
  education: { text: string; level: string }[];
  status: string;
  score: Score | null;
}

export interface RankedCandidate {
  rank: number;
  candidate: Candidate;
}

export interface Job {
  id: number;
  title: string;
  required_skills: string[];
  preferred_skills: string[];
  certifications: string[];
  education: string[];
  keywords: string[];
  soft_skills: string[];
  industry_terms: string[];
  min_years_experience: number;
  weights: Record<string, number>;
  created_at: string;
}

export interface ProcessingStatus {
  job_id: number;
  total: number;
  scored: number;
  processing: number;
  pending: number;
  errored: number;
  done: boolean;
}
