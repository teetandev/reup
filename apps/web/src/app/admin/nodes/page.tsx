'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import AdminNav from '@/components/AdminNav';
import {
  StatusBadge,
  Modal,
  ConfirmModal,
  CopyButton,
  EmptyState,
  Skeleton,
  useToast,
  timeAgo,
} from '@/components/ui';
import { api, Node, RegisterNodeResponse, RotateNodeTokenResponse } from '@/lib/api';

const SETUP_COMMAND = 'bash scripts/setup-codespace-worker.sh';

function envBlock(nodeId: string, token: string): string {
  return [
    `NODE_ID=${nodeId}`,
    `NODE_TOKEN=${token}`,
    `CONTROL_API_URL=https://reup-control-api.onrender.com`,
    `MOCK_AI=false`,
    `GROQ_MODEL=whisper-large-v3`,
    `GEMINI_MODEL=gemini-2.5-flash`,
    `OUTPUT_TTL_HOURS=6`,
    `PORT=8100`,
  ].join('\n');
}

type ConfirmAction =
  | { kind: 'disable'; node: Node }
  | { kind: 'enable'; node: Node }
  | { kind: 'rotate'; node: Node }
  | { kind: 'delete'; node: Node; force: boolean }
  | null;

export default function AdminNodesPage() {
  const toast = useToast();
  const [nodes, setNodes] = useState<Node[]>([]);
  const [loading, setLoading] = useState(true);
  const [showRegister, setShowRegister] = useState(false);
  const [credentials, setCredentials] = useState<{ nodeId: string; token: string; name: string } | null>(null);
  const [confirm, setConfirm] = useState<ConfirmAction>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const loadNodes = useCallback(() => {
    api.admin
      .listNodes()
      .then(setNodes)
      .catch(() => toast('Không tải được danh sách node', 'error'))
      .finally(() => setLoading(false));
  }, [toast]);

  useEffect(() => {
    loadNodes();
    const t = setInterval(loadNodes, 10000); // smooth polling
    return () => clearInterval(t);
  }, [loadNodes]);

  const handleRegister = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const data = {
      name: (form.elements.namedItem('name') as HTMLInputElement).value,
      public_url: (form.elements.namedItem('public_url') as HTMLInputElement).value,
    };
    try {
      const res: RegisterNodeResponse = await api.admin.registerNode(data);
      setShowRegister(false);
      setCredentials({ nodeId: res.id, token: res.node_token, name: res.name });
      toast('Đã tạo node agent', 'success');
      loadNodes();
    } catch {
      toast('Lỗi đăng ký node', 'error');
    }
  };

  const runAction = async () => {
    if (!confirm) return;
    setActionLoading(true);
    try {
      if (confirm.kind === 'disable') {
        await api.admin.disableNode(confirm.node.id);
        toast('Đã disable node', 'success');
      } else if (confirm.kind === 'enable') {
        await api.admin.enableNode(confirm.node.id);
        toast('Đã enable node', 'success');
      } else if (confirm.kind === 'delete') {
        await api.admin.deleteNode(confirm.node.id, confirm.force);
        toast('Đã xóa node', 'success');
      } else if (confirm.kind === 'rotate') {
        const res: RotateNodeTokenResponse = await api.admin.rotateNodeToken(confirm.node.id);
        setCredentials({ nodeId: res.id, token: res.node_token, name: res.name });
        toast('Đã rotate token. Token cũ đã vô hiệu.', 'success');
      }
      setConfirm(null);
      loadNodes();
    } catch (err: any) {
      // If a delete failed because the node is BUSY, keep the modal open and
      // flip it into "force" mode so the admin can confirm the forced delete.
      if (confirm.kind === 'delete' && err?.code === 'NODE_BUSY') {
        setConfirm({ ...confirm, force: true });
        toast('Node đang BUSY — tích "Force delete" để xóa.', 'error');
      } else {
        toast(err?.message || 'Hành động thất bại', 'error');
      }
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <>
      <AdminNav />
      <div className="container">
        <div className="page-header">
          <div>
            <h1>VPS Nodes</h1>
            <div className="subtitle">Quản lý worker agent — tạo, disable, rotate token, xóa.</div>
          </div>
          <button className="btn btn-primary" onClick={() => setShowRegister(true)}>
            + Tạo node agent
          </button>
        </div>

        {loading ? (
          <div className="card">
            <Skeleton className="skeleton-line" style={{ width: '40%' }} />
            <Skeleton className="skeleton-line" style={{ width: '70%' }} />
            <Skeleton className="skeleton-line" style={{ width: '55%' }} />
          </div>
        ) : nodes.length === 0 ? (
          <div className="card">
            <EmptyState
              icon="🖥️"
              title="Chưa có node nào"
              hint="Tạo node agent đầu tiên rồi chạy script setup trong Codespace."
              action={
                <button className="btn btn-primary" onClick={() => setShowRegister(true)}>
                  + Tạo node agent
                </button>
              }
            />
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Tên</th>
                  <th>Trạng thái</th>
                  <th>Public URL</th>
                  <th>Job</th>
                  <th>CPU / RAM</th>
                  <th>Disk</th>
                  <th>Heartbeat</th>
                  <th style={{ textAlign: 'right' }}>Hành động</th>
                </tr>
              </thead>
              <tbody>
                {nodes.map((node) => {
                  const hb = timeAgo(node.last_heartbeat_at);
                  return (
                    <tr key={node.id}>
                      <td>
                        <Link href={`/admin/nodes/${node.id}`}>{node.name}</Link>
                        <div className="text-faint text-sm text-mono">{node.id.substring(0, 8)}</div>
                      </td>
                      <td><StatusBadge status={node.status} /></td>
                      <td>
                        <a href={node.public_url} target="_blank" rel="noreferrer" className="text-sm">
                          {node.public_url.replace(/^https?:\/\//, '')}
                        </a>
                      </td>
                      <td className="text-sm">
                        {node.current_job_id ? (
                          <Link href={`/admin/jobs/${node.current_job_id}`}>
                            {node.current_job_id.substring(0, 8)}
                          </Link>
                        ) : (
                          <span className="text-faint">—</span>
                        )}
                      </td>
                      <td className="text-sm">
                        {node.cpu_percent != null && node.ram_used_mb != null && node.ram_total_mb != null
                          ? `${node.cpu_percent.toFixed(0)}% · ${node.ram_used_mb}/${node.ram_total_mb}MB`
                          : '—'}
                      </td>
                      <td className="text-sm">
                        {node.disk_free_gb != null ? `${node.disk_free_gb.toFixed(1)}GB` : '—'}
                      </td>
                      <td className="text-sm">
                        <span style={{ color: hb.stale ? 'var(--red)' : 'var(--text-soft)' }}>
                          {hb.text}
                        </span>
                      </td>
                      <td>
                        <div className="flex gap-8 wrap" style={{ justifyContent: 'flex-end' }}>
                          <CopyButton value={node.id} label="ID" copiedLabel="✓" className="btn btn-ghost btn-sm" />
                          {node.enabled ? (
                            <button className="btn btn-ghost btn-sm" onClick={() => setConfirm({ kind: 'disable', node })}>
                              Disable
                            </button>
                          ) : (
                            <button className="btn btn-ghost btn-sm" onClick={() => setConfirm({ kind: 'enable', node })}>
                              Enable
                            </button>
                          )}
                          <button className="btn btn-ghost btn-sm" onClick={() => setConfirm({ kind: 'rotate', node })}>
                            Rotate
                          </button>
                          <button
                            className="btn btn-ghost btn-sm"
                            style={{ color: 'var(--red)' }}
                            onClick={() => setConfirm({ kind: 'delete', node, force: false })}
                          >
                            Xóa
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Register modal */}
      {showRegister && (
        <Modal title="Tạo node agent mới" onClose={() => setShowRegister(false)}>
          <form onSubmit={handleRegister}>
            <div className="field">
              <label>Tên node</label>
              <input type="text" name="name" className="input" placeholder="codespace-worker-1" required />
            </div>
            <div className="field">
              <label>Public URL</label>
              <input
                type="url"
                name="public_url"
                className="input"
                placeholder="https://xxxxx-8100.app.github.dev"
                required
              />
              <div className="text-faint text-sm mt-8">
                Với Codespace: dùng URL forward port 8100 (HTTP, Public).
              </div>
            </div>
            <div className="modal-actions">
              <button type="button" className="btn btn-secondary" onClick={() => setShowRegister(false)}>
                Hủy
              </button>
              <button type="submit" className="btn btn-primary">Tạo node</button>
            </div>
          </form>
        </Modal>
      )}

      {/* Credentials (token shown once) */}
      {credentials && (
        <Modal title="🔑 Node credentials (chỉ hiện một lần)" width={620} onClose={() => setCredentials(null)}>
          <div className="alert alert-warn mb-16">
            <span>⚠️</span>
            <span>
              <b>Token chỉ hiện một lần.</b> Nếu mất token, hãy dùng nút <b>Rotate</b> để tạo token mới.
            </span>
          </div>

          <div className="field">
            <label>NODE_ID</label>
            <div className="token-row">
              <span className="token-val">{credentials.nodeId}</span>
              <CopyButton value={credentials.nodeId} />
            </div>
          </div>

          <div className="field">
            <label>NODE_TOKEN</label>
            <div className="token-row">
              <span className="token-val">{credentials.token}</span>
              <CopyButton value={credentials.token} />
            </div>
          </div>

          <div className="field">
            <label>Copy nguyên block .env</label>
            <div className="code-block">{envBlock(credentials.nodeId, credentials.token)}</div>
            <div className="mt-8">
              <CopyButton value={envBlock(credentials.nodeId, credentials.token)} label="Copy .env" />
            </div>
          </div>

          <div className="field">
            <label>Lệnh setup trong Codespace</label>
            <div className="token-row">
              <span className="token-val">{SETUP_COMMAND}</span>
              <CopyButton value={SETUP_COMMAND} />
            </div>
          </div>

          <div className="alert alert-info">
            <span>📋</span>
            <span>
              <b>Các bước:</b> 1) Tạo Codespace từ repo → 2) chạy <code>{SETUP_COMMAND}</code> →
              3) paste NODE_ID/NODE_TOKEN khi được hỏi → 4) script tự start worker &amp; mở port 8100.
            </span>
          </div>

          <div className="modal-actions mt-16">
            <button className="btn btn-primary" onClick={() => setCredentials(null)}>
              Tôi đã lưu credentials
            </button>
          </div>
        </Modal>
      )}

      {/* Confirm modals */}
      {confirm?.kind === 'disable' && (
        <ConfirmModal
          title="Disable node?"
          message={`Node "${confirm.node.name}" sẽ không nhận job mới cho đến khi được enable lại.`}
          confirmLabel="Disable"
          loading={actionLoading}
          onConfirm={runAction}
          onCancel={() => setConfirm(null)}
        />
      )}
      {confirm?.kind === 'enable' && (
        <ConfirmModal
          title="Enable node?"
          message={`Node "${confirm.node.name}" sẽ lại được phân job (tùy heartbeat).`}
          confirmLabel="Enable"
          loading={actionLoading}
          onConfirm={runAction}
          onCancel={() => setConfirm(null)}
        />
      )}
      {confirm?.kind === 'rotate' && (
        <ConfirmModal
          title="Rotate token?"
          message="Token cũ sẽ bị vô hiệu ngay lập tức. Worker đang chạy cần được cập nhật NODE_TOKEN mới."
          confirmLabel="Rotate token"
          danger
          loading={actionLoading}
          onConfirm={runAction}
          onCancel={() => setConfirm(null)}
        />
      )}
      {confirm?.kind === 'delete' && (
        <ConfirmModal
          title="Xóa node agent?"
          message={
            confirm.node.status === 'BUSY' ? (
              <>
                <div className="alert alert-error mb-16">
                  <span>🚫</span>
                  <span>Node đang <b>BUSY</b>. Job hiện tại sẽ mất worker.</span>
                </div>
                <label className="flex gap-8">
                  <input
                    type="checkbox"
                    checked={confirm.force}
                    onChange={(e) => setConfirm({ ...confirm, force: e.target.checked })}
                  />
                  Force delete (xóa dù đang BUSY)
                </label>
              </>
            ) : (
              `Node "${confirm.node.name}" sẽ bị xóa. Job history được giữ lại.`
            )
          }
          confirmLabel="Xóa node"
          danger
          loading={actionLoading}
          onConfirm={runAction}
          onCancel={() => setConfirm(null)}
        />
      )}
    </>
  );
}
