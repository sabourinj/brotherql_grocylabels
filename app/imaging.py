from pylibdmtx.pylibdmtx import encode
import qrcode
from PIL import Image, ImageColor, ImageFont, ImageDraw

def createDatamatrix(text: str):
    encoded = encode(text.encode('utf8'), "Ascii", "ShapeAuto")
    barcode = Image.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)
    return barcode

def createQRCode(text: str):
    return qrcode.make(text, box_size = 1)

def createBarcode(text: str, type: str):
    match type:
        case "QRCode":
            return createQRCode(text)
        case "DataMatrix":
            return createDatamatrix(text)
        case _:
            return createDatamatrix(text)

def createLabelImage(labelSize : tuple, endlessMargin : int, text : str, textFont : ImageFont, textFontSize : int, textMaxLines : int, barcode : Image, dates : list, dateFont : ImageFont, rightMargin : int = 0, boldDates : bool = False):
    (width, height) = labelSize
    # default line spacing used by multiline_text, doesn't seem to have an effect if changed though but we need to take into account
    lineSpacing = 4
    # margin to use for label
    marginTop = 0
    marginBottom = 0

    # date lines are stacked in the bottom right corner, the last one sits at the very bottom
    # each is a (prefix, date) pair or plain text, the date part can be drawn bold
    dates = [d if isinstance(d, tuple) else (d, "") for d in dates]
    dates = [(p or "", v or "") for (p, v) in dates if p or v]
    # there's no bold font included, outlining the text in the same colour thickens it instead
    boldWidth = max(1, round(dateFont.size / 30)) if boldDates else 0
    # distance between the baselines of stacked date lines
    dateLinePitch = dateFont.size + lineSpacing
    # height taken by the date lines above the bottom one
    datesExtraHeight = dateLinePitch * (len(dates) - 1) if dates else 0

    # for endless labels with a height of zero
    if height == 0:
        # height should be text size + spacing x max lines + margin x 2
        height = (textFontSize + lineSpacing) * textMaxLines + endlessMargin * 2
        # negate the empty space above the text
        (_, tTop, _, _) = textFont.getbbox("testing")
        marginTop = endlessMargin - tTop
        # regular bottom margin
        marginBottom = endlessMargin
        # make space for the dates
        if dates:
            (_, _, _, ddBottom) = dateLineBox(dates[-1], dateFont, boldWidth)
            height += ddBottom + datesExtraHeight

    # increase the size of the barcode if space permits
    if (barcode.size[1] * 8) < height:
        barcode = barcode.resize((barcode.size[0] * 8, barcode.size[1] * 8), Image.Resampling.NEAREST)
    if (barcode.size[1] * 6) < height:
        barcode = barcode.resize((barcode.size[0] * 6, barcode.size[1] * 6), Image.Resampling.NEAREST)
    if (barcode.size[1] * 4) < height:
        barcode = barcode.resize((barcode.size[0] * 4, barcode.size[1] * 4), Image.Resampling.NEAREST)
    if (barcode.size[1] * 2) < height:
        barcode = barcode.resize((barcode.size[0] * 2, barcode.size[1] * 2), Image.Resampling.NEAREST)
    
    label = Image.new("RGB", (width, height), ImageColor.getrgb("#FFF"))
    # vertically align barcode (ignoring margin)
    barcode_padding = [0, (int)((label.size[1] / 2) - (barcode.size[1] / 2))]
    label.paste(barcode, barcode_padding)
    
    draw = ImageDraw.Draw(label)

    # work out where each date line goes, bottom line first, so the name can avoid them
    datePositions = []
    datesTop = label.size[1]
    if dates:
        (_, _, _, ddBottom) = dateLineBox(dates[-1], dateFont, boldWidth)
        bottomLineY = label.size[1] - ddBottom - marginBottom
        for i, line in enumerate(reversed(dates)):
            (_, ddTop, ddRight, _) = dateLineBox(line, dateFont, boldWidth)
            y = bottomLineY - i * dateLinePitch
            datePositions.append((line, [label.size[0] - rightMargin - ddRight, y]))
            datesTop = min(datesTop, y + ddTop)

    # keep text clear of the right edge, printers don't line up exactly with die-cut labels
    nameMaxWidth = width - barcode.size[0] - rightMargin
    # use fewer name lines if the full amount would run into the dates
    nameLines = textMaxLines
    while True:
        (nameText, nameTextWidth) = wrapText(text, textFont, nameMaxWidth, nameLines)
        if not dates or nameLines <= 1:
            break
        (_, _, _, nameBottom) = draw.multiline_textbbox((0, marginTop), nameText, font = textFont, spacing = lineSpacing)
        if nameBottom + lineSpacing <= datesTop:
            break
        nameLines -= 1
    nameLeftMargin = (nameMaxWidth - nameTextWidth) / 2

    draw.multiline_text(
        [barcode.size[0] + nameLeftMargin, marginTop],
        nameText,
        fill = ImageColor.getrgb("#000"),
        font = textFont,
        align = "center",
        spacing = lineSpacing
    )

    black = ImageColor.getrgb("#000")
    for ((prefix, value), (x, y)) in datePositions:
        prefixText = datePrefixText(prefix, value)
        if prefixText:
            draw.text([x, y], prefixText, fill = black, font = dateFont)
        if value:
            draw.text([x + dateFont.getlength(prefixText), y], value, fill = black, font = dateFont, stroke_width = boldWidth, stroke_fill = black)

    return label

def datePrefixText(prefix : str, value : str):
    return prefix + " " if prefix and value else prefix

def dateLineBox(line : tuple, font : ImageFont, boldWidth : int):
    """Bounding box of a (prefix, date) line drawn from the origin, the date part can be outlined to make it bold."""
    (prefix, value) = line
    prefixText = datePrefixText(prefix, value)
    boxes = []
    if prefixText:
        boxes.append(font.getbbox(prefixText))
    if value:
        offset = font.getlength(prefixText)
        (left, top, right, bottom) = font.getbbox(value, stroke_width = boldWidth)
        boxes.append((left + offset, top, right + offset, bottom))
    return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))

def wrapText(text : str, font : ImageFont, maxWidth : int, maxLines : int):
    parts = text.split(" ")
    parts.reverse()
    lines = []
    longestLine = 0

    # break words that are too long for a single line
    trimmedParts = []
    for part in parts:
        if font.getlength(part) >= maxWidth:
            # just chop in half, nothing fancy
            midpoint = int(len(part) / 2);
            trimmedParts.append(part[midpoint:])
            trimmedParts.append(part[0:midpoint] + '-')
        else:
            trimmedParts.append(part)

    parts = trimmedParts
    
    # create lines from input
    while len(parts) > 0:
        nextLine = []
        
        # create this line adding words while the next word fits
        while len(parts) > 0:
            nextPart = parts.pop()

            if font.getlength(' '.join(nextLine) + ' ' + nextPart) < maxWidth:
                nextLine.append(nextPart)
            else:
                # didn't fit so put it back on the stack
                parts.append(nextPart)
                break
        
        # finished with the line
        if len(nextLine) > 0:
            lines.append(' '.join(nextLine))
            lineLength = font.getlength(' '.join(nextLine))
            if lineLength > longestLine:
                longestLine = lineLength
    
    if len(lines) > maxLines:
        lines = lines[0:maxLines]
        lines[-1] += '...'
        lineLength = font.getlength(lines[-1])
        if lineLength > longestLine:
            longestLine = lineLength

    return ('\n'.join(lines), longestLine)
