FROM alpine:3.20
WORKDIR /src
COPY . .
LABEL org.opencontainers.image.source="https://github.com/mafzalkalwardev/fmcsa-safer-scraper"
CMD ["sh", "-c", "echo 'fmcsa-safer-scraper source package' && ls -1"]
