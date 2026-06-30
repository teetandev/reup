'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import AdminNav from '@/components/AdminNav';
import { api, Job } from '@/lib/api';
import { STATUS_LABELS } from '@/lib/status';

export default function AdminJobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('ALL');

  useEffect(() => {
    api.admin.listAllJobs()
      .then(setJobs)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const getStatusClass = (status: string) => {
    if (status === 'DONE') return 'status-done';
    if (status === 'FAILED') return 'status-failed';
    if (['EXTRACTING_AUDIO', 'TRANSCRIBING', 'TRANSLATING', 'RENDERING'].includes(status)) {
      return 'status-processing';
    }
    return 'status-waiting';
  };

  const filteredJobs = filter === 'ALL' ? jobs : jobs.filter(j => j.status === filter);

  return (
    <>
      <AdminNav />
      <div className="container">
        <h1 style={{ marginBottom: '24px' }}>Quản lý Jobs</h1>

        <div style={{ marginBottom: '16px', display: 'flex', gap: '8px' }}>
          <button
            className={`btn ${filter === 'ALL' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setFilter('ALL')}
          >
            Tất cả
          </button>
          <button
            className={`btn ${filter === 'DONE' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setFilter('DONE')}
          >
            Hoàn tất
          </button>
          <button
            className={`btn ${filter === 'FAILED' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setFilter('FAILED')}
          >
            Lỗi
          </button>
        </div>

        {loading ? (
          <p>Đang tải...</p>
        ) : (
          <div className="card">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>User</th>
                  <th>File</th>
                  <th>Node</th>
                  <th>Trạng thái</th>
                  <th>Tiến độ</th>
                  <th>Thời gian</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filteredJobs.map((job) => (
                  <tr key={job.id}>
                    <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                      {job.id.substring(0, 8)}
                    </td>
                    <td style={{ fontSize: '12px' }}>{job.user_id.substring(0, 8)}</td>
                    <td>{job.original_filename}</td>
                    <td style={{ fontSize: '12px' }}>
                      {job.node_id ? job.node_id.substring(0, 8) : '—'}
                    </td>
                    <td>
                      <span className={`status-badge ${getStatusClass(job.status)}`}>
                        {STATUS_LABELS[job.status] || job.status}
                      </span>
                    </td>
                    <td>{Math.round(job.progress_percent)}%</td>
                    <td style={{ fontSize: '12px' }}>
                      {new Date(job.created_at).toLocaleString('vi-VN')}
                    </td>
                    <td>
                      <Link href={`/admin/jobs/${job.id}`} style={{ color: '#0066cc', fontSize: '12px' }}>
                        Chi tiết →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredJobs.length === 0 && (
              <p style={{ textAlign: 'center', color: '#666', marginTop: '16px' }}>
                Không có job nào.
              </p>
            )}
          </div>
        )}
      </div>
    </>
  );
}
