'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import AdminNav from '@/components/AdminNav';
import { api, Node } from '@/lib/api';

export default function AdminNodesPage() {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [loading, setLoading] = useState(true);
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [showTokenModal, setShowTokenModal] = useState(false);
  const [generatedToken, setGeneratedToken] = useState<string | null>(null);
  const [installCommand, setInstallCommand] = useState<string | null>(null);

  useEffect(() => {
    loadNodes();
  }, []);

  const loadNodes = () => {
    api.admin.listNodes()
      .then(setNodes)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  const handleRegisterNode = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const data = {
      name: (form.elements.namedItem('name') as HTMLInputElement).value,
      public_url: (form.elements.namedItem('public_url') as HTMLInputElement).value,
    };
    try {
      const result = await api.admin.registerNode(data);
      setGeneratedToken(result.node_token);
      setInstallCommand(result.install_command);
      setShowRegisterModal(false);
      setShowTokenModal(true);
      loadNodes();
    } catch (err) {
      alert('Lỗi đăng ký node');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'IDLE': return '#155724';
      case 'BUSY': return '#856404';
      case 'OFFLINE': return '#721c24';
      case 'DISABLED': return '#666';
      case 'ERROR': return '#d32f2f';
      default: return '#666';
    }
  };

  const formatHeartbeat = (timestamp: string | null) => {
    if (!timestamp) return 'Chưa có';
    const diff = Date.now() - new Date(timestamp).getTime();
    const seconds = Math.floor(diff / 1000);
    if (seconds < 60) return `${seconds}s trước`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m trước`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h trước`;
  };

  return (
    <>
      <AdminNav />
      <div className="container">
        <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1>Quản lý VPS Nodes</h1>
          <button className="btn btn-primary" onClick={() => setShowRegisterModal(true)}>
            + Đăng ký node
          </button>
        </div>

        {loading ? (
          <p>Đang tải...</p>
        ) : nodes.length === 0 ? (
          <div className="card">
            <p style={{ color: '#666' }}>Chưa có node nào. Hãy đăng ký node đầu tiên!</p>
          </div>
        ) : (
          <div className="card">
            <table>
              <thead>
                <tr>
                  <th>Tên</th>
                  <th>URL</th>
                  <th>Trạng thái</th>
                  <th>Job hiện tại</th>
                  <th>CPU / RAM</th>
                  <th>Disk free</th>
                  <th>Heartbeat</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {nodes.map((node) => (
                  <tr key={node.id}>
                    <td>
                      <Link href={`/admin/nodes/${node.id}`} style={{ color: '#0066cc', textDecoration: 'none' }}>
                        {node.name}
                      </Link>
                    </td>
                    <td style={{ fontSize: '12px', color: '#666' }}>{node.public_url}</td>
                    <td>
                      <span style={{ color: getStatusColor(node.status), fontWeight: '600', fontSize: '12px' }}>
                        {node.status}
                      </span>
                    </td>
                    <td style={{ fontSize: '12px' }}>
                      {node.current_job_id ? (
                        <Link href={`/admin/jobs/${node.current_job_id}`} style={{ color: '#0066cc' }}>
                          {node.current_job_id.substring(0, 8)}
                        </Link>
                      ) : '—'}
                    </td>
                    <td style={{ fontSize: '12px' }}>
                      {node.cpu_percent !== null && node.ram_used_mb !== null && node.ram_total_mb !== null
                        ? `${node.cpu_percent.toFixed(1)}% / ${node.ram_used_mb}/${node.ram_total_mb}MB`
                        : '—'}
                    </td>
                    <td style={{ fontSize: '12px' }}>
                      {node.disk_free_gb !== null ? `${node.disk_free_gb.toFixed(1)}GB` : '—'}
                    </td>
                    <td style={{ fontSize: '12px' }}>{formatHeartbeat(node.last_heartbeat_at)}</td>
                    <td>
                      <Link href={`/admin/nodes/${node.id}`} style={{ color: '#0066cc', fontSize: '12px' }}>
                        Chi tiết →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {showRegisterModal && (
          <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
          }}>
            <div className="card" style={{ width: '500px', maxWidth: '90%' }}>
              <h2 style={{ marginBottom: '16px' }}>Đăng ký VPS node mới</h2>
              <form onSubmit={handleRegisterNode}>
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '8px' }}>Tên node</label>
                  <input type="text" name="name" className="input" placeholder="node-1" required />
                </div>
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '8px' }}>Public URL</label>
                  <input type="url" name="public_url" className="input" placeholder="https://node-1.example.com" required />
                </div>
                <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                  <button type="button" className="btn btn-secondary" onClick={() => setShowRegisterModal(false)}>
                    Hủy
                  </button>
                  <button type="submit" className="btn btn-primary">
                    Đăng ký
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {showTokenModal && generatedToken && installCommand && (
          <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
          }}>
            <div className="card" style={{ width: '800px', maxWidth: '90%', maxHeight: '80vh', overflow: 'auto' }}>
              <h2 style={{ marginBottom: '16px', color: '#d32f2f' }}>⚠️ Node Token & Install Command (chỉ hiện một lần)</h2>
              <p style={{ marginBottom: '16px', color: '#666' }}>
                Sao chép lệnh install này và chạy trên VPS Ubuntu. Token sẽ không hiện lại.
              </p>
              <div style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px', marginBottom: '16px', wordBreak: 'break-all', fontFamily: 'monospace', fontSize: '12px' }}>
                {installCommand}
              </div>
              <button
                className="btn btn-primary"
                onClick={() => {
                  navigator.clipboard.writeText(installCommand);
                  alert('Đã sao chép lệnh cài đặt!');
                }}
                style={{ marginRight: '8px' }}
              >
                Sao chép lệnh
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => {
                  setShowTokenModal(false);
                  setGeneratedToken(null);
                  setInstallCommand(null);
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
