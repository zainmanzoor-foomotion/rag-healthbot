export interface Medication {
    name: string;
    purpose: string;
}
export interface ReportSummary {
  reportId?: string; // Added for chat/embedding context
  filename: string;
  summary: string;
  medications: Medication[];
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
