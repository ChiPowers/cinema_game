import type { Metadata } from "next";
import { JetBrains_Mono } from "next/font/google";
import "./globals.css";

const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "Cinema Game",
  description: "Connect actors through movies — six degrees of cinema.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="bg-cinema-black">
      <body className={`${mono.variable} font-mono text-white antialiased`}>
        {children}
      </body>
    </html>
  );
}
