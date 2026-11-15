import json
from io import BytesIO
from os import path, getenv, environ
from flask import Flask, Response, request
from PIL import Image, ImageFont
from dotenv import load_dotenv
from brother_ql.labels import ALL_LABELS, Color
from brother_ql import BrotherQLRaster, create_label
from brother_ql.backends import guess_backend, backend_factory
from app.imaging import createBarcode, createLabelImage

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
PURCHASED_DATE_PREFIX = getenv("PURCHASED_DATE_PREFIX", "Purchased:").strip()
OPENED_DATE_PREFIX = getenv("OPENED_DATE_PREFIX", "Opened:").strip()

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
    source = request.form if request.method == "POST" else request.args

    name = ""
    if 'product' in source:
        name = source['product']
    if 'battery' in request.form:
        name = source['battery']
    if 'chore' in request.form:
        name = source['chore']
    if 'recipe' in request.form:
        name = source['recipe']
    
    barcode = source['grocycode'] if 'grocycode' in source else ''
    dueDate = source['due_date'] if 'due_date' in source else ''
    purchasedDate = source['purchased_date'] if 'purchased_date' in source else ''
    openedDate = source['opened_date'] if 'opened_date' in source else ''

    # top to bottom order on the label, due date stays at the very bottom
    dates = []
    if purchasedDate:
        dates.append(' '.join(filter(None, [PURCHASED_DATE_PREFIX, purchasedDate])))
    if openedDate:
        dates.append(' '.join(filter(None, [OPENED_DATE_PREFIX, openedDate])))
    if dueDate:
        dates.append(dueDate)

    return (name, barcode, dates)

@app.route("/print", methods=["GET", "POST"])
def print_route():
    (name, barcode, dates) = get_params();

    label = createLabelImage(label_spec.dots_printable, ENDLESS_MARGIN, name, nameFont, NAME_FONT_SIZE, NAME_MAX_LINES, createBarcode(barcode, BARCODE_FORMAT), dates, ddFont)

    buf = BytesIO()
    label.save(buf, format="PNG")
    buf.seek(0)
    sendToPrinter(label)

    return Response("OK", 200)

@app.route("/image")
def test():
    (name, barcode, dates) = get_params();

    img = createLabelImage(label_spec.dots_printable, ENDLESS_MARGIN, name, nameFont, NAME_FONT_SIZE, NAME_MAX_LINES, createBarcode(barcode, BARCODE_FORMAT), dates, ddFont)
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
