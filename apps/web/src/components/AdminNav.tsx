'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

export default function AdminNav() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (userData) {
      const u = JSON.parse(userData);
      setUser(u);
      if (u.role !== 'ADMIN') {
        router.push('/dashboard');
      }
    } else {
      router.push('/login');
    }
  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    router.push('/login');
  };

  return (
    <nav className="nav">
      <div className="nav-content">
        <Link href="/admin" className="nav-title">Reup Vietsub Admin</Link>
        <div className="nav-links">
          <Link href="/admin" className="nav-link">Tổng quan</Link>
          <Link href="/admin/users" className="nav-link">Người dùng</Link>
          <Link href="/admin/nodes" className="nav-link">VPS Nodes</Link>
          <Link href="/admin/jobs" className="nav-link">Jobs</Link>
          {user && <span style={{ color: '#666' }}>{user.display_name}</span>}
          <button onClick={handleLogout} className="btn btn-secondary" style={{ padding: '6px 12px' }}>
            Đăng xuất
          </button>
        </div>
      </div>
    </nav>
  );
}
