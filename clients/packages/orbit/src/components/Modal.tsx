'use client'

import { motion } from 'motion/react'
import React, {
  FunctionComponent,
  MouseEvent,
  useCallback,
  useEffect,
  type JSX,
} from 'react'
import ReactDOM from 'react-dom'
import FocusLock from 'react-focus-lock'
import { twMerge } from 'tailwind-merge'
import { Button } from './Button'
import { X } from 'lucide-react'

export interface ModalProps {
  title: string | JSX.Element
  isShown: boolean
  hide: () => void
  modalContent: JSX.Element
  className?: string
}

export const Modal: FunctionComponent<ModalProps> = ({
  title,
  isShown,
  hide,
  modalContent,
  className,
}) => {
  const ref = React.useRef<HTMLDivElement>(null)

  const onKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      const contains = ref.current?.contains(event.target as Node)

      if (event.keyCode === 27 && isShown && contains) {
        hide()
      }
    },
    [hide, isShown],
  )

  useEffect(() => {
    if (isShown) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = 'unset'
    }
  }, [isShown, hide])

  const onInnerClick = (e: MouseEvent) => {
    e.stopPropagation()
  }

  const modal = (
    <FocusLock>
      <div
        ref={ref}
        className="fixed top-0 right-0 bottom-0 left-0 z-50 overflow-hidden focus-within:outline-none dark:text-white"
        aria-modal
        tabIndex={-1}
        role="dialog"
        onKeyDown={onKeyDown}
      >
        <div
          className="glass-overlay flex h-full flex-col items-center p-2 md:w-full"
          onClick={(e) => {
            e.preventDefault()
            e.stopPropagation()
            hide()
          }}
        >
          <div className="block h-20 w-2 lg:max-h-[10%] lg:grow-2" />
          <motion.div
            className={twMerge(
              'glass-pop-strong relative z-10 flex max-h-full w-full flex-col gap-y-1 overflow-x-hidden overflow-y-auto rounded-3xl p-1 lg:w-[800px] lg:max-w-full',
              className,
            )}
            initial={{ opacity: 0, scale: 0.99 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.1, ease: 'easeInOut' }}
            onClick={onInnerClick}
          >
            <div className="flex flex-row items-center justify-between pt-1 pr-1 pb-0 pl-4 text-sm">
              <span className="dark:text-outception-500 text-gray-500">
                {title}
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="dark:text-outception-500 dark:hover:text-outception-400 size-8 rounded-full text-gray-500 hover:text-gray-600"
                onClick={hide}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex flex-col overflow-y-auto rounded-[20px] bg-transparent">
              {modalContent}
            </div>
          </motion.div>
        </div>
      </div>
    </FocusLock>
  )

  return isShown ? ReactDOM.createPortal(modal, document.body) : null
}
