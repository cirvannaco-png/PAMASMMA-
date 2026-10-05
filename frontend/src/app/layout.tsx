import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { Toaster } from "react-hot-toast";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], display: "swap" });
const jetbrainsMono = JetBrains_Mono({ subsets: ["latin"], display: "swap" });

export const metadata: Metadata = {
  title: "PAMASMMA — Governed Synthetic Executive Intelligence",
  description:
    "Principal cognitive infrastructure for Kelson Mwangi · Cirvanna · Nakuru, Kenya",
  robots: "noindex, nofollow", // private system
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.className} ${jetbrainsMono.className}`}>
      <head>
      </head>
      <body className="h-screen overflow-hidden bg-[#04040D]">
        {children}
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: "#0C0C22",
              color: "#D0D0EC",
              border: "1px solid #1A1A3A",
              fontFamily: "Inter, sans-serif",
              fontSize: "13px",
            },
          }}
        />
      </body>
    </html>
  );
}
