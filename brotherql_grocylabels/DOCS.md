# Brother QL Grocy Labels

A webhook target for Grocy that prints labels on a Brother QL label printer.
Labels show the product name, a grocycode barcode, and up to three dates: purchased, opened and due.

## Setup

1. Connect the printer. For USB, plug it into the Home Assistant machine **before** starting the add-on.
   For a network printer, note its IP address.
2. Set the options on the **Configuration** tab:
   - **Printer model**, e.g. `QL-700`.
   - **Printer path**: `file:///dev/usb/lp0` for USB, or `tcp://<printer ip>` for a network printer.
     If a USB printer isn't found at `lp0`, try `lp1`, or use the raw USB form `usb://0x04f9:<product id>`.
   - **Label size**: the label loaded in the printer, e.g. `62x29` (die-cut) or `62` (endless).
3. Start the add-on, then open `http://<home assistant ip>:8000/image?product=Test&grocycode=test&due_date=DD:%202026-01-01`
   in a browser to see a preview without printing.

## Connecting Grocy

Point Grocy's label printer webhook at this add-on, in Grocy's `config.php`:

```php
Setting('LABEL_PRINTER_WEBHOOK', 'http://<address>:8000/print');
Setting('LABEL_PRINTER_RUN_SERVER', true);
Setting('LABEL_PRINTER_PARAMS', []);
Setting('LABEL_PRINTER_HOOK_JSON', false);
Setting('FEATURE_FLAG_LABEL_PRINTER', true);
```

For `<address>`, use either:

- the **Hostname** shown on this add-on's **Info** tab, if Grocy also runs as a Home Assistant add-on, or
- the Home Assistant machine's IP address, if Grocy runs somewhere else.

## Parameters

`/print` prints a label, `/image` returns the same label as a PNG. Both take GET or POST parameters:

| Name             | Use                                                   |
| ---------------- | ----------------------------------------------------- |
| `product`, `battery`, `chore`, `recipe` | the name, whichever is given   |
| `grocycode`      | the barcode                                           |
| `due_date`       | printed at the bottom right, as given (Grocy sends `DD: <date>`) |
| `purchased_date` | printed above the due date, after the purchased date prefix |
| `opened_date`    | printed above the due date, after the opened date prefix    |

Grocy's built-in webhook only sends `due_date`. To print purchased or opened dates, call `/print`
yourself, for example from a Home Assistant `rest_command` using values from the Grocy integration.

## Security

There's no authentication on this service, so don't expose port 8000 outside your network.
