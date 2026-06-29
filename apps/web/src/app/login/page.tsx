'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { api, ApiError } from '@/lib/api';

export default function LoginPage() {
  const [secretKey, setSecretKey] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const data = await api.login(secretKey);
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      router.push('/dashboard');
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === 'INVALID_SECRET_KEY') {
          setError('Secret key không hợp lệ');
        } else if (err.code === 'USER_BLOCKED') {
          setError('Tài khoản đã bị khóa');
        } else if (err.code === 'KEY_REVOKED') {
          setError('Secret key đã bị thu hồi');
        } else {
          setError('Đăng nhập thất bại. Vui lòng thử lại.');
        }
      } else {
        setError('Lỗi kết nối. Vui lòng thử lại.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="card" style={{ maxWidth: '400px', width: '100%' }}>
        <h1 style={{ marginBottom: '24px', textAlign: 'center' }}>Reup Vietsub</h1>
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
              Secret Key
            </label>
            <input
              type="text"
              className="input"
              value={secretKey}
              onChange={(e) => setSecretKey(e.target.value)}
              placeholder="sub_live_xxx"
              disabled={loading}
              required
            />
          </div>
          {error && <div className="error">{error}</div>}
          <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '16px' }} disabled={loading}>
            {loading ? 'Đang đăng nhập...' : 'Đăng nhập'}
          </button>
        </form>
      </div>
    </div>
  );
}
