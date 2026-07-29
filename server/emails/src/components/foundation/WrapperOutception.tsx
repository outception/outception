import { Container, Preview } from 'react-email'
import OutceptionHeader from '../OutceptionHeader'
import WrapperBase from '../WrapperBase'

interface WrapperOutceptionProps {
  children: React.ReactNode
  preview?: string
}

const WrapperOutception = ({ children, preview }: WrapperOutceptionProps) => {
  return (
    <WrapperBase>
      {preview ? <Preview>{preview}</Preview> : null}
      <Container className="px-[12px] pt-[20px] pb-[10px]">
        <OutceptionHeader />
      </Container>
      <Container className="px-[20px] pt-[10px] pb-[20px]">
        {children}
      </Container>
    </WrapperBase>
  )
}

export default WrapperOutception
