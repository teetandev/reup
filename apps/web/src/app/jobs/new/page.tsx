'use client';

import { useState, useRef, ChangeEvent } from 'react';
import { useRouter } from 'next/navigation';
import Nav from '@/components/Nav';
import { api, uploadToNode, startJob, ApiError } from '@/lib/api';

const MAX_FILE_SIZE = 500 * 1024 * 1024; // 500MB

export default function NewJobPage() {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [status, setStatus] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    setError('');
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    const ext = selectedFile.name.split('.').pop()?.toLowerCase();
    if (!ext || !['mp4', 'mov', 'mkv', 'webm'].includes(ext)) {
      setError('Chỉ chấp nhận file MP4, MOV, MKV, WEBM');
      return;
    }

    if (selectedFile.size > MAX_FILE_SIZE) {
      setError('File vượt quá 500MB');
      return;
    }

    setFile(selectedFile);
  };

  const handleUpload = async () => {
    if (!file) return;

    setError('');
    setUploading(true);
    setStatus('Đang tạo job...');

    try {
      // Step 1: Create job
      const jobData = await api.createJob(file.name, file.size);
      setStatus('Đang upload video...');

      // Step 2: Upload to VPS
      await uploadToNode(
        jobData.upload.url,
        jobData.upload.token,
        file,
        setUploadProgress
      );
      setStatus('Đang bắt đầu xử lý...');

      // Step 3: Start processing
      const nodeUrl = jobData.upload.url.split('/jobs/')[0];
      await startJob(nodeUrl, jobData.job_id, jobData.upload.token);

      // Redirect to job detail
      router.push(`/jobs/${jobData.job_id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === 'NO_NODE_AVAILABLE') {
          setError('Hiện chưa có VPS rảnh. Vui lòng thử lại sau.');
        } else if (err.code === 'FILE_TOO_LARGE') {
          setError('File quá lớn (tối đa 500MB)');
        } else if (err.code === 'USER_LIMIT_REACHED') {
          setError('Bạn đã đạt giới hạn job hôm nay');
        } else {
          setError('Có lỗi xảy ra: ' + err.message);
        }
      } else {
        setError('Upload thất bại. Vui lòng thử lại.');
      }
      setUploading(false);
    }
  };

  return (
    <>
      <Nav />
      <div className="container">
        <h1 style={{ marginBottom: '24px' }}>Upload Video Mới</h1>

        <div className="card" style={{ maxWidth: '600px' }}>
          <div className="file-input-wrapper">
            <input
              ref={fileInputRef}
              type="file"
              className="file-input"
              accept=".mp4,.mov,.mkv,.webm"
              onChange={handleFileChange}
              disabled={uploading}
            />
            <label
              className="file-input-label"
              onClick={() => fileInputRef.current?.click()}
            >
              {file ? (
                <>
                  <div style={{ fontSize: '16px', fontWeight: '600', marginBottom: '8px' }}>
                    {file.name}
                  </div>
                  <div style={{ fontSize: '14px', color: '#666' }}>
                    {(file.size / (1024 * 1024)).toFixed(2)} MB
                  </div>
                </>
              ) : (
                <>
                  <div style={{ fontSize: '16px', fontWeight: '600', marginBottom: '8px' }}>
                    Chọn file video
                  </div>
                  <div style={{ fontSize: '14px', color: '#666' }}>
                    MP4, MOV, MKV, WEBM (tối đa 500MB)
                  </div>
                </>
              )}
            </label>
          </div>

          {error && <div className="error" style={{ marginTop: '16px' }}>{error}</div>}

          {uploading && (
            <div style={{ marginTop: '24px' }}>
              <div style={{ marginBottom: '8px', fontSize: '14px', color: '#666' }}>
                {status}
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${uploadProgress}%` }} />
              </div>
              <div style={{ marginTop: '8px', fontSize: '14px', textAlign: 'center' }}>
                {uploadProgress}%
              </div>
            </div>
          )}

          <div style={{ marginTop: '24px', display: 'flex', gap: '12px' }}>
            <button
              onClick={handleUpload}
              className="btn btn-primary"
              disabled={!file || uploading}
              style={{ flex: 1 }}
            >
              {uploading ? 'Đang xử lý...' : 'Bắt đầu'}
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
