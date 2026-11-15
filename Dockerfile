FROM python:3.15-alpine AS builder

WORKDIR /app

RUN apk add fontconfig build-base tiff-dev jpeg-dev openjpeg-dev \
    zlib-dev freetype-dev lcms2-dev libwebp-dev tcl-dev tk-dev \
    harfbuzz-dev fribidi-dev libimagequant-dev libxcb-dev libpng-dev \
    libdmtx libdmtx-dev

RUN python3 -m venv /app/.venv
ENV PATH=/app/.venv/bin:$PATH

COPY requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

FROM python:3.15-alpine

# gcc needed because pythons find_libary doesn't work without it https://bugs.python.org/issue21622
# libusb for usb:// printer paths (pyusb backend)
RUN apk add gcc fontconfig jpeg lcms2 zlib freetype tcl tk harfbuzz \
    fribidi libimagequant libxcb libpng libdmtx libdmtx-dev libusb

WORKDIR /app

COPY --from=builder /app /app
ENV PATH=/app/.venv/bin:$PATH

COPY . .

ARG BUILD_VERSION=dev
LABEL io.hass.type="addon" \
      io.hass.name="Brother QL Grocy Labels" \
      io.hass.version="${BUILD_VERSION}"

EXPOSE 8000
CMD ["gunicorn", "--conf", "/app/gunicorn_conf.py", "--bind", "0.0.0.0:8000", "app:app"]