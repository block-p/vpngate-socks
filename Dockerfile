FROM alpine:latest

RUN apk add --no-cache openvpn dante-server iproute2 bash curl

COPY sockd.conf /etc/sockd.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 1080

ENTRYPOINT ["/entrypoint.sh"]
