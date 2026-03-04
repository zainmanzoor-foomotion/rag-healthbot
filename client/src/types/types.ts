export interface Medication {
    id?: number | null;       // canonical medication entity id
    link_id?: number | null;  // report_medication join row id (review handle)
    name: string;
    purpose: string;
    cui?: string | null;
    confidence?: number | null;
    review_status?: string;
    is_drug_class?: boolean;
}

export interface Disease {
    id?: number | null;       // canonical disease entity id
    link_id?: number | null;  // report_disease join row id (review handle)
    name: string;
    cui?: string | null;
    icd10_code?: string | null;
    severity?: string | null;
    status?: string | null;
    confidence?: number | null;
    review_status?: string;
}

export interface Procedure {
    id?: number | null;       // canonical procedure entity id
    link_id?: number | null;  // report_procedure join row id (review handle)
    name: string;
    cui?: string | null;
    cpt_code?: string | null;
    date_performed?: string | null;
    body_site?: string | null;
    outcome?: string | null;
    confidence?: number | null;
    review_status?: string;
}

export interface ReviewCandidate {
    code: string;
    description?: string | null;
    source?: string;
    raw_score?: number;
}

export interface ReviewItem {
    id: number;               // canonical entity id
    link_id?: number | null;  // join row id (per-report review handle)
    report_id?: number | null;
    entity_type: "disease" | "procedure" | "medication";
    name: string;
    cui?: string | null;
    code?: string | null;
    confidence?: number | null;
    review_status: string;
    review_notes?: string | null;
    candidates?: ReviewCandidate[] | null;
}

export interface ReportSummary {
  reportId?: string;
  filename: string;
  summary: string;
  medications: Medication[];
  diseases: Disease[];
  procedures: Procedure[];
}

export interface UploadedFile {
    file: File;
    preview: string | null;
}


export interface Message {
  userContent: string;
  aiContent: string;
  loading?: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
}
