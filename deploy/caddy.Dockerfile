# Caddy built with the Cloudflare DNS plugin so it can solve the ACME DNS-01
# challenge through Cloudflare. This issues real Let's Encrypt certs even when
# the records are proxied (orange cloud), no port-80 challenge needed.
FROM caddy:2-builder AS builder
RUN xcaddy build --with github.com/caddy-dns/cloudflare

FROM caddy:2
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
