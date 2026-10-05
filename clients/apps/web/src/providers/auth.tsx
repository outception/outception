'use client'

import { schemas } from '@outception-com/client'
import React from 'react'

type AuthContextValue = {
  user?: schemas['UserRead']
  setUser: React.Dispatch<React.SetStateAction<schemas['UserRead']>>
}

const stub = (): never => {
  throw new Error('You forgot to wrap your component in <UserContextProvider>.')
}

export const AuthContext = React.createContext<AuthContextValue>(
  // eslint-disable-next-line @typescript-eslint/ban-ts-comment
  // @ts-ignore
  stub,
)

export const UserContextProvider = ({
  user: _user,
  children,
}: {
  user: schemas['UserRead'] | undefined
  children: React.ReactNode
}) => {
  const [user, setUser] = React.useState<schemas['UserRead'] | undefined>(_user)

  const contextValue = React.useMemo(
    () => ({
      user,
      setUser: setUser as React.Dispatch<
        React.SetStateAction<schemas['UserRead']>
      >,
    }),
    [user, setUser],
  )

  return (
    <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>
  )
}
