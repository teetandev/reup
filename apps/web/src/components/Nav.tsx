'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

export default function Nav() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (userData) {
      setUser(JSON.parse(userData));
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    router.push('/login');
  };

  return (
    <nav className="nav">
      <div className="nav-content">
        <Link href="/dashboard" className="nav-title">Reup Vietsub</Link>
        <div className="nav-links">
          <Link href="/dashboard" className="nav-link">Trang chủ</Link>
          <Link href="/jobs" className="nav-link">Lịch sử</Link>
          {user && <span style={{ color: '#666' }}>{user.display_name}</span>}
          <button onClick={handleLogout} className="btn btn-secondary" style={{ padding: '6px 12px' }}>
            Đăng xuất
          </button>
        </div>
      </div>
    </nav>
  );
}
