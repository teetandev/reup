'use client';

import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

export default function AdminNav() {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<any>(null);
  const cls = (href: string) =>
    `nav-link${pathname === href || (href !== '/admin' && pathname?.startsWith(href)) ? ' active' : ''}`;

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
        <Link href="/admin" className="nav-title">⚡ Reup Vietsub Admin</Link>
        <div className="nav-links">
          <Link href="/admin" className={cls('/admin')}>Tổng quan</Link>
          <Link href="/admin/users" className={cls('/admin/users')}>Người dùng</Link>
          <Link href="/admin/nodes" className={cls('/admin/nodes')}>VPS Nodes</Link>
          <Link href="/admin/jobs" className={cls('/admin/jobs')}>Jobs</Link>
          {user && <span className="text-soft text-sm">{user.display_name}</span>}
          <button onClick={handleLogout} className="btn btn-secondary btn-sm">
            Đăng xuất
          </button>
        </div>
      </div>
    </nav>
  );
}
