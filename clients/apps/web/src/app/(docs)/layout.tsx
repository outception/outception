import { OutceptionThemeProvider } from '../providers'

export default function DocsRootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <OutceptionThemeProvider>{children}</OutceptionThemeProvider>
}
