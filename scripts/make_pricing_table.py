from PIL import Image, ImageDraw, ImageFont

W, H = 1600, 1040
BG = (255, 255, 255)
HEADER_BG = (26, 28, 33)
HEADER_FG = (255, 255, 255)
ROW_BG_ALT = (245, 246, 248)
ROW_BG = (255, 255, 255)
TEXT = (26, 28, 33)
SUBTEXT = (110, 115, 122)
BORDER = (225, 227, 230)
ACCENT = (204, 118, 84)  # Anthropic-ish terracotta accent

FONT_DIR = r"C:\Windows\Fonts"
f_title = ImageFont.truetype(FONT_DIR + r"\segoeuib.ttf", 46)
f_subtitle = ImageFont.truetype(FONT_DIR + r"\segoeui.ttf", 26)
f_head = ImageFont.truetype(FONT_DIR + r"\segoeuisb.ttf", 28) if False else ImageFont.truetype(FONT_DIR + r"\seguisb.ttf", 28)
f_model = ImageFont.truetype(FONT_DIR + r"\segoeuib.ttf", 30)
f_cell = ImageFont.truetype(FONT_DIR + r"\segoeui.ttf", 30)
f_note = ImageFont.truetype(FONT_DIR + r"\segoeui.ttf", 22)
f_footer = ImageFont.truetype(FONT_DIR + r"\segoeui.ttf", 20)

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

# Title
margin = 70
d.text((margin, 55), "Prezzi API — principali modelli LLM", font=f_title, fill=TEXT)
d.text((margin, 112), "$ per milione di token, input / output — agosto 2026", font=f_subtitle, fill=SUBTEXT)

# Table geometry
table_top = 190
table_left = margin
table_right = W - margin
col_model_w = 480
col_price_w = 300
col_note_w = (table_right - table_left) - col_model_w - 2 * col_price_w

col_x = [table_left, table_left + col_model_w,
         table_left + col_model_w + col_price_w,
         table_left + col_model_w + 2 * col_price_w,
         table_right]

header_h = 74
row_h = 110

rows = [
    ("Claude Sonnet 5", "Anthropic", "$2", "$10", "prezzo intro reso permanente"),
    ("GPT-5.6 Sol", "OpenAI", "$5", "$30", "flagship, invariato"),
    ("GPT-5.6 Terra", "OpenAI", "$2", "$12", "-20% dal 30 luglio"),
    ("GPT-5.6 Luna", "OpenAI", "$0,20", "$1,20", "-80% dal 30 luglio"),
    ("Gemini 3.7 Flash", "Google", "$0,75", "$3,75", "prezzo intro fino al 31/12/2026"),
    ("DeepSeek V3.2", "DeepSeek", "$0,28", "$0,42", "pressione dei modelli cinesi"),
]

# Header row
y0 = table_top
y1 = y0 + header_h
d.rectangle([table_left, y0, table_right, y1], fill=HEADER_BG)
d.text((col_x[0] + 24, y0 + 22), "Modello", font=f_head, fill=HEADER_FG)
d.text((col_x[1] + 24, y0 + 22), "Input", font=f_head, fill=HEADER_FG)
d.text((col_x[2] + 24, y0 + 22), "Output", font=f_head, fill=HEADER_FG)
d.text((col_x[3] + 24, y0 + 22), "Note", font=f_head, fill=HEADER_FG)

y = y1
for i, (name, vendor, inp, out, note) in enumerate(rows):
    ry0, ry1 = y, y + row_h
    bg = ROW_BG_ALT if i % 2 == 1 else ROW_BG
    d.rectangle([table_left, ry0, table_right, ry1], fill=bg)

    is_highlight = name.startswith("Claude")
    if is_highlight:
        d.rectangle([table_left, ry0, table_left + 8, ry1], fill=ACCENT)

    # Model + vendor
    d.text((col_x[0] + 24, ry0 + 24), name, font=f_model, fill=TEXT)
    d.text((col_x[0] + 24, ry0 + 62), vendor, font=f_note, fill=SUBTEXT)

    # Prices
    d.text((col_x[1] + 24, ry0 + 36), inp, font=f_cell, fill=TEXT)
    d.text((col_x[2] + 24, ry0 + 36), out, font=f_cell, fill=TEXT)

    # Note
    d.text((col_x[3] + 24, ry0 + 40), note, font=f_note, fill=SUBTEXT)

    d.line([table_left, ry1, table_right, ry1], fill=BORDER, width=1)
    y = ry1

# Outer border
d.rectangle([table_left, table_top, table_right, y], outline=BORDER, width=2)

# Footer
d.text((margin, y + 30), "Fonti: pagine prezzi ufficiali Anthropic, OpenAI, Google, DeepSeek — dati ad agosto 2026",
        font=f_footer, fill=SUBTEXT)

out_path = r"C:\Users\afalc\Desktop\Linkedin\20260821-anthropic-cancella-aumento-sonnet5.png"
img.save(out_path)
print(out_path)
