export interface Job {
  id: string;
  filename: string;
  storage_path: string | null;
  status: 'PENDING' | 'PROCESSING' | 'LLM_PROCESSING' | 'REPORTING' | 'COMPLETED' | 'FAILED';
  row_count_raw: number | null;
  row_count_clean: number | null;
  error_message: string | null;
  llm_failed: boolean;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface JobEvent {
  id: string;
  job_id: string;
  event_type: string;
  domain_event_name: string;
  timestamp: string;
  metadata_: any;
}

export interface RiskSignal {
  id: string;
  transaction_id: string;
  signal_type: string;
  signal_score: number;
  description: string;
}

export interface Transaction {
  id: string;
  job_id: string;
  txn_id: string | null;
  date: string;
  merchant: string;
  amount: number;
  currency: string;
  status: string;
  category: string;
  account_id: string;
  is_anomaly: boolean;
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  notes: string | null;
  anomaly_reason: string | null;
  created_at: string;
  risk_signals: RiskSignal[];
}

export interface JobSummary {
  id: string;
  job_id: string;
  total_spend_inr: number;
  total_spend_usd: number;
  top_merchants: { merchant: string; total: number }[];
  currency_breakdown: Record<string, number>;
  anomaly_count: number;
  narrative: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
}

export interface JobDetailsResponse {
  job: Job;
  summary: JobSummary | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

const API_BASE = 'http://localhost:8000';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  try {
    const res = await fetch(url, options);
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `Request failed with status ${res.status}`);
    }
    return (await res.json()) as T;
  } catch (error) {
    console.error(`API Error on path ${path}:`, error);
    throw error;
  }
}

export const api = {
  // Get all jobs
  getJobs: (params?: { status?: string; limit?: number; offset?: number }) => {
    const query = new URLSearchParams();
    if (params?.status) query.append('status', params.status);
    if (params?.limit !== undefined) query.append('limit', String(params.limit));
    if (params?.offset !== undefined) query.append('offset', String(params.offset));
    
    return request<Job[]>(`/jobs?${query.toString()}`);
  },

  // Upload transaction CSV
  uploadCSV: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return request<Job>('/jobs/upload', {
      method: 'POST',
      body: formData,
    });
  },

  // Get single job details
  getJobDetails: (id: string) => {
    return request<JobDetailsResponse>(`/jobs/${id}`);
  },

  // Get job timeline events
  getJobTimeline: (id: string) => {
    return request<JobEvent[]>(`/jobs/${id}/timeline`);
  },

  // Get job results (paginated transactions)
  getJobResults: (id: string, params?: { limit?: number; offset?: number }) => {
    const query = new URLSearchParams();
    if (params?.limit !== undefined) query.append('limit', String(params.limit));
    if (params?.offset !== undefined) query.append('offset', String(params.offset));
    return request<PaginatedResponse<Transaction>>(`/jobs/${id}/results?${query.toString()}`);
  },

  // Check backend health status
  getHealth: () => {
    return request<{ status: string; checks?: { postgresql?: boolean; redis?: boolean; workers?: boolean; gemini?: boolean } }>('/health');
  },

  // Get operational metrics snapshot
  getMetrics: () => {
    return request<any>('/metrics');
  },

  // Get global transaction analytics
  getGlobalAnalytics: () => {
    return request<GlobalAnalytics>('/jobs/global/analytics');
  },

  // Get global transactions (filtered, paginated)
  getGlobalTransactions: (params?: {
    limit?: number;
    offset?: number;
    search?: string;
    category?: string;
    currency?: string;
    risk_level?: string;
    min_amount?: number;
    max_amount?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.limit !== undefined) query.append('limit', String(params.limit));
    if (params?.offset !== undefined) query.append('offset', String(params.offset));
    if (params?.search) query.append('search', params.search);
    if (params?.category) query.append('category', params.category);
    if (params?.currency) query.append('currency', params.currency);
    if (params?.risk_level) query.append('risk_level', params.risk_level);
    if (params?.min_amount !== undefined) query.append('min_amount', String(params.min_amount));
    if (params?.max_amount !== undefined) query.append('max_amount', String(params.max_amount));

    return request<PaginatedResponse<Transaction>>(`/jobs/global/transactions?${query.toString()}`);
  }
};

export interface GlobalAnalytics {
  category_spend: Record<string, Record<string, number>>;
  currency_spend: Record<string, number>;
  top_merchants: { merchant: string; currency: string; total: number }[];
  risk_levels: Record<string, number>;
  anomalies: Record<string, number>;
  trend: { date: string; count: number; amount: number }[];
}
