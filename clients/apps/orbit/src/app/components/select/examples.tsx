'use client'

import { useState } from 'react'
import { Box } from '@outception-com/orbit/Box'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from '@outception-com/orbit'

export function BasicDemo() {
  const [value, setValue] = useState<string>('')
  return (
    <Box width={240}>
      <Select value={value} onValueChange={setValue}>
        <SelectTrigger>
          <SelectValue placeholder="Select a plan" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="free">Free</SelectItem>
          <SelectItem value="pro">Pro</SelectItem>
          <SelectItem value="scale">Scale</SelectItem>
          <SelectItem value="enterprise" disabled>
            Enterprise
          </SelectItem>
        </SelectContent>
      </Select>
    </Box>
  )
}

export function GroupedDemo() {
  const [value, setValue] = useState<string>('')
  return (
    <Box width={240}>
      <Select value={value} onValueChange={setValue}>
        <SelectTrigger>
          <SelectValue placeholder="Select a timezone" />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectLabel>Americas</SelectLabel>
            <SelectItem value="est">Eastern</SelectItem>
            <SelectItem value="pst">Pacific</SelectItem>
          </SelectGroup>
          <SelectSeparator />
          <SelectGroup>
            <SelectLabel>Europe</SelectLabel>
            <SelectItem value="gmt">London</SelectItem>
            <SelectItem value="cet">Central European</SelectItem>
          </SelectGroup>
        </SelectContent>
      </Select>
    </Box>
  )
}
