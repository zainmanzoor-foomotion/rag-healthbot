export interface Medication {
    name: string;
    purpose: string;
}
export interface ReportSummary {
    filename: string;
    summary: string;
    medications: Medication[];
}

export interface UploadedFile {
    file: File;
    preview: string | null;
}
