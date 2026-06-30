import './globals.css';
import { ToastProvider } from '@/components/ui';

export const metadata = {
  title: 'Reup Vietsub',
  description: 'Dịch video Trung-Việt tự động',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body>
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  );
}
