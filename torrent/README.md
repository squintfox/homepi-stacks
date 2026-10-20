# setup

- Standalone Compose stack (gluetun + qbittorrent). Requires:
    - a Portainer environment named `local-standalone` (Docker Standalone, same node as the swarm)
    - `webproxy-backend` network created with `--attachable`
- generate a wireguard config file in Proton VPN
    - add key to vault (`hpi_protonvpn_private_key`)
- qbittorrent admin password is in the container logs
- verify the VPN: `docker exec <qbittorrent> curl -s https://ipinfo.io` should show a Proton IP
