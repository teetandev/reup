'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    const userData = localStorage.getItem('user');

    if (!token || !userData) {
      router.push('/login');
      return;
    }

    const parsedUser = JSON.parse(userData);
    if (parsedUser.role !== 'ADMIN') {
      router.push('/dashboard');
      return;
    }

    setUser(parsedUser);
    setLoading(false);
  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    router.push('/login');
  };

  if (loading) {
    return <div style={{ padding: '20px' }}>Đang tải...</div>;
  }

  return (
    <>
      <nav className="nav">
        <div className="nav-content">
          <Link href="/admin" className="nav-title">Reup Vietsub Admin</Link>
          <div className="nav-links">
            <Link href="/admin" className={`nav-link ${pathname === '/admin' ? 'active' : ''}`}>Dashboard</Link>
            <Link href="/admin/users" className={`nav-link ${pathname?.startsWith('/admin/users') ? 'active' : ''}`}>Người dùng</Link>
            <Link href="/admin/nodes" className={`nav-link ${pathname?.startsWith('/admin/nodes') ? 'active' : ''}`}>VPS Nodes</Link>
            <Link href="/admin/jobs" className={`nav-link ${pathname?.startsWith('/admin/jobs') ? 'active' : ''}`}>Jobs</Link>
            <Link href="/dashboard" className="nav-link">User View</Link>
            {user && <span style={{ color: '#666' }}>{user.display_name}</span>}
            <button onClick={handleLogout} className="btn btn-secondary" style={{ padding: '6px 12px' }}>
              Đăng xuất
            </button>
          </div>
        </div>
      </nav>
      <div className="container">{children}</div>
    </>
  );
}
