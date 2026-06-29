'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Nav from '@/components/Nav';
import { api, Job } from '@/lib/api';
import { STATUS_LABELS } from '@/lib/status';

export default function DashboardPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    api.listJobs()
      .then((data) => {
        setJobs(data.slice(0, 5));
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  }, [router]);

  const getStatusClass = (status: string) => {
    if (status === 'DONE') return 'status-done';
    if (status === 'FAILED') return 'status-failed';
    if (['EXTRACTING_AUDIO', 'TRANSCRIBING', 'TRANSLATING', 'RENDERING'].includes(status)) {
      return 'status-processing';
    }
    return 'status-waiting';
  };

  return (
    <>
      <Nav />
      <div className="container">
        <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1>Dashboard</h1>
          <Link href="/jobs/new" className="btn btn-primary">
            + Upload Video Mới
          </Link>
        </div>

        <div className="card">
          <h2 style={{ marginBottom: '16px' }}>Jobs gần đây</h2>
          {loading ? (
            <p>Đang tải...</p>
          ) : jobs.length === 0 ? (
            <p style={{ color: '#666' }}>Chưa có job nào. Hãy upload video đầu tiên!</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Tên file</th>
                  <th>Trạng thái</th>
                  <th>Tiến độ</th>
                  <th>Thời gian</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id}>
                    <td>{job.original_filename}</td>
                    <td>
                      <span className={`status-badge ${getStatusClass(job.status)}`}>
                        {STATUS_LABELS[job.status] || job.status}
                      </span>
                    </td>
                    <td>{Math.round(job.progress_percent)}%</td>
                    <td>{new Date(job.created_at).toLocaleString('vi-VN')}</td>
                    <td>
                      <Link href={`/jobs/${job.id}`} style={{ color: '#0066cc', textDecoration: 'none' }}>
                        Xem
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {jobs.length > 0 && (
            <div style={{ marginTop: '16px', textAlign: 'center' }}>
              <Link href="/jobs" style={{ color: '#0066cc', textDecoration: 'none' }}>
                Xem tất cả →
              </Link>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
