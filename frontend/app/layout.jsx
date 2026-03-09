import "./globals.css";

export const metadata = {
  title: "Finance AI Deal Review",
  description: "Review extracted deal inputs before generating the workbook."
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
