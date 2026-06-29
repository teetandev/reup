'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import AdminNav from '@/components/AdminNav';
import { api, Node } from '@/lib/api';

export default function NodeDetailPage() {
  const params = useParams();
  const nodeId = params.nodeId as string;
  const [node, setNode] = useState<Node | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (nodeId) {
      api.admin.getNode(nodeId)
        .then(setNode)
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [nodeId]);

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

  if (!node) {
    return (
      <>
        <AdminNav />
        <div className="container">
          <p>Không tìm thấy node.</p>
        </div>
      </>
    );
  }

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

  return (
    <>
      <AdminNav />
      <div className="container">
        <h1 style={{ marginBottom: '24px' }}>{node.name}</h1>

        <div style={{ display: 'grid', gap: '16px', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))' }}>
          <div className="card">
            <h2 style={{ marginBottom: '16px' }}>Thông tin cơ bản</h2>
            <div style={{ display: 'grid', gap: '8px' }}>
              <div>
                <span style={{ color: '#666' }}>ID: </span>
                <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>{node.id}</span>
              </div>
              <div>
                <span style={{ color: '#666' }}>Public URL: </span>
                <a href={node.public_url} target="_blank" rel="noopener noreferrer" style={{ color: '#0066cc' }}>
                  {node.public_url}
                </a>
              </div>
              <div>
                <span style={{ color: '#666' }}>Trạng thái: </span>
                <span style={{ color: getStatusColor(node.status), fontWeight: '600' }}>{node.status}</span>
              </div>
              <div>
                <span style={{ color: '#666' }}>Enabled: </span>
                <span>{node.enabled ? '✅ Yes' : '❌ No'}</span>
              </div>
              <div>
                <span style={{ color: '#666' }}>Agent version: </span>
                <span>{node.agent_version || '—'}</span>
              </div>
              <div>
                <span style={{ color: '#666' }}>Token prefix: </span>
                <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>{node.node_token_prefix || '—'}</span>
              </div>
            </div>
          </div>

          <div className="card">
            <h2 style={{ marginBottom: '16px' }}>Tài nguyên</h2>
            <div style={{ display: 'grid', gap: '8px' }}>
              <div>
                <span style={{ color: '#666' }}>CPU: </span>
                <span>{node.cpu_percent !== null ? `${node.cpu_percent.toFixed(1)}%` : '—'}</span>
              </div>
              <div>
                <span style={{ color: '#666' }}>RAM used: </span>
                <span>{node.ram_used_mb !== null ? `${node.ram_used_mb} MB` : '—'}</span>
              </div>
              <div>
                <span style={{ color: '#666' }}>RAM total: </span>
                <span>{node.ram_total_mb !== null ? `${node.ram_total_mb} MB` : '—'}</span>
              </div>
              <div>
                <span style={{ color: '#666' }}>Disk free: </span>
                <span>{node.disk_free_gb !== null ? `${node.disk_free_gb.toFixed(1)} GB` : '—'}</span>
              </div>
              <div>
                <span style={{ color: '#666' }}>Max jobs: </span>
                <span>{node.max_jobs}</span>
              </div>
              <div>
                <span style={{ color: '#666' }}>Current job: </span>
                <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                  {node.current_job_id || '—'}
                </span>
              </div>
            </div>
          </div>

          <div className="card">
            <h2 style={{ marginBottom: '16px' }}>Heartbeat</h2>
            <div style={{ display: 'grid', gap: '8px' }}>
              <div>
                <span style={{ color: '#666' }}>Last heartbeat: </span>
                <span>
                  {node.last_heartbeat_at
                    ? new Date(node.last_heartbeat_at).toLocaleString('vi-VN')
                    : 'Chưa có'}
                </span>
              </div>
              <div>
                <span style={{ color: '#666' }}>Created at: </span>
                <span>{new Date(node.created_at).toLocaleString('vi-VN')}</span>
              </div>
              <div>
                <span style={{ color: '#666' }}>Updated at: </span>
                <span>{new Date(node.updated_at).toLocaleString('vi-VN')}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="card" style={{ marginTop: '16px' }}>
          <h2 style={{ marginBottom: '16px' }}>Install command</h2>
          <p style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>
            Lệnh cài đặt đã được tạo khi đăng ký node. Token không thể xem lại.
          </p>
          <div style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px', fontFamily: 'monospace', fontSize: '12px' }}>
            curl -fsSL {process.env.NEXT_PUBLIC_CONTROL_API_URL}/install-node.sh | bash -s -- \<br/>
            &nbsp;&nbsp;--node-id {node.id} \<br/>
            &nbsp;&nbsp;--node-token [TOKEN_HIDDEN] \<br/>
            &nbsp;&nbsp;--control-api-url {process.env.NEXT_PUBLIC_CONTROL_API_URL} \<br/>
            &nbsp;&nbsp;--public-url {node.public_url}
          </div>
        </div>
      </div>
    </>
  );
}
