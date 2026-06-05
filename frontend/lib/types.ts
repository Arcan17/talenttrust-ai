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

// --- candidates ---

export type CandidateStatus = "received" | "analyzed";

export interface ParsedProfile {
  language: string;
  emails: string[];
  phones: string[];
  links: string[];
  skills: string[];
  char_count: number;
}

export interface CandidateDocument {
  id: string;
  filename: string;
  content_type: "pdf" | "docx";
  size_bytes: number;
  sha256: string;
  parsed: ParsedProfile;
}

export interface Consent {
  id: string;
  version: string;
  scope: string;
}

export interface Candidate {
  id: string;
  organization_id: string;
  vacancy_id: string;
  display_name: string | null;
  status: CandidateStatus;
  document: CandidateDocument | null;
  consent: Consent | null;
}

export type CandidateUploadResponse = Candidate;

// --- score ---

export type Recommendation =
  | "high_priority_interview"
  | "good_review_gaps"
  | "needs_human_review"
  | "low_fit";

export interface ScoreBreakdown {
  factor: string;
  weight: number;
  sub_score: number;
  weighted: number;
}

export interface Score {
  id: string;
  candidate_id: string;
  value: number; // 0–100
  recommendation: Recommendation;
  breakdown: ScoreBreakdown[];
  narrative: Record<string, unknown> | null;
}

// --- dossier ---

export type EvidenceSource = "cv" | "vacancy" | "score_breakdown" | "system_rule";

export interface EvidenceItem {
  source: EvidenceSource;
  detail: string;
}

export interface SkillEvidence {
  name: string;
  required: boolean;
  evidence: EvidenceItem[];
}

export interface GapItem {
  requirement: string;
  note: string;
  evidence: EvidenceItem[];
}

export interface InconsistencyItem {
  signal: string;
  message: string;
  severity: string;
  evidence: EvidenceItem[];
}

export interface InterviewQuestion {
  question: string;
  rationale: string;
  based_on: string;
  evidence: EvidenceItem[];
}

export interface DossierSummary {
  text: string;
  score: number;
  recommendation: Recommendation;
  evidence: EvidenceItem[];
}

export interface Dossier {
  id: string;
  candidate_id: string;
  vacancy_id: string;
  status: CandidateStatus;
  summary: DossierSummary;
  skills: SkillEvidence[];
  gaps: GapItem[];
  inconsistencies: InconsistencyItem[];
  interview_questions: InterviewQuestion[];
  recommendation: Recommendation;
}

// --- decision (backend contract: interview | review | reject | hold) ---

export type DecisionOutcome = "interview" | "review" | "reject" | "hold";

export interface Decision {
  id: string;
  candidate_id: string;
  organization_id: string;
  actor_user_id: string | null;
  human_outcome: DecisionOutcome;
  ai_recommendation: Recommendation;
  note: string | null;
  decided_at: string;
}

export interface DecisionRequest {
  human_outcome: DecisionOutcome;
  note?: string;
}
