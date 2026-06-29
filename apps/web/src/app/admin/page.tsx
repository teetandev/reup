'use client';

import { useEffect, useState } from 'react';
import AdminNav from '@/components/AdminNav';
import { api, DashboardStats } from '@/lib/api';

export default function AdminDashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.admin.getStats()
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

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

  return (
    <>
      <AdminNav />
      <div className="container">
        <h1 style={{ marginBottom: '24px' }}>Tổng quan</h1>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
          <div className="card">
            <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>Tổng người dùng</div>
            <div style={{ fontSize: '32px', fontWeight: '700', color: '#0066cc' }}>{stats?.total_users || 0}</div>
          </div>
          <div className="card">
            <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>Jobs đang chạy</div>
            <div style={{ fontSize: '32px', fontWeight: '700', color: '#0c5460' }}>{stats?.active_jobs || 0}</div>
          </div>
          <div className="card">
            <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>Nodes rảnh</div>
            <div style={{ fontSize: '32px', fontWeight: '700', color: '#155724' }}>{stats?.idle_nodes || 0}</div>
          </div>
          <div className="card">
            <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>Nodes đang bận</div>
            <div style={{ fontSize: '32px', fontWeight: '700', color: '#856404' }}>{stats?.busy_nodes || 0}</div>
          </div>
          <div className="card">
            <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>Nodes offline</div>
            <div style={{ fontSize: '32px', fontWeight: '700', color: '#721c24' }}>{stats?.offline_nodes || 0}</div>
          </div>
          <div className="card">
            <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>Jobs lỗi hôm nay</div>
            <div style={{ fontSize: '32px', fontWeight: '700', color: '#d32f2f' }}>{stats?.failed_jobs_today || 0}</div>
          </div>
        </div>
      </div>
    </>
  );
}
