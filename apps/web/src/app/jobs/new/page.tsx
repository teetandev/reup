'use client';

import { useState, useRef, ChangeEvent, DragEvent } from 'react';
import { useRouter } from 'next/navigation';
import Nav from '@/components/Nav';
import { useToast, formatBytes } from '@/components/ui';
import { api, uploadToNode, startJob, ApiError } from '@/lib/api';

const MAX_FILE_SIZE = 500 * 1024 * 1024; // 500MB
const ALLOWED = ['mp4', 'mov', 'mkv', 'webm'];

export default function NewJobPage() {
  const toast = useToast();
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [phase, setPhase] = useState<'idle' | 'creating' | 'uploading' | 'starting'>('idle');
  const [dragging, setDragging] = useState(false);

  const validate = (f: File): string | null => {
    const ext = f.name.split('.').pop()?.toLowerCase();
    if (!ext || !ALLOWED.includes(ext)) return 'Chỉ chấp nhận file MP4, MOV, MKV, WEBM';
    if (f.size > MAX_FILE_SIZE) return 'File vượt quá 500MB';
    return null;
  };

  const pick = (f: File | undefined) => {
    setError('');
    if (!f) return;
    const err = validate(f);
    if (err) {
      setError(err);
      return;
    }
    setFile(f);
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => pick(e.target.files?.[0]);

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (uploading) return;
    pick(e.dataTransfer.files?.[0]);
  };

  const handleUpload = async () => {
    if (!file || uploading) return; // guard against duplicate job creation
    setError('');
    setUploading(true);
    setPhase('creating');

    try {
      const jobData = await api.createJob(file.name, file.size);

      setPhase('uploading');
      await uploadToNode(jobData.upload.url, jobData.upload.token, file, setUploadProgress);

      setPhase('starting');
      const nodeUrl = jobData.upload.url.split('/jobs/')[0];
      await startJob(nodeUrl, jobData.job_id, jobData.upload.token);

      toast('Đã bắt đầu xử lý video', 'success');
      router.push(`/jobs/${jobData.job_id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === 'NO_NODE_AVAILABLE') {
          setError('Chưa có worker online hoặc heartbeat đã stale. Kiểm tra VPS Nodes.');
        } else if (err.code === 'FILE_TOO_LARGE') {
          setError('File quá lớn (tối đa 500MB).');
        } else if (err.code === 'USER_LIMIT_REACHED') {
          setError('Bạn đã đạt giới hạn job đồng thời/hôm nay.');
        } else {
          setError('Có lỗi xảy ra: ' + err.message);
        }
      } else {
        setError('Upload thất bại. Vui lòng thử lại.');
      }
      setUploading(false);
      setPhase('idle');
      setUploadProgress(0);
    }
  };

  const phaseLabel = {
    idle: '',
    creating: 'Đang tạo job...',
    uploading: `Đang upload video... ${uploadProgress}%`,
    starting: 'Đang khởi động pipeline...',
  }[phase];

  return (
    <>
      <Nav />
      <div className="container">
        <div className="page-header">
          <div>
            <h1>Upload video</h1>
            <div className="subtitle">Video tiếng Trung → phụ đề tiếng Việt (hardsub).</div>
          </div>
        </div>

        <div className="card" style={{ maxWidth: 640 }}>
          <div
            className="file-input-wrapper"
            onDragOver={(e) => {
              e.preventDefault();
              if (!uploading) setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            <input
              ref={fileInputRef}
              type="file"
              className="file-input"
              accept=".mp4,.mov,.mkv,.webm"
              onChange={handleFileChange}
              disabled={uploading}
            />
            <label
              className={`file-input-label ${dragging ? 'dragging' : ''}`}
              onClick={() => !uploading && fileInputRef.current?.click()}
            >
              {file ? (
                <>
                  <div style={{ fontSize: 30, marginBottom: 8 }}>🎬</div>
                  <div style={{ fontSize: 16, fontWeight: 650, marginBottom: 4 }}>{file.name}</div>
                  <div className="text-soft text-sm">{formatBytes(file.size)}</div>
                </>
              ) : (
                <>
                  <div style={{ fontSize: 30, marginBottom: 8 }}>⬆️</div>
                  <div style={{ fontSize: 16, fontWeight: 650, marginBottom: 4 }}>
                    Kéo thả hoặc bấm để chọn file
                  </div>
                  <div className="text-soft text-sm">MP4, MOV, MKV, WEBM · tối đa 500MB</div>
                </>
              )}
            </label>
          </div>

          {error && (
            <div className="alert alert-error mt-16">
              <span>⚠️</span>
              <span>{error}</span>
            </div>
          )}

          {uploading && (
            <div className="mt-24">
              <div className="flex-between mb-8">
                <span className="text-sm text-soft">{phaseLabel}</span>
                {phase === 'uploading' && <span className="text-sm">{uploadProgress}%</span>}
              </div>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: phase === 'uploading' ? `${uploadProgress}%` : '100%' }}
                />
              </div>
            </div>
          )}

          <div className="flex gap-12 mt-24">
            <button
              onClick={handleUpload}
              className="btn btn-primary btn-block"
              disabled={!file || uploading}
            >
              {uploading ? <span className="spinner" /> : 'Bắt đầu xử lý'}
            </button>
            <button
              onClick={() => router.push('/dashboard')}
              className="btn btn-secondary"
              disabled={uploading}
            >
              Hủy
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
