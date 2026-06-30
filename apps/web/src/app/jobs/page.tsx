'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Nav from '@/components/Nav';
import { api, Job } from '@/lib/api';
import { STATUS_LABELS } from '@/lib/status';

export default function JobsPage() {
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
        setJobs(data);
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
          <h1>Lịch sử Jobs</h1>
          <Link href="/jobs/new" className="btn btn-primary">
            + Upload Video Mới
          </Link>
        </div>

        <div className="card">
          {loading ? (
            <p>Đang tải...</p>
          ) : jobs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <p style={{ color: '#666', marginBottom: '16px' }}>Chưa có job nào</p>
              <Link href="/jobs/new" className="btn btn-primary">
                Upload video đầu tiên
              </Link>
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Tên file</th>
                  <th>Trạng thái</th>
                  <th>Tiến độ</th>
                  <th>Thời gian tạo</th>
                  <th>Hoàn thành</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id}>
                    <td style={{ fontSize: '12px', fontFamily: 'monospace', color: '#666' }}>
                      {job.id.slice(0, 8)}
                    </td>
                    <td>{job.original_filename}</td>
                    <td>
                      <span className={`status-badge ${getStatusClass(job.status)}`}>
                        {STATUS_LABELS[job.status] || job.status}
                      </span>
                    </td>
                    <td>{Math.round(job.progress_percent)}%</td>
                    <td>{new Date(job.created_at).toLocaleString('vi-VN')}</td>
                    <td>
                      {job.completed_at
                        ? new Date(job.completed_at).toLocaleString('vi-VN')
                        : '-'}
                    </td>
                    <td>
                      <Link href={`/jobs/${job.id}`} style={{ color: '#0066cc', textDecoration: 'none' }}>
                        Chi tiết
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
}
