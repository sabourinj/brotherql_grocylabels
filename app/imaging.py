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

def createLabelImage(labelSize : tuple, endlessMargin : int, text : str, textFont : ImageFont, textFontSize : int, textMaxLines : int, barcode : Image, dates : list, dateFont : ImageFont):
    (width, height) = labelSize
    # default line spacing used by multiline_text, doesn't seem to have an effect if changed though but we need to take into account
    lineSpacing = 4
    # margin to use for label
    marginTop = 0
    marginBottom = 0

    # date lines are stacked in the bottom right corner, the last one sits at the very bottom
    dates = [d for d in dates if d]
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
            (_, _, _, ddBottom) = dateFont.getbbox(dates[-1])
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
        (_, _, _, ddBottom) = dateFont.getbbox(dates[-1])
        bottomLineY = label.size[1] - ddBottom - marginBottom
        for i, dateText in enumerate(reversed(dates)):
            (_, ddTop, ddRight, _) = dateFont.getbbox(dateText)
            y = bottomLineY - i * dateLinePitch
            datePositions.append((dateText, [label.size[0] - ddRight, y]))
            datesTop = min(datesTop, y + ddTop)

    nameMaxWidth = width - barcode.size[0]
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

    for (dateText, position) in datePositions:
        draw.text(
            position,
            dateText,
            fill = ImageColor.getrgb("#000"),
            font = dateFont
        )

    return label

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
