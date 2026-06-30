'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Nav from '@/components/Nav';
import { StatusBadge, Skeleton, formatBytes } from '@/components/ui';
import { api, Job } from '@/lib/api';
import { STATUS_LABELS, PROGRESS_MAP, PIPELINE_STEPS, TERMINAL_STATUSES } from '@/lib/status';

function Timeline({ job }: { job: Job }) {
  const failed = job.status === 'FAILED';
  const currentIdx = PIPELINE_STEPS.indexOf(job.status);
  // Map current_step (which is a status) onto the steps as well.
  const stepIdx = job.current_step ? PIPELINE_STEPS.indexOf(job.current_step) : -1;
  const activeIdx = Math.max(currentIdx, stepIdx);

  return (
    <div className="timeline">
      {PIPELINE_STEPS.map((step, i) => {
        let cls = '';
        if (job.status === 'DONE') cls = 'done';
        else if (i < activeIdx) cls = 'done';
        else if (i === activeIdx) cls = failed ? 'error' : 'current';

        const isLast = i === PIPELINE_STEPS.length - 1;
        const mark = cls === 'done' ? '✓' : cls === 'error' ? '!' : i + 1;
        return (
          <div key={step} className={`timeline-step ${cls}`}>
            <div className="timeline-marker">
              <div className="timeline-dot">{mark}</div>
              {!isLast && <div className="timeline-line" />}
            </div>
            <div className="timeline-content">
              <div className="step-name">{STATUS_LABELS[step] || step}</div>
              {i === activeIdx && !failed && job.status !== 'DONE' && (
                <div className="step-hint">Đang xử lý…</div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

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
    let interval: ReturnType<typeof setInterval> | null = null;
    const fetchJob = () => {
      api.getJob(jobId)
        .then((data) => {
          setJob(data);
          setLoading(false);
          if (TERMINAL_STATUSES.includes(data.status) && interval) {
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
          <div className="card">
            <Skeleton className="skeleton-line" style={{ width: '50%' }} />
            <Skeleton className="skeleton-line" style={{ width: '80%' }} />
            <Skeleton className="skeleton-line" style={{ width: '65%' }} />
          </div>
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
            <div className="alert alert-error">{error || 'Không tìm thấy job'}</div>
          </div>
        </div>
      </>
    );
  }

  const progressPercent = Math.round(job.progress_percent || PROGRESS_MAP[job.status] || 0);
  const downloadUrl = job.node_download_url;

  return (
    <>
      <Nav />
      <div className="container">
        <div className="page-header">
          <div>
            <h1 style={{ overflowWrap: 'anywhere' }}>{job.original_filename || 'Job'}</h1>
            <div className="subtitle text-mono">{job.id}</div>
          </div>
          <StatusBadge status={job.status} label={STATUS_LABELS[job.status] || job.status} />
        </div>

        <div className="grid grid-2">
          <div className="card">
            <div className="card-title">Tiến trình</div>
            <div className="flex-between mb-8">
              <span className="text-sm text-soft">
                {job.current_step ? STATUS_LABELS[job.current_step] || job.current_step : '—'}
              </span>
              <span style={{ fontWeight: 700 }}>{progressPercent}%</span>
            </div>
            <div className="progress-bar mb-16">
              <div className="progress-fill" style={{ width: `${progressPercent}%` }} />
            </div>

            {job.error_message && (
              <div className="alert alert-error mb-16">
                <span>⚠️</span>
                <span>
                  {job.error_code && <b>[{job.error_code}] </b>}
                  {job.error_message}
                </span>
              </div>
            )}

            {job.status === 'DONE' && downloadUrl && (
              <>
                <a href={downloadUrl} download className="btn btn-primary btn-block">
                  ⬇ Tải xuống video
                </a>
                <div className="text-faint text-sm mt-8">
                  Lưu ý: sau khi tải xuống, file output trên worker sẽ được dọn để tiết kiệm ổ đĩa.
                </div>
              </>
            )}

            <div className="grid grid-2 mt-24">
              <div>
                <div className="text-faint text-sm">Kích thước</div>
                <div style={{ fontWeight: 600 }}>{formatBytes(job.file_size_bytes)}</div>
              </div>
              <div>
                <div className="text-faint text-sm">Độ phân giải</div>
                <div style={{ fontWeight: 600 }}>{job.resolution || '—'}</div>
              </div>
              <div>
                <div className="text-faint text-sm">Thời lượng</div>
                <div style={{ fontWeight: 600 }}>
                  {job.duration_seconds ? `${Math.round(job.duration_seconds)}s` : '—'}
                </div>
              </div>
              <div>
                <div className="text-faint text-sm">Tạo lúc</div>
                <div style={{ fontWeight: 600 }}>{new Date(job.created_at).toLocaleString('vi-VN')}</div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-title">Các bước xử lý</div>
            <Timeline job={job} />
          </div>
        </div>

        <div className="mt-24">
          <button onClick={() => router.push('/jobs')} className="btn btn-secondary">
            ← Lịch sử jobs
          </button>
        </div>
      </div>
    </>
  );
}
