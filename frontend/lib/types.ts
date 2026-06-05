export type Role = "org_admin" | "recruiter" | "viewer";

export interface User {
  id: string;
  organization_id: string;
  email: string;
  role: Role;
  is_active: boolean;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export type Modality = "remote" | "hybrid" | "onsite";
export type Seniority = "junior" | "mid" | "senior";
export type VacancyStatus = "open" | "closed";

export interface Vacancy {
  id: string;
  organization_id: string;
  title: string;
  description: string;
  required_skills: string[];
  desired_skills: string[];
  modality: Modality;
  country: string | null;
  salary_min: number | null;
  salary_max: number | null;
  seniority: Seniority;
  status: VacancyStatus;
}

export interface VacancyCreate {
  title: string;
  description?: string;
  required_skills: string[];
  desired_skills?: string[];
  modality: Modality;
  country?: string | null;
  salary_min?: number | null;
  salary_max?: number | null;
  seniority: Seniority;
}
