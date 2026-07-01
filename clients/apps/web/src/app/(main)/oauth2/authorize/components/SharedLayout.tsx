import LogoIcon from '@/components/Brand/logos/LogoIcon'
import { UploadImage } from '@/components/Image/Image'
import AddOutlined from '@mui/icons-material/AddOutlined'
import { schemas } from '@outception-com/client'

export default function SharedLayout({
  client,
  introduction,
  children,
}: {
  client?: schemas['AuthorizeResponseOrganization']['client']
  introduction?: string | React.ReactNode
  children?: React.ReactNode
}) {
  return (
    <div className="flex flex-col items-center gap-12 pt-16 md:p-16">
      <div className="flex w-96 flex-col items-center gap-6">
        <div className="flex flex-row items-center gap-2">
          <LogoIcon size={40} />
          {client?.logo_uri && (
            <>
              <AddOutlined className="h-5" />
              <UploadImage
                src={client.logo_uri}
                approximateWidth={40}
                className="h-10"
                alt={client.client_name ?? client.client_id}
              />
            </>
          )}
        </div>
        {introduction && (
          <div className="dark:text-outception-400 w-full text-center text-lg text-gray-600">
            {introduction}
          </div>
        )}
      </div>
      {children && <div className="flex w-lg flex-col gap-6">{children}</div>}
    </div>
  )
}
