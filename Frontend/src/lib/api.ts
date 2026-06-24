const API_BASE_URL = 'http://localhost:8000';

export interface Source {
  doc_name: string;
  page_number: string | number;
  score: number | null;
  type: string;
  summary: string;
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
  ragas?: any;
}

export interface UploadResponse {
  message: string;
  chunks_created: number;
  files: string[];
}

export const api = {
  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/health`);
      return response.ok;
    } catch {
      return false;
    }
  },

  async getDocuments(): Promise<string[]> {
    const response = await fetch(`${API_BASE_URL}/api/documents`);
    if (!response.ok) {
      throw new Error('Failed to fetch documents list');
    }
    return response.json();
  },

  async uploadFiles(files: FileList | File[]): Promise<UploadResponse> {
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }

    const response = await fetch(`${API_BASE_URL}/api/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(errData.detail || 'Failed to upload files');
    }

    return response.json();
  },

  async askQuestion(question: string, apiKey?: string, runRagas?: boolean): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question,
        api_key: apiKey?.trim() || null,
        run_ragas: !!runRagas,
      }),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(errData.detail || 'Failed to get answer');
    }

    return response.json();
  },

  async resetDatabase(): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE_URL}/api/reset`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error('Failed to reset database');
    }

    return response.json();
  },
};
