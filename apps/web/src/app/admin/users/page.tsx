'use client';

import { useEffect, useState } from 'react';
import AdminNav from '@/components/AdminNav';
import { api, User, ApiKey } from '@/lib/api';

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = () => {
    api.admin.listUsers()
      .then(setUsers)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  const handleCreateUser = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const data = {
      display_name: (form.elements.namedItem('display_name') as HTMLInputElement).value,
      daily_job_limit: parseInt((form.elements.namedItem('daily_job_limit') as HTMLInputElement).value),
      max_file_mb: parseInt((form.elements.namedItem('max_file_mb') as HTMLInputElement).value),
    };
    try {
      await api.admin.createUser(data);
      setShowCreateModal(false);
      loadUsers();
    } catch (err) {
      alert('Lỗi tạo user');
    }
  };

  const handleIssueKey = async (userId: string) => {
    try {
      const result = await api.admin.issueKey(userId, 'Main key');
      setGeneratedKey(result.secret_key);
      setShowKeyModal(true);
      setSelectedUserId(null);
    } catch (err) {
      alert('Lỗi tạo key');
    }
  };

  return (
    <>
      <AdminNav />
      <div className="container">
        <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1>Quản lý người dùng</h1>
          <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
            + Tạo người dùng
          </button>
        </div>

        {loading ? (
          <p>Đang tải...</p>
        ) : (
          <div className="card">
            <table>
              <thead>
                <tr>
                  <th>Tên</th>
                  <th>Role</th>
                  <th>Trạng thái</th>
                  <th>Max file (MB)</th>
                  <th>Jobs/ngày</th>
                  <th>Hành động</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>{user.display_name}</td>
                    <td><span className="status-badge">{user.role}</span></td>
                    <td>
                      <span className={`status-badge ${user.status === 'ACTIVE' ? 'status-done' : 'status-failed'}`}>
                        {user.status === 'ACTIVE' ? 'Hoạt động' : 'Bị khóa'}
                      </span>
                    </td>
                    <td>{user.max_file_mb}</td>
                    <td>{user.daily_job_limit}</td>
                    <td>
                      <button
                        className="btn btn-primary"
                        style={{ padding: '6px 12px', fontSize: '12px' }}
                        onClick={() => handleIssueKey(user.id)}
                      >
                        Tạo key
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {showCreateModal && (
          <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
          }}>
            <div className="card" style={{ width: '500px', maxWidth: '90%' }}>
              <h2 style={{ marginBottom: '16px' }}>Tạo người dùng mới</h2>
              <form onSubmit={handleCreateUser}>
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '8px' }}>Tên hiển thị</label>
                  <input type="text" name="display_name" className="input" required />
                </div>
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '8px' }}>Giới hạn jobs/ngày</label>
                  <input type="number" name="daily_job_limit" className="input" defaultValue="10" required />
                </div>
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '8px' }}>Max file size (MB)</label>
                  <input type="number" name="max_file_mb" className="input" defaultValue="500" required />
                </div>
                <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                  <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>
                    Hủy
                  </button>
                  <button type="submit" className="btn btn-primary">
                    Tạo
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {showKeyModal && generatedKey && (
          <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
          }}>
            <div className="card" style={{ width: '600px', maxWidth: '90%' }}>
              <h2 style={{ marginBottom: '16px', color: '#d32f2f' }}>⚠️ Secret Key (chỉ hiện một lần)</h2>
              <p style={{ marginBottom: '16px', color: '#666' }}>
                Sao chép key này ngay. Bạn sẽ không thể xem lại.
              </p>
              <div style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px', marginBottom: '16px', wordBreak: 'break-all', fontFamily: 'monospace' }}>
                {generatedKey}
              </div>
              <button
                className="btn btn-primary"
                onClick={() => {
                  navigator.clipboard.writeText(generatedKey);
                  alert('Đã sao chép!');
                }}
                style={{ marginRight: '8px' }}
              >
                Sao chép
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => {
                  setShowKeyModal(false);
                  setGeneratedKey(null);
                }}
              >
                Đóng
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
