import { Newsreader, Inter, JetBrains_Mono } from "next/font/google";
import { ThemeProvider } from "./theme";
import { Header, Footer } from "./components/Nav";
import "./globals.css";

const display = Newsreader({ subsets: ["latin"], weight: ["500", "600", "700"], style: ["normal", "italic"], variable: "--font-display" });
const body = Inter({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-body" });
const mono = JetBrains_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-mono" });

export const metadata = {
  title: "DataPilot",
  description: "A guarded, six-stage pipeline that turns plain-English questions into validated SQL.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={`${display.variable} ${body.variable} ${mono.variable}`}>
        <ThemeProvider>
          <div className="app-shell">
            <Header />
            <div className="app-body">{children}</div>
            <Footer />
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}