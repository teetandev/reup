'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Nav from '@/components/Nav';
import { StatusBadge, EmptyState, Skeleton } from '@/components/ui';
import { api, Job } from '@/lib/api';
import { STATUS_LABELS } from '@/lib/status';

const FILTERS = ['ALL', 'RUNNING', 'DONE', 'FAILED'] as const;
type Filter = (typeof FILTERS)[number];
const RUNNING = ['UPLOADING', 'UPLOADED', 'EXTRACTING_AUDIO', 'CHUNKING_AUDIO', 'TRANSCRIBING', 'TRANSLATING', 'GENERATING_SRT', 'RENDERING', 'WAITING_UPLOAD'];

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<Filter>('ALL');
  const router = useRouter();

  useEffect(() => {
    if (!localStorage.getItem('access_token')) {
      router.push('/login');
      return;
    }
    const load = () => api.listJobs().then(setJobs).catch(() => {}).finally(() => setLoading(false));
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [router]);

  const filtered = useMemo(() => {
    return jobs
      .filter((j) => {
        if (filter === 'DONE') return j.status === 'DONE';
        if (filter === 'FAILED') return j.status === 'FAILED';
        if (filter === 'RUNNING') return RUNNING.includes(j.status);
        return true;
      })
      .filter((j) => {
        const q = search.trim().toLowerCase();
        if (!q) return true;
        return (j.original_filename || '').toLowerCase().includes(q) || j.id.includes(q);
      })
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [jobs, filter, search]);

  return (
    <>
      <Nav />
      <div className="container">
        <div className="page-header">
          <div>
            <h1>Lịch sử jobs</h1>
            <div className="subtitle">{jobs.length} job tổng cộng.</div>
          </div>
          <Link href="/jobs/new" className="btn btn-primary">+ Upload video</Link>
        </div>

        <div className="card mb-16">
          <div className="flex gap-12 wrap">
            <input
              className="input"
              style={{ maxWidth: 320 }}
              placeholder="Tìm theo tên file hoặc job id…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <div className="flex gap-8">
              {FILTERS.map((f) => (
                <button
                  key={f}
                  className={`btn btn-sm ${filter === f ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setFilter(f)}
                >
                  {f === 'ALL' ? 'Tất cả' : f === 'RUNNING' ? 'Đang chạy' : f === 'DONE' ? 'Hoàn tất' : 'Lỗi'}
                </button>
              ))}
            </div>
          </div>
        </div>

        {loading ? (
          <div className="card">
            <Skeleton className="skeleton-line" style={{ width: '60%' }} />
            <Skeleton className="skeleton-line" style={{ width: '80%' }} />
          </div>
        ) : filtered.length === 0 ? (
          <div className="card">
            <EmptyState
              icon="🎞️"
              title="Không có job phù hợp"
              hint="Thử bỏ lọc, hoặc upload video mới."
              action={<Link href="/jobs/new" className="btn btn-primary">Upload video đầu tiên</Link>}
            />
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Tên file</th>
                  <th>Trạng thái</th>
                  <th>Tiến độ</th>
                  <th>Tạo lúc</th>
                  <th style={{ textAlign: 'right' }}></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((job) => (
                  <tr key={job.id}>
                    <td>
                      <Link href={`/jobs/${job.id}`}>{job.original_filename || job.id.slice(0, 8)}</Link>
                      <div className="text-faint text-sm text-mono">{job.id.slice(0, 8)}</div>
                    </td>
                    <td><StatusBadge status={job.status} label={STATUS_LABELS[job.status] || job.status} /></td>
                    <td className="text-sm">{Math.round(job.progress_percent)}%</td>
                    <td className="text-sm">{new Date(job.created_at).toLocaleString('vi-VN')}</td>
                    <td style={{ textAlign: 'right' }}>
                      <div className="flex gap-8" style={{ justifyContent: 'flex-end' }}>
                        <Link href={`/jobs/${job.id}`} className="btn btn-ghost btn-sm">Chi tiết</Link>
                        {job.status === 'DONE' && job.node_download_url && (
                          <a href={job.node_download_url} download className="btn btn-secondary btn-sm">
                            Tải
                          </a>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
