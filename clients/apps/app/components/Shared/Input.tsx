import { useTone } from '@/design-system/toneStore'
import { useTheme } from '@/design-system/useTheme'
import { forwardRef } from 'react'
import { TextInput, TextInputProps } from 'react-native'

export const Input = forwardRef<TextInput, TextInputProps>((props, ref) => {
  const theme = useTheme()
  const tone = useTone()

  return (
    <TextInput
      ref={ref}
      {...props}
      placeholderTextColor={theme.colors.subtext}
      keyboardAppearance={tone === 'dark' ? 'dark' : 'light'}
      style={[
        {
          borderRadius: theme.borderRadii['border-radius-12'],
          borderWidth: 1,
          padding: theme.spacing['spacing-16'],
          fontSize: 16,
          backgroundColor: theme.colors.card,
          color: theme.colors.text,
          borderColor: theme.colors.border,
        },
        props.style,
      ]}
    />
  )
})

Input.displayName = 'Input'
