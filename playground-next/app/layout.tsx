import type { Metadata } from "next";
import "./globals.css";
import "prismjs/themes/prism-tomorrow.css";

export const metadata: Metadata = {
  title: "QAlityDeep – Eval API",
  description: "Developer documentation and API playground",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="h-screen overflow-hidden font-sans">{children}</body>
    </html>
  );
}
