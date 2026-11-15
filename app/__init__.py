import json
import re
from datetime import date
import threading
import time
from io import BytesIO
from os import path, getenv, environ
from flask import Flask, Response, request
from PIL import Image, ImageFont
from dotenv import load_dotenv
from brother_ql.labels import ALL_LABELS, Color
from brother_ql import BrotherQLRaster, create_label
from brother_ql.backends import guess_backend, backend_factory
from app.imaging import createBarcode, createLabelImage
from app import grocy

load_dotenv()

# When running as a Home Assistant add-on the settings come from the add-on options,
# option names are the lower case versions of the environment variables below.
# Environment variables still take priority if both are set.
OPTIONS_FILE = getenv("OPTIONS_FILE", "/data/options.json")
if path.isfile(OPTIONS_FILE):
    with open(OPTIONS_FILE, encoding="utf-8") as f:
        for (key, value) in json.load(f).items():
            environ.setdefault(key.upper(), str(value))
    # blank optional options are left out of the file, which means print the date with no prefix
    environ.setdefault("PURCHASED_DATE_PREFIX", "")
    environ.setdefault("OPENED_DATE_PREFIX", "")
    environ.setdefault("DUE_DATE_PREFIX", "")

LABEL_SIZE = getenv("LABEL_SIZE", "62x29")
PRINTER_MODEL = getenv("PRINTER_MODEL", "QL-500")
PRINTER_PATH = getenv("PRINTER_PATH", "file:///dev/usb/lp1")
BARCODE_FORMAT = getenv("BARCODE_FORMAT", "Datamatrix")
NAME_FONT = getenv("NAME_FONT", "NotoSerif-Regular.ttf")
NAME_FONT_SIZE = int(getenv("NAME_FONT_SIZE", "48"))
NAME_MAX_LINES = int(getenv("NAME_MAX_LINES", "4"))
DUE_DATE_FONT =  getenv("DUE_DATE_FONT", "NotoSerif-Regular.ttf")
DUE_DATE_FONT_SIZE = int(getenv("DUE_DATE_FONT_SIZE", "30"))
ENDLESS_MARGIN = int(getenv("ENDLESS_MARGIN", "10"))
# about 2mm at 300dpi
RIGHT_MARGIN = int(getenv("RIGHT_MARGIN", "24"))
BOLD_DATES = getenv("BOLD_DATES", "true").strip().lower() in ["1", "true", "yes", "on"]
PURCHASED_DATE_PREFIX = getenv("PURCHASED_DATE_PREFIX", "Purchased:").strip()
OPENED_DATE_PREFIX = getenv("OPENED_DATE_PREFIX", "Opened:").strip()
# unset means print due_date exactly as given (Grocy sends "DD: <date>")
DUE_DATE_PREFIX = getenv("DUE_DATE_PREFIX")
if DUE_DATE_PREFIX is not None:
    DUE_DATE_PREFIX = DUE_DATE_PREFIX.strip()
# optional, lets labels use the stock entry as Grocy has it after the webhook (see README)
# how dates are printed, one of DATE_FORMATS or a strftime pattern
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DATE_FORMATS = {
    "YYYY-MM-DD": lambda d: d.strftime("%Y-%m-%d"),
    "MM/DD/YYYY": lambda d: d.strftime("%m/%d/%Y"),
    "DD/MM/YYYY": lambda d: d.strftime("%d/%m/%Y"),
    "MM/DD/YY": lambda d: d.strftime("%m/%d/%y"),
    "DD.MM.YYYY": lambda d: d.strftime("%d.%m.%Y"),
    "Mon D, YYYY": lambda d: "%s %d, %d" % (MONTHS[d.month - 1], d.day, d.year),
    "D Mon YYYY": lambda d: "%d %s %d" % (d.day, MONTHS[d.month - 1], d.year),
}
DATE_FORMAT = getenv("DATE_FORMAT", "YYYY-MM-DD").strip() or "YYYY-MM-DD"
formatDateValue = DATE_FORMATS.get(DATE_FORMAT, lambda d: d.strftime(DATE_FORMAT))
GROCY_URL = getenv("GROCY_URL", "").strip()
GROCY_API_KEY = getenv("GROCY_API_KEY", "").strip()
GROCY_LOOKUP_DELAY = float(getenv("GROCY_LOOKUP_DELAY", "3"))
GROCY_LOOKUP = bool(GROCY_URL and GROCY_API_KEY)

selected_backend = guess_backend(PRINTER_PATH)
BACKEND_CLASS = backend_factory(selected_backend)['backend_class']

label_spec = next(x for x in ALL_LABELS if x.identifier == LABEL_SIZE)

thisDir = path.dirname(path.abspath(__file__))
nameFont = ImageFont.truetype(path.join(thisDir, "..", "fonts", NAME_FONT), NAME_FONT_SIZE)
ddFont = ImageFont.truetype(path.join(thisDir, "..", "fonts", DUE_DATE_FONT), DUE_DATE_FONT_SIZE)

app = Flask(__name__)

@app.route("/")
def home_route():
    return "Label %s, %s"%(label_spec.identifier, label_spec.name)

def get_params():
    if request.is_json:
        source = request.get_json(silent = True) or {}
    else:
        source = request.form if request.method == "POST" else request.args

    name = ""
    for key in ["product", "battery", "chore", "recipe"]:
        if key in source:
            name = grocy.text(source[key])

    return {
        "name": name,
        "barcode": grocy.text(source.get("grocycode")),
        "dueDate": grocy.text(source.get("due_date")),
        # given directly, these win over anything from Grocy
        "purchasedDate": grocy.text(source.get("purchased_date")),
        "openedDate": grocy.text(source.get("opened_date")),
        # sent by Grocy's own stock label webhook
        "stockEntry": grocy.stockEntryFromRequest(source),
    }

def lookupStockEntry(params):
    """Fresh copy of the stock entry from the Grocy API, or None if not configured / not possible."""
    if not GROCY_LOOKUP or not grocy.canLookup(params["stockEntry"], params["barcode"]):
        return None
    try:
        return grocy.fetchStockEntry(GROCY_URL, GROCY_API_KEY, params["stockEntry"], params["barcode"])
    except Exception as e:
        app.logger.warning("Grocy lookup failed, using the webhook data instead: %s", e)
        return None

DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")

def formatDate(text):
    """Rewrite any YYYY-MM-DD dates in the text in DATE_FORMAT."""
    def replace(match):
        try:
            return formatDateValue(date.fromisoformat(match.group(0)))
        except ValueError:
            return match.group(0)
    return DATE_PATTERN.sub(replace, text)

def formatDueDate(dueDate, entry):
    """
    The due date line as (prefix, date).
    Swaps Grocy's "DD: <date>" prefix for DUE_DATE_PREFIX, when it's set.
    """
    if not dueDate:
        return None
    match = DATE_PATTERN.search(dueDate)
    if DUE_DATE_PREFIX is None:
        # print it as given, only the date part is reformatted (and bold)
        if not match:
            return (dueDate, "")
        return (dueDate[:match.start()].strip(), formatDate(dueDate[match.start():]))
    # no date in the text (e.g. just "DD"), fall back to the stock entry's due date
    day = match.group(0) if match else grocy.text(entry.get("best_before_date"))[:10]
    if not day:
        # not something we understand, leave it alone
        return (dueDate, "")
    return (DUE_DATE_PREFIX, formatDate(day))

def createLabel(params, freshEntry = None):
    entry = freshEntry or params["stockEntry"]
    purchasedDate = formatDate(params["purchasedDate"] or grocy.text(entry.get("purchased_date"))[:10])
    openedDate = formatDate(params["openedDate"] or grocy.text(entry.get("opened_date"))[:10])

    # top to bottom order on the label, due date stays at the very bottom
    dates = []
    if purchasedDate:
        dates.append((PURCHASED_DATE_PREFIX, purchasedDate))
    if openedDate:
        dates.append((OPENED_DATE_PREFIX, openedDate))
    dueDate = formatDueDate(params["dueDate"], entry)
    if dueDate:
        dates.append(dueDate)

    return createLabelImage(label_spec.dots_printable, ENDLESS_MARGIN, params["name"], nameFont, NAME_FONT_SIZE, NAME_MAX_LINES, createBarcode(params["barcode"], BARCODE_FORMAT), dates, ddFont, RIGHT_MARGIN, BOLD_DATES)

# one label at a time, the delayed prints run on their own threads
printLock = threading.Lock()

def printLabel(params, freshEntry = None):
    label = createLabel(params, freshEntry)
    with printLock:
        sendToPrinter(label)

def delayedPrint(params):
    # Grocy sends the webhook before it saves the stock entry (e.g. when opening a product)
    # and waits for the reply, so give it time to finish before looking the entry up
    try:
        time.sleep(GROCY_LOOKUP_DELAY)
        printLabel(params, lookupStockEntry(params))
    except Exception:
        app.logger.exception("Printing label failed")

@app.route("/print", methods=["GET", "POST"])
def print_route():
    params = get_params()

    if GROCY_LOOKUP and grocy.canLookup(params["stockEntry"], params["barcode"]):
        # reply straight away, Grocy only waits 2 seconds for webhooks
        threading.Thread(target = delayedPrint, args = (params,), daemon = True).start()
        return Response("OK", 200)

    printLabel(params)
    return Response("OK", 200)

@app.route("/image", methods=["GET", "POST"])
def image_route():
    params = get_params()

    img = createLabel(params, lookupStockEntry(params))
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return Response(buf, 200, mimetype="image/png")

def sendToPrinter(image : Image):
    bql = BrotherQLRaster(PRINTER_MODEL)

    redLabel = label_spec.color == Color.BLACK_RED_WHITE

    create_label(
        bql,
        image,
        LABEL_SIZE,
        red=redLabel
    )

    be = BACKEND_CLASS(PRINTER_PATH)
    be.write(bql.data)
    del be
