'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import AdminNav from '@/components/AdminNav';
import { StatusBadge, SkeletonStats, Skeleton, timeAgo } from '@/components/ui';
import { api, DashboardStats, Node, Job } from '@/lib/api';
import { STATUS_LABELS } from '@/lib/status';

export default function AdminDashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [nodes, setNodes] = useState<Node[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = () =>
      Promise.all([
        api.admin.getStats().catch(() => null),
        api.admin.listNodes().catch(() => []),
        api.admin.listAllJobs().catch(() => []),
      ]).then(([s, n, j]) => {
        if (s) setStats(s);
        setNodes(n);
        setJobs(j);
        setLoading(false);
      });
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, []);

  const doneJobs = jobs.filter((j) => j.status === 'DONE').length;
  const failedJobs = jobs.filter((j) => j.status === 'FAILED').length;
  const onlineNodes = nodes.filter((n) => !timeAgo(n.last_heartbeat_at).stale && n.enabled).length;
  const recent = jobs.slice(0, 6);

  return (
    <>
      <AdminNav />
      <div className="container">
        <div className="page-header">
          <div>
            <h1>Tổng quan</h1>
            <div className="subtitle">Theo dõi jobs &amp; worker nodes theo thời gian thực.</div>
          </div>
          <Link href="/jobs/new" className="btn btn-primary">+ Upload video</Link>
        </div>

        {loading ? (
          <SkeletonStats count={4} />
        ) : (
          <>
            <div className="grid grid-4">
              <div className="stat accent-blue">
                <div className="stat-label">Jobs đang chạy</div>
                <div className="stat-value">{stats?.active_jobs ?? 0}</div>
              </div>
              <div className="stat accent-green">
                <div className="stat-label">Jobs hoàn tất</div>
                <div className="stat-value">{doneJobs}</div>
              </div>
              <div className="stat accent-red">
                <div className="stat-label">Jobs lỗi</div>
                <div className="stat-value">{failedJobs}</div>
                <div className="stat-hint">{stats?.failed_jobs_today ?? 0} hôm nay</div>
              </div>
              <div className="stat">
                <div className="stat-label">Tổng người dùng</div>
                <div className="stat-value">{stats?.total_users ?? 0}</div>
              </div>
            </div>

            <div className="grid grid-3 mt-24">
              <div className="stat accent-green">
                <div className="stat-label">Nodes online</div>
                <div className="stat-value">{onlineNodes}</div>
              </div>
              <div className="stat accent-blue">
                <div className="stat-label">Nodes đang bận</div>
                <div className="stat-value">{stats?.busy_nodes ?? 0}</div>
              </div>
              <div className="stat">
                <div className="stat-label">Nodes offline / stale</div>
                <div className="stat-value">{stats?.offline_nodes ?? 0}</div>
              </div>
            </div>

            <div className="grid grid-2 mt-24">
              <div className="card">
                <div className="flex-between mb-16">
                  <div className="card-title" style={{ marginBottom: 0 }}>Jobs gần đây</div>
                  <Link href="/admin/jobs" className="text-sm">Xem tất cả →</Link>
                </div>
                {recent.length === 0 ? (
                  <div className="text-soft text-sm">Chưa có job nào.</div>
                ) : (
                  recent.map((j) => (
                    <Link
                      key={j.id}
                      href={`/admin/jobs/${j.id}`}
                      className="flex-between"
                      style={{ padding: '10px 0', borderBottom: '1px solid var(--border)', textDecoration: 'none', color: 'inherit' }}
                    >
                      <div style={{ overflow: 'hidden' }}>
                        <div style={{ fontWeight: 600, fontSize: 14, whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                          {j.original_filename || j.id.substring(0, 8)}
                        </div>
                        <div className="text-faint text-sm">{new Date(j.created_at).toLocaleString('vi-VN')}</div>
                      </div>
                      <StatusBadge status={j.status} label={STATUS_LABELS[j.status] || j.status} />
                    </Link>
                  ))
                )}
              </div>

              <div className="card">
                <div className="flex-between mb-16">
                  <div className="card-title" style={{ marginBottom: 0 }}>Node health</div>
                  <Link href="/admin/nodes" className="text-sm">Quản lý →</Link>
                </div>
                {nodes.length === 0 ? (
                  <div className="text-soft text-sm">Chưa có node nào.</div>
                ) : (
                  nodes.slice(0, 6).map((n) => {
                    const hb = timeAgo(n.last_heartbeat_at);
                    return (
                      <div
                        key={n.id}
                        className="flex-between"
                        style={{ padding: '10px 0', borderBottom: '1px solid var(--border)' }}
                      >
                        <div>
                          <div style={{ fontWeight: 600, fontSize: 14 }}>{n.name}</div>
                          <div className="text-faint text-sm" style={{ color: hb.stale ? 'var(--red)' : undefined }}>
                            {hb.text}
                          </div>
                        </div>
                        <StatusBadge status={n.status} />
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}
