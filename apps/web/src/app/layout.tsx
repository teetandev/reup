import './globals.css';

export const metadata = {
  title: 'Reup Vietsub',
  description: 'Dịch video Trung-Việt tự động',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
