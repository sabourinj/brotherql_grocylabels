# 0.8.1

- Added `RIGHT_MARGIN` (default 24 dots, about 2mm) so the dates and name stay clear of the right edge of the label

# 0.8.0

- Added `DUE_DATE_PREFIX` to replace Grocy's `DD:` before the due date (add-on default `Due:`)
- If the due date text has no date in it, the stock entry's due date is used

# 0.7.0

- Purchased and opened dates are read from the `stock_entry` Grocy sends with stock label webhooks, so Grocy can call `/print` directly
- Requests can be sent as JSON (Grocy's `LABEL_PRINTER_HOOK_JSON`)
- Optional `GROCY_URL` / `GROCY_API_KEY` lookup so labels reprinted on opening get the opened date
- `battery`, `chore` and `recipe` names now work for GET requests too

# 0.6.0

- Added optional `purchased_date` and `opened_date` parameters, printed above the due date
- Added `PURCHASED_DATE_PREFIX` and `OPENED_DATE_PREFIX` settings
- Packaged as a Home Assistant add-on, settings can come from `/data/options.json`
- Docker image is now published to `ghcr.io/sabourinj/brotherql_grocylabels`
- Added `libusb` to the image for `usb://` printer paths
- Name text uses fewer lines on die-cut labels when it would otherwise overlap the dates
- Fixed `DUE_DATE_FONT` being read from `NAME_FONT`

# 0.5.0

- Updated python dependencies (Flask 3.1, Pillow 13, qrcode 8, gunicorn 26)
- Updated the docker base image to python 3.15-alpine, python 3.11 or newer is now required
- Updated GitHub workflow actions to current major versions

# 0.4.2

- add support for `62red` labels (and other red labels)

# 0.4.1

- publish main branch as latest docker image

# 0.4.0

- Added support for printing endless labels

# 0.3.0

- Added support for using QR codes instead of Datamatrix

# 0.2.0

- Scaling barcode by 2x or 4x space permitting
- Centered text