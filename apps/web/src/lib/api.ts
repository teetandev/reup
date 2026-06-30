const API_URL = process.env.NEXT_PUBLIC_CONTROL_API_URL || 'http://localhost:8000';

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    display_name: string;
    role: string;
  };
}

export interface Job {
  id: string;
  user_id: string;
  node_id: string | null;
  status: string;
  current_step: string | null;
  progress_percent: number;
  original_filename: string | null;
  file_size_bytes: number | null;
  duration_seconds: number | null;
  resolution: string | null;
  node_download_url: string | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  assigned_at: string | null;
  upload_started_at: string | null;
  upload_completed_at: string | null;
  processing_started_at: string | null;
  completed_at: string | null;
  expires_at: string | null;
  updated_at: string;
}

export interface JobListResponse {
  jobs: Job[];
}

export interface CreateJobResponse {
  job_id: string;
  status: string;
  upload: {
    url: string;
    token: string;
    expires_at: string;
  };
}

export class ApiError extends Error {
  constructor(public code: string, message: string, public status: number) {
    super(message);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  const data = await res.json();

  if (!res.ok) {
    // Session expired / invalid token → clear and bounce to login.
    if (res.status === 401 && typeof window !== 'undefined' && path !== '/auth/login') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    throw new ApiError(
      data.error?.code || 'UNKNOWN_ERROR',
      data.error?.message || 'An error occurred',
      res.status
    );
  }
  return data;
}

export interface User {
  id: string;
  display_name: string;
  role: string;
  status: string;
  max_file_mb: number;
  max_concurrent_jobs: number;
  daily_job_limit: number;
}

export interface ApiKey {
  id: string;
  key_prefix: string;
  status: string;
  name: string | null;
  created_at: string;
}

export interface Node {
  id: string;
  name: string;
  public_url: string;
  status: string;
  enabled: boolean;
  max_jobs: number;
  current_job_id: string | null;
  node_token_prefix: string | null;
  agent_version: string | null;
  cpu_percent: number | null;
  ram_used_mb: number | null;
  ram_total_mb: number | null;
  disk_free_gb: number | null;
  last_heartbeat_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DashboardStats {
  total_users: number;
  active_jobs: number;
  idle_nodes: number;
  busy_nodes: number;
  offline_nodes: number;
  failed_jobs_today: number;
}

export const api = {
  login: (secretKey: string) =>
    request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ secret_key: secretKey }),
    }),

  createJob: (filename: string, fileSize: number) =>
    request<CreateJobResponse>('/jobs', {
      method: 'POST',
      body: JSON.stringify({ original_filename: filename, file_size_bytes: fileSize }),
    }),

  getJob: (jobId: string) => request<Job>(`/jobs/${jobId}`),

  listJobs: () => request<JobListResponse>('/jobs').then((r) => r.jobs),

  admin: {
    getStats: () => request<DashboardStats>('/admin/stats'),
    listUsers: () => request<User[]>('/admin/users'),
    getUser: (userId: string) => request<User>(`/admin/users/${userId}`),
    createUser: (data: { display_name: string; daily_job_limit: number; max_file_mb: number }) =>
      request<User>('/admin/users', { method: 'POST', body: JSON.stringify(data) }),
    issueKey: (userId: string, name?: string) =>
      request<{ secret_key: string; key_prefix: string }>(`/admin/users/${userId}/keys`, {
        method: 'POST',
        body: JSON.stringify({ name }),
      }),
    revokeKey: (keyId: string) =>
      request<{ id: string; status: string }>(`/admin/keys/${keyId}/revoke`, {
        method: 'POST',
      }),
    listNodes: () => request<Node[]>('/admin/nodes'),
    getNode: (nodeId: string) => request<Node>(`/admin/nodes/${nodeId}`),
    registerNode: (data: { name: string; public_url: string }) =>
      request<{ id: string; name: string; public_url: string; status: string; node_token: string; node_token_prefix: string; install_command: string }>('/admin/nodes', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    toggleNodeEnabled: (nodeId: string, enabled: boolean) =>
      request<Node>(`/admin/nodes/${nodeId}`, {
        method: 'PATCH',
        body: JSON.stringify({ enabled }),
      }),
    listAllJobs: () => request<JobListResponse>('/admin/jobs').then((r) => r.jobs),
    getJob: (jobId: string) => request<Job>(`/admin/jobs/${jobId}`),
  },
};

export function uploadToNode(
  uploadUrl: string,
  uploadToken: string,
  file: File,
  onProgress: (percent: number) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', uploadUrl);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
      } else {
        reject(new Error(`Upload failed: ${xhr.statusText}`));
      }
    };

    xhr.onerror = () => reject(new Error('Upload failed'));

    const formData = new FormData();
    formData.append('file', file);
    formData.append('upload_token', uploadToken);
    xhr.send(formData);
  });
}

export async function startJob(nodeUrl: string, jobId: string, uploadToken: string): Promise<void> {
  const formData = new FormData();
  formData.append('upload_token', uploadToken);

  const res = await fetch(`${nodeUrl}/jobs/${jobId}/start`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    throw new Error('Failed to start job');
  }
}
