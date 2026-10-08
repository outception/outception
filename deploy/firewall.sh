#!/usr/bin/env bash
# Only the edge reaches the web ports. Caddy publishes 80 and 443 through
# Docker, and Docker's own forwarding rules accept such traffic before the
# host firewall sees it, so the host rules alone would not close the origin.
# This script does both: an address set checked in Docker's DOCKER-USER
# chain for the published ports (IPv4 and IPv6 forwarding), and ufw rules
# for anything that reaches the host itself (Docker's IPv6 proxy among
# them). Container egress is untouched: the forwarding rule matches only
# new connections arriving on the external interface. SSH stays open, and
# is allowed before anything is denied.
#
# Root runs it from a root-owned copy (see provision.sh): at boot, before
# Docker publishes the web ports (the address sets and the forwarding rule
# live in memory), and weekly, since the edge's ranges change now and then.
# The last good list is kept on disk, so a boot before the network is up,
# or a failed download, applies the known ranges instead of leaving the
# ports open. Every run converges: rules for ranges still published are
# kept or added, stale ones removed, and adding comes first so there is
# never a moment without the edge allowed.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Run as root (sudo)." >&2; exit 1; }

state="${STATE_DIRECTORY:-/var/lib/outception-firewall}"
mkdir -p "$state"
chmod 700 "$state"

if ! command -v ipset >/dev/null 2>&1; then
  apt-get update -q >/dev/null
  apt-get install -y -q ipset >/dev/null
fi

v6=1
[ -d /proc/sys/net/ipv6 ] || v6=0
if [ -f /etc/default/ufw ] && grep -q '^IPV6=no' /etc/default/ufw; then v6=0; fi

# A list counts only if every token is a well-formed range and there are
# enough of them: a blank or truncated answer must never empty the sets.
# (The edge publishes 15 IPv4 and 7 IPv6 ranges today.)
valid() { # $1 = ranges, $2 = regex, $3 = minimum count
  local range count=0
  for range in $1; do
    [[ "$range" =~ $2 ]] || return 1
    count=$((count + 1))
  done
  [ "$count" -ge "$3" ]
}
re4='^([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$'
re6='^[0-9a-fA-F:]+/[0-9]{1,3}$'
fetched4="$(curl -fsS --max-time 15 https://www.cloudflare.com/ips-v4 2>/dev/null || true)"
fetched6="$(curl -fsS --max-time 15 https://www.cloudflare.com/ips-v6 2>/dev/null || true)"
if valid "$fetched4" "$re4" 5 && valid "$fetched6" "$re6" 3; then
  ranges4="$fetched4"
  ranges6="$fetched6"
  printf '%s\n' "$ranges4" > "$state/ranges4"
  printf '%s\n' "$ranges6" > "$state/ranges6"
elif [ -s "$state/ranges4" ] && [ -s "$state/ranges6" ]; then
  echo "edge list unavailable; applying the last good one" >&2
  ranges4="$(cat "$state/ranges4")"
  ranges6="$(cat "$state/ranges6")"
  valid "$ranges4" "$re4" 5 && valid "$ranges6" "$re6" 3 \
    || { echo "the saved edge list is damaged" >&2; exit 1; }
else
  echo "could not read the edge ranges and none are saved" >&2
  exit 1
fi
# One space-separated list (the answers come one range per line), so the
# stale check below can look a range up by " range ".
wanted="$(printf '%s ' $ranges4)"
[ "$v6" = 1 ] && wanted="$wanted$(printf '%s ' $ranges6)"

# 1. SSH first, before any default changes.
ufw allow OpenSSH >/dev/null 2>&1 || ufw allow 22/tcp >/dev/null

# 2. The address sets, rebuilt by swap so they are never empty in use.
rebuild_set() { # $1 = name, $2 = family, $3 = ranges
  ipset create "$1" hash:net family "$2" -exist
  ipset create "$1_new" hash:net family "$2" -exist
  ipset flush "$1_new"
  for range in $3; do ipset add "$1_new" "$range" -exist; done
  ipset swap "$1_new" "$1"
  ipset destroy "$1_new"
}
rebuild_set edge4 inet "$ranges4"
[ "$v6" = 1 ] && rebuild_set edge6 inet6 "$ranges6"

# 3. Docker's forwarding path: drop new connections to the web ports from
#    outside the sets, on the interface that carries the default route.
guard() { # $1 = iptables binary, $2 = interface, $3 = set
  local rule=(-i "$2" -p tcp -m multiport --dports 80,443 -m conntrack --ctstate NEW -m set ! --match-set "$3" src -j DROP)
  "$1" -N DOCKER-USER 2>/dev/null || true
  "$1" -C DOCKER-USER "${rule[@]}" 2>/dev/null || "$1" -I DOCKER-USER 1 "${rule[@]}"
}
# Early at boot the route may not be up yet: the interface last seen is
# kept with the ranges.
iface4="$(ip -4 route show default 2>/dev/null | awk '/default/ {print $5; exit}')"
if [ -n "$iface4" ]; then
  printf '%s\n' "$iface4" > "$state/iface4"
elif [ -s "$state/iface4" ]; then
  iface4="$(cat "$state/iface4")"
fi
[ -n "$iface4" ] || { echo "no IPv4 default interface" >&2; exit 1; }
guard iptables "$iface4" edge4
if [ "$v6" = 1 ]; then
  iface6="$(ip -6 route show default 2>/dev/null | awk '/default/ {print $5; exit}')"
  guard ip6tables "${iface6:-$iface4}" edge6
fi

# 4. The host's own ports: one rule per range for both web ports. Add what
#    is missing first (ufw skips rules it already has), then remove stale
#    edge rules, one at a time since numbers shift after each delete.
for range in $wanted; do
  ufw allow proto tcp from "$range" to any port 80,443 comment edge >/dev/null
done
stale_rule() { # prints the number of the first edge rule not wanted, if any
  local listing
  listing="$(ufw status numbered)"
  awk -v wanted=" $wanted " '
    /# edge/ {
      n = $0; sub(/^\[ */, "", n); sub(/\].*/, "", n)
      line = $0; sub(/^\[[^]]*\] */, "", line)
      split(line, f, /  +/)
      to = f[1]; from = f[3]
      if ((to != "80,443/tcp" && to != "80,443/tcp (v6)") || index(wanted, " " from " ") == 0) { print n; exit }
    }' <<<"$listing"
}
while n="$(stale_rule)"; [ -n "$n" ]; do
  ufw --force delete "$n" >/dev/null
done
ufw delete allow 80/tcp >/dev/null 2>&1 || true
ufw delete allow 443/tcp >/dev/null 2>&1 || true

# 5. Deny by default, last, with SSH and the edge already allowed. Only
#    when something differs: on an active ufw, setting a default reloads
#    every rule, with a moment of the host wide open in between.
verbose="$(ufw status verbose)"
if ! grep -q '^Default: deny (incoming), allow (outgoing)' <<<"$verbose"; then
  ufw default deny incoming >/dev/null
  ufw default allow outgoing >/dev/null
fi
grep -q '^Status: active' <<<"$verbose" || ufw --force enable >/dev/null

count6=0
[ "$v6" = 1 ] && count6="$(ipset list edge6 | grep -c '/')"
echo "edge: $(ipset list edge4 | grep -c '/') v4 ranges, $count6 v6 ranges; ufw edge rules: $(grep -c '# edge' <<<"$(ufw status)"); interface $iface4"
