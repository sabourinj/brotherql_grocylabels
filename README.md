# Brother QL Grocy Label Printer Service

<img src="example.png" alt="Example Label" width="348" height="135">

This project is intended to be a webhook target for [Grocy](https://github.com/grocy/grocy) to print labels to a brother QL label printer. 

Datamatrix or QR codes can be used with Datamatrix being the default. Datamatrix will fit better in smaller labels but I've found aren't as easily read by the Grocy 
barcode reader or by the [Android App](https://github.com/patzly/grocy-android).

Only die-cut labels are supported as I don't have any endless rolls to test with.

## Home Assistant Add-on

This repository is also a Home Assistant add-on repository (needs Home Assistant OS or Supervised).

1. In Home Assistant go to **Settings → Add-ons → Add-on Store**, open the **⋮** menu, choose **Repositories**
   and add `https://github.com/sabourinj/brotherql_grocylabels`.
2. Install **Brother QL Grocy Labels**, set the printer options on its **Configuration** tab and start it.

The add-on options match the environment variables below, in lower case. Setup details are in [the add-on docs](brotherql_grocylabels/DOCS.md).

To release a new add-on version: bump `version` in [brotherql_grocylabels/config.yaml](brotherql_grocylabels/config.yaml),
merge to `main` and push a matching tag (e.g. `v0.6.0`). The GitHub workflow builds the image and publishes it to
`ghcr.io/sabourinj/brotherql_grocylabels` with that version, which is what the add-on installs.

## Connecting Grocy

Once you have this running somewhere update your config at `app/data/config.php` to match the following. Presuming that you have this running on localhost at port 8000.

```
    // Label printer settings
    Setting('LABEL_PRINTER_WEBHOOK', 'http://127.0.0.1:8000/print');
    Setting('LABEL_PRINTER_RUN_SERVER', true);
    Setting('LABEL_PRINTER_PARAMS', []);
    Setting('LABEL_PRINTER_HOOK_JSON', false);

    Setting('FEATURE_FLAG_LABEL_PRINTER', true);
```

## Environment Variables

The label size and printer are configured via environmental variables. You can also create a `.env` file instead.

| Variable           | Default               | Description                                                                                   |
| ------------------ | --------------------- | --------------------------------------------------------------------------------------------- |
| LABEL_SIZE         | 62x29                 | See the [brother_ql](https://github.com/pklaus/brother_ql) readme for the names of the labels |
| PRINTER_MODEL      | QL-500                | The printer model. One of the values accepted by brother_ql                                   |
| PRINTER_PATH       | file:///dev/usb/lp1   | Where the printer is found on the system. For network printers use `tcp://printer.address`    |
| BARCODE_FORMAT     | Datamatrix            | `Datamatrix` or `QRCode`                                                                      |
| NAME_FONT          | NotoSerif-Regular.ttf | The file name of the font in the fonts directory                                              |
| NAME_FONT_SIZE     | 48                    | The size of that font                                                                         |
| NAME_MAX_LINES     | 4                     | The maximum number of lines to use for the name                                               |
| DUE_DATE_FONT      | NotoSerif-Regular.ttf | The file name of the font in the fonts directory, used for all dates                          |
| DUE_DATE_FONT_SIZE | 30                    | The size of that font                                                                         |
| ENDLESS_MARGIN     | 10                    | The top & bottom margin to add when using endless labels                                      |
| RIGHT_MARGIN       | 24                    | Dots (about 12 per mm) kept clear between the name/dates and the right edge of the label      |
| PURCHASED_DATE_PREFIX | `Purchased:`       | Text printed (plus a space) before `purchased_date`. Set it empty to print the value as-is    |
| OPENED_DATE_PREFIX | `Opened:`             | Text printed (plus a space) before `opened_date`. Set it empty to print the value as-is       |
| DUE_DATE_PREFIX    | *(unset)*             | Replaces the prefix on `due_date` (Grocy sends `DD: <date>`), plus a space. Unset prints `due_date` as given, empty prints just the date |
| BOLD_DATES         | `true`                | Print the dates in bold (the prefixes stay regular)                                           |
| DATE_FORMAT        | `YYYY-MM-DD`          | How dates are printed: `YYYY-MM-DD`, `MM/DD/YYYY`, `DD/MM/YYYY`, `MM/DD/YY`, `DD.MM.YYYY`, `Mon D, YYYY`, `D Mon YYYY`, or any [strftime](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes) pattern |
| GROCY_URL          |                       | Optional, Grocy's address e.g. `http://192.168.1.10:9192`. See [Grocy API lookup](#grocy-api-lookup) |
| GROCY_API_KEY      |                       | Optional, a Grocy API key, needed with `GROCY_URL`                                            |
| GROCY_LOOKUP_DELAY | 3                     | Seconds to wait before looking up the stock entry in Grocy                                    |

Included fonts are `NotoSans-Regular.ttf` and `NotoSerif-Regular.ttf`

## Endless Labels

These are supported, for example the `62` label size. The length of the label will be big enough to accommodate the max number of lines including a margin.
You may want to experiment with font sizes and line count to get the most out of it.

## Endpoints

Two endpoints are available `/print` and `/image` both accept the same parameters. `/image` will return the rendered image as a PNG instead of sending to the printer.

### Parameters

POST or GET accepted.

| Name      | Use                                 |
| --------- | ------------------------------------|
| product   | name                                |
| battery   | name                                |
| chore     | name                                |
| recipe    | name                                |
| grocycode | the barcode                         |
| due_date  | the text at the bottom of the label |
| purchased_date | purchased date, printed above the due date with `PURCHASED_DATE_PREFIX` in front |
| opened_date    | opened date, printed above the due date with `OPENED_DATE_PREFIX` in front       |
| stock_entry    | sent by Grocy with stock labels, its `purchased_date` and `opened_date` are used when the two above aren't given |

The name will use whichever parameter is given. Parameters can also be sent as a JSON body (`LABEL_PRINTER_HOOK_JSON` set to `true` in Grocy).

The dates are stacked in the bottom right corner in the order purchased, opened, due, with the due date always at the bottom. Any that are missing are left out.
On die-cut labels the name will use fewer lines if needed so it doesn't run into the dates.

Grocy's label webhook includes the stock entry, so purchased and opened dates print with no extra setup.
You can also pass them yourself, for example: `/print?product=Milk&grocycode=grcy:p:1&due_date=DD:%202026-11-21&purchased_date=2026-11-14&opened_date=2026-11-15`

### Grocy API lookup

When a product has "Auto reprint stock entry label" turned on, Grocy reprints the label when it's opened, but sends
the webhook before it saves the stock entry as opened, so the label would have no opened date.

Set `GROCY_URL` and `GROCY_API_KEY` to fix this. Stock labels are then printed in the background: `/print` replies
straight away, waits `GROCY_LOOKUP_DELAY` seconds, reads the stock entry from the Grocy API, and prints from that.
`/image` does the lookup without waiting. If the lookup fails, the webhook data is used and a warning is logged.

## Running

**Note:** Theres no security on this web service, so don't make it publicly available.

This has been tested with python 3.15, python 3.11 or newer is required.

You will need to install the `libdmtx` library for the barcodes to generate, see [pylibdmtx](https://pypi.org/project/pylibdmtx/) documentation on pypi.

Its advisable to run and install in a [venv](https://docs.python.org/3/library/venv.html). For example:

```
    # Create and enter the venv
    python -m venv .venv
    source ./.venv/bin/activate
    # Install packages
    python -m pip install -U -r requirements.txt

    # exit with ./.venv/bin/deactivate
```

For development you can use `flask run --debug` to run the service on port 5000. Alternatively use `gunicorn -c gunicorn_conf.py app:app` to run the service on port 8000.

## TODO

- Some more formatting options

### Docker

A Dockerfile is included based on a python 3.15 alpine image. The default port is 8000.

Published to Dockerhub as [sam159/brotherql_grocylabels](https://hub.docker.com/r/sam159/brotherql_grocylabels) for architectures amd64, arm64, and armv7.

As an example, you can launch this with `docker run -d -p 8000:8000 -e PRINTER_MODEL=QL-500 -e PRINTER_PATH=file:///dev/usb/lp1 sam159/brotherql_grocylabels:latest`.

An example `docker-compose.yml` file can be found [here](docker-compose.yml).

## Contributing

I'll try to keep on top of bugs but feature requests may go unfulfilled. Please use the issue tracking in Github.

PRs are welcome!
