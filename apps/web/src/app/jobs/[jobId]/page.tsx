'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Nav from '@/components/Nav';
import { api, Job } from '@/lib/api';
import { STATUS_LABELS, PROGRESS_MAP } from '@/lib/status';

export default function JobDetailPage() {
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const params = useParams();
  const router = useRouter();
  const jobId = params.jobId as string;

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    const TERMINAL = ['DONE', 'FAILED', 'CANCELLED', 'EXPIRED'];
    let interval: ReturnType<typeof setInterval> | null = null;

    const fetchJob = () => {
      api.getJob(jobId)
        .then((data) => {
          setJob(data);
          setLoading(false);
          // Stop polling once the job reaches a terminal state.
          if (TERMINAL.includes(data.status) && interval) {
            clearInterval(interval);
            interval = null;
          }
        })
        .catch(() => {
          setError('Không tìm thấy job');
          setLoading(false);
        });
    };

    fetchJob();
    interval = setInterval(fetchJob, 3000);
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [jobId, router]);

  if (loading) {
    return (
      <>
        <Nav />
        <div className="container">
          <p>Đang tải...</p>
        </div>
      </>
    );
  }

  if (error || !job) {
    return (
      <>
        <Nav />
        <div className="container">
          <div className="card">
            <p className="error">{error || 'Không tìm thấy job'}</p>
          </div>
        </div>
      </>
    );
  }

  const getStatusClass = (status: string) => {
    if (status === 'DONE') return 'status-done';
    if (status === 'FAILED') return 'status-failed';
    if (['EXTRACTING_AUDIO', 'TRANSCRIBING', 'TRANSLATING', 'RENDERING'].includes(status)) {
      return 'status-processing';
    }
    return 'status-waiting';
  };

  const progressPercent = Math.round(job.progress_percent || PROGRESS_MAP[job.status] || 0);
  const downloadUrl = job.node_download_url;

  return (
    <>
      <Nav />
      <div className="container">
        <h1 style={{ marginBottom: '24px' }}>Chi tiết Job</h1>

        <div className="card">
          <div style={{ marginBottom: '24px' }}>
            <h2 style={{ marginBottom: '8px' }}>{job.original_filename}</h2>
            <div style={{ fontSize: '14px', color: '#666' }}>
              Job ID: {job.id}
            </div>
          </div>

          <div style={{ marginBottom: '24px' }}>
            <div style={{ marginBottom: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className={`status-badge ${getStatusClass(job.status)}`}>
                {STATUS_LABELS[job.status] || job.status}
              </span>
              <span style={{ fontSize: '14px', fontWeight: '600' }}>{progressPercent}%</span>
            </div>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${progressPercent}%` }} />
            </div>
            {job.current_step && (
              <div style={{ marginTop: '8px', fontSize: '14px', color: '#666' }}>
                Bước hiện tại: {STATUS_LABELS[job.current_step] || job.current_step}
              </div>
            )}
          </div>

          {job.error_message && (
            <div style={{ marginBottom: '24px', padding: '16px', background: '#f8d7da', borderRadius: '4px' }}>
              <div style={{ fontWeight: '600', color: '#721c24', marginBottom: '4px' }}>Lỗi:</div>
              <div style={{ color: '#721c24', fontSize: '14px' }}>{job.error_message}</div>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
            <div>
              <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>Kích thước</div>
              <div style={{ fontSize: '14px', fontWeight: '500' }}>
                {job.file_size_bytes ? (job.file_size_bytes / (1024 * 1024)).toFixed(2) + ' MB' : '-'}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>Thời gian tạo</div>
              <div style={{ fontSize: '14px', fontWeight: '500' }}>
                {new Date(job.created_at).toLocaleString('vi-VN')}
              </div>
            </div>
            {job.processing_started_at && (
              <div>
                <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>Bắt đầu xử lý</div>
                <div style={{ fontSize: '14px', fontWeight: '500' }}>
                  {new Date(job.processing_started_at).toLocaleString('vi-VN')}
                </div>
              </div>
            )}
            {job.completed_at && (
              <div>
                <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>Hoàn thành</div>
                <div style={{ fontSize: '14px', fontWeight: '500' }}>
                  {new Date(job.completed_at).toLocaleString('vi-VN')}
                </div>
              </div>
            )}
          </div>

          {job.status === 'DONE' && downloadUrl && (
            <a
              href={downloadUrl}
              download
              className="btn btn-primary"
              style={{ display: 'inline-block', textDecoration: 'none' }}
            >
              ⬇ Tải xuống video
            </a>
          )}

          <div style={{ marginTop: '24px' }}>
            <button
              onClick={() => router.push('/dashboard')}
              className="btn btn-secondary"
            >
              ← Quay lại Dashboard
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
