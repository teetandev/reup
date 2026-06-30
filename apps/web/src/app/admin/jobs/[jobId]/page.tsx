'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import AdminNav from '@/components/AdminNav';
import { api, Job } from '@/lib/api';
import { STATUS_LABELS, PROGRESS_MAP } from '@/lib/status';

export default function AdminJobDetailPage() {
  const params = useParams();
  const jobId = params.jobId as string;
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (jobId) {
      loadJob();
      const interval = setInterval(loadJob, 3000);
      return () => clearInterval(interval);
    }
  }, [jobId]);

  const loadJob = () => {
    api.getJob(jobId)
      .then(setJob)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  if (loading) {
    return (
      <>
        <AdminNav />
        <div className="container">
          <p>Đang tải...</p>
        </div>
      </>
    );
  }

  if (!job) {
    return (
      <>
        <AdminNav />
        <div className="container">
          <p>Không tìm thấy job.</p>
        </div>
      </>
    );
  }

  const progress = PROGRESS_MAP[job.status] || job.progress_percent;

  return (
    <>
      <AdminNav />
      <div className="container">
        <h1 style={{ marginBottom: '24px' }}>Chi tiết Job</h1>

        <div style={{ display: 'grid', gap: '16px' }}>
          <div className="card">
            <h2 style={{ marginBottom: '16px' }}>Trạng thái</h2>
            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px' }}>
                {STATUS_LABELS[job.status] || job.status}
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${progress}%` }}></div>
              </div>
              <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                {Math.round(progress)}%
              </div>
            </div>
            {job.error_message && (
              <div style={{ background: '#f8d7da', color: '#721c24', padding: '12px', borderRadius: '4px' }}>
                <strong>Lỗi:</strong> {job.error_message}
              </div>
            )}
          </div>

          <div className="card">
            <h2 style={{ marginBottom: '16px' }}>Thông tin</h2>
            <div style={{ display: 'grid', gap: '8px' }}>
              <div>
                <span style={{ color: '#666' }}>Job ID: </span>
                <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>{job.id}</span>
              </div>
              <div>
                <span style={{ color: '#666' }}>User ID: </span>
                <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>{job.user_id}</span>
              </div>
              <div>
                <span style={{ color: '#666' }}>Node ID: </span>
                <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>{job.node_id || '—'}</span>
              </div>
              <div>
                <span style={{ color: '#666' }}>File name: </span>
                <span>{job.original_filename}</span>
              </div>
              <div>
                <span style={{ color: '#666' }}>File size: </span>
                <span>{job.file_size_bytes ? `${(job.file_size_bytes / 1024 / 1024).toFixed(2)} MB` : '—'}</span>
              </div>
              <div>
                <span style={{ color: '#666' }}>Duration: </span>
                <span>{job.duration_seconds ? `${job.duration_seconds.toFixed(1)}s` : '—'}</span>
              </div>
              <div>
                <span style={{ color: '#666' }}>Resolution: </span>
                <span>{job.resolution || '—'}</span>
              </div>
            </div>
          </div>

          <div className="card">
            <h2 style={{ marginBottom: '16px' }}>Timeline</h2>
            <div style={{ display: 'grid', gap: '8px', fontSize: '12px' }}>
              <div>
                <span style={{ color: '#666' }}>Created: </span>
                <span>{new Date(job.created_at).toLocaleString('vi-VN')}</span>
              </div>
              {job.assigned_at && (
                <div>
                  <span style={{ color: '#666' }}>Assigned: </span>
                  <span>{new Date(job.assigned_at).toLocaleString('vi-VN')}</span>
                </div>
              )}
              {job.upload_started_at && (
                <div>
                  <span style={{ color: '#666' }}>Upload started: </span>
                  <span>{new Date(job.upload_started_at).toLocaleString('vi-VN')}</span>
                </div>
              )}
              {job.upload_completed_at && (
                <div>
                  <span style={{ color: '#666' }}>Upload completed: </span>
                  <span>{new Date(job.upload_completed_at).toLocaleString('vi-VN')}</span>
                </div>
              )}
              {job.processing_started_at && (
                <div>
                  <span style={{ color: '#666' }}>Processing started: </span>
                  <span>{new Date(job.processing_started_at).toLocaleString('vi-VN')}</span>
                </div>
              )}
              {job.completed_at && (
                <div>
                  <span style={{ color: '#666' }}>Completed: </span>
                  <span>{new Date(job.completed_at).toLocaleString('vi-VN')}</span>
                </div>
              )}
            </div>
          </div>

          {job.status === 'DONE' && job.node_download_url && (
            <div className="card">
              <h2 style={{ marginBottom: '16px' }}>Download</h2>
              <a href={job.node_download_url} className="btn btn-primary" download>
                Tải video đã vietsub
              </a>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
