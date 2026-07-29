'use client'

import { Text } from '@outception-com/orbit'
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from '@outception-com/ui/components/ui/dialog'
import { useState, type ReactNode } from 'react'

/** A footer link that opens a legal document (Privacy / Terms) as a popup dialog
 * over the wall - a dimmed overlay, click-outside or Escape to dismiss, matching
 * the source/language palettes. The content scrolls inside the dialog. */
export const LegalDialog = ({
  label,
  title,
  children,
}: {
  label: string
  title: string
  children: ReactNode
}) => {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="cursor-pointer"
      >
        <Text variant="caption" color="muted">
          {label}
        </Text>
      </button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="paper-search max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-2xl border-0 p-6 text-black md:p-10 dark:text-white">
          <DialogTitle className="sr-only">{title}</DialogTitle>
          {children}
        </DialogContent>
      </Dialog>
    </>
  )
}
