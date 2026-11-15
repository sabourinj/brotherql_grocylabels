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

Point Grocy's label printer webhook straight at this add-on, in Grocy's `config.php`:

```php
Setting('LABEL_PRINTER_WEBHOOK', 'http://<address>:8000/print');
Setting('LABEL_PRINTER_RUN_SERVER', true);
Setting('LABEL_PRINTER_PARAMS', []);
Setting('LABEL_PRINTER_HOOK_JSON', true);
Setting('FEATURE_FLAG_LABEL_PRINTER', true);
```

For `<address>`, use either:

- the add-on's hostname, if Grocy also runs as a Home Assistant add-on. It's `<repository hash>-brotherql-grocylabels`,
  shown as **Hostname** on this add-on's **Info** tab, or
- the Home Assistant machine's IP address, which works from anywhere on your network.

Grocy sends the stock entry with each stock label, so the purchased and opened dates are printed without
any extra setup. `LABEL_PRINTER_HOOK_JSON` can be `true` or `false`, both work.

### Opened dates on labels reprinted when opening

If a product has **Auto reprint stock entry label** turned on, Grocy reprints its label when you open it.
Grocy sends that webhook just *before* it saves the item as opened, so on its own the label has no opened date.

To fix that, set **Grocy URL** and **Grocy API key** (create one in Grocy under the user menu, **Manage API keys**).
The add-on then replies to Grocy straight away, waits **Grocy lookup delay** seconds, reads the stock entry
from the Grocy API and prints. You can use the same URL and API key as Home Assistant's Grocy integration.
If the lookup fails the label is printed from the webhook data and the error is in the add-on log.

## Parameters

`/print` prints a label, `/image` returns the same label as a PNG. Both take GET or POST parameters:

| Name             | Use                                                   |
| ---------------- | ----------------------------------------------------- |
| `product`, `battery`, `chore`, `recipe` | the name, whichever is given   |
| `grocycode`      | the barcode                                           |
| `due_date`       | printed at the bottom right, as given (Grocy sends `DD: <date>`) |
| `purchased_date` | printed above the due date, after the purchased date prefix |
| `opened_date`    | printed above the due date, after the opened date prefix    |
| `stock_entry`    | sent by Grocy, its `purchased_date` and `opened_date` are used when the two above aren't given |

Parameters can also be sent as a JSON body.

## Security

There's no authentication on this service, so don't expose port 8000 outside your network.
