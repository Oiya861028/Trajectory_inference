#!/usr/bin/env python
"""Build the progress deck for the E7-E10 trajectory-inference project."""

import copy

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt, Emu

OUT = "progress_trajectory_inference.pptx"

# Palette taken from the expression colormap used in every figure in this
# project, so the deck and the figures read as one piece of work.
INK    = RGBColor(0x1A, 0x1A, 0x1A)
DARK   = RGBColor(0x1C, 0x17, 0x19)
CHERRY = RGBColor(0x99, 0x00, 0x0D)
EMBER  = RGBColor(0xE3, 0x2F, 0x27)
PEACH  = RGBColor(0xFB, 0x8A, 0x6A)
SAND   = RGBColor(0xFC, 0xC9, 0xB4)
NAVY   = RGBColor(0x2F, 0x3C, 0x7E)
STEEL  = RGBColor(0x48, 0x78, 0xA6)
GREY   = RGBColor(0x6E, 0x6E, 0x6E)
MIDGREY= RGBColor(0x9A, 0x9A, 0x9A)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
TINT   = RGBColor(0xF7, 0xF2, 0xF1)
TINT2  = RGBColor(0xEE, 0xF1, 0xF6)

HEAD = "Cambria"
BODY = "Calibri"

W, H = 13.333, 7.5

# Layout grid. Content must stay inside a 0.5" margin, so the usable band is
# y = 2.00 .. 6.30, with a banner (if any) at 6.35 and a footer at 6.72.
TITLE_Y, TITLE_H = 0.50, 1.00
SUB_Y = 1.48
BODY_Y = 2.00
BAND_BOTTOM = 6.28
BANNER_Y = 6.26
FOOTER_Y = 6.72

# inches of advance per point of font size (average glyph, Calibri/Cambria) and
# line height as a multiple of font size
CHAR_W, LINE_H = 0.0085, 1.22


def est_lines(text, w, size):
    """Lines a string needs at this width and size, honouring explicit breaks."""
    per_line = max(1, int(w / (CHAR_W * size)))
    return sum(max(1, -(-len(seg) // per_line)) for seg in str(text).split("\n"))


def est_h(text, w, size):
    return est_lines(text, w, size) * size * LINE_H / 72


def new_deck():
    p = Presentation()
    p.slide_width = Inches(W)
    p.slide_height = Inches(H)
    return p


def blank(prs, dark=False):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    if dark:
        bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(W), Inches(H))
        bg.fill.solid(); bg.fill.fore_color.rgb = DARK
        bg.line.fill.background(); bg.shadow.inherit = False
    return s


def textbox(s, x, y, w, h, runs, size=16, color=INK, font=BODY, bold=False,
            italic=False, align=PP_ALIGN.LEFT, space_after=6, line=None,
            anchor=MSO_ANCHOR.TOP):
    """runs: str, or list of (text, {opts}) tuples, or list of str paragraphs."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    if isinstance(runs, str):
        runs = [runs]
    first = True
    for item in runs:
        para = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        para.alignment = align
        para.space_after = Pt(space_after)
        if line:
            para.line_spacing = line
        pieces = item if isinstance(item, list) else [(item, {})]
        for text, opt in pieces:
            r = para.add_run(); r.text = text
            f = r.font
            f.name = opt.get("font", font)
            f.size = Pt(opt.get("size", size))
            f.bold = opt.get("bold", bold)
            f.italic = opt.get("italic", italic)
            f.color.rgb = opt.get("color", color)
    return tb


def title(s, text, dark=False, sub=None, size=28):
    textbox(s, 0.7, TITLE_Y, W - 1.4, TITLE_H, text, size=size, font=HEAD,
            bold=True, color=WHITE if dark else INK, line=1.12)
    if sub:
        textbox(s, 0.7, SUB_Y, W - 1.4, 0.36, sub, size=13.5,
                color=MIDGREY if dark else GREY, italic=True)


def card(s, x, y, w, h, fill=TINT, line=None):
    c = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y),
                           Inches(w), Inches(h))
    c.adjustments[0] = 0.06
    c.fill.solid(); c.fill.fore_color.rgb = fill
    if line:
        c.line.color.rgb = line; c.line.width = Pt(1.25)
    else:
        c.line.fill.background()
    c.shadow.inherit = False
    return c


def stat(s, x, y, w, number, label, note=None, color=CHERRY, h=2.05, fill=TINT):
    card(s, x, y, w, h, fill=fill)
    tw = w - 0.44
    textbox(s, x + 0.22, y + 0.16, tw, 0.68, number, size=38, font=HEAD,
            bold=True, color=color, space_after=0)
    lh = est_h(label, tw, 12.5)
    textbox(s, x + 0.22, y + 0.90, tw, lh, label, size=12.5, bold=True,
            color=INK, space_after=0, line=1.15)
    if note:
        textbox(s, x + 0.22, y + 0.94 + lh, tw, est_h(note, tw, 10.5), note,
                size=10.5, color=GREY, line=1.15, space_after=0)


def bullets(s, x, y, w, items, size=14, gap=9, color=INK, marker=CHERRY):
    """Items: list of (bold_lead, rest) or plain strings. Dot marker, no stripes."""
    tw = w - 0.26
    cy = y
    for it in items:
        dot = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(cy + 0.07),
                                 Inches(0.1), Inches(0.1))
        dot.fill.solid(); dot.fill.fore_color.rgb = marker
        dot.line.fill.background(); dot.shadow.inherit = False
        text = it if isinstance(it, str) else "".join(it)
        if isinstance(it, tuple):
            runs = [[(it[0], {"bold": True}), (it[1], {})]]
        else:
            runs = [it]
        h = est_h(text, tw, size)
        tb = textbox(s, x + 0.26, cy, tw, h, runs, size=size, color=color,
                     line=1.18, space_after=0)
        tb.text_frame.word_wrap = True
        cy += h + gap / 72
    return cy


def table(s, x, y, w, rows, col_w=None, head_fill=DARK, size=11.5,
          head_size=11.5, cell_colors=None, row_h=0.32, head_h=0.36):
    nr, nc = len(rows), len(rows[0])
    shp = s.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(w),
                             Inches(head_h + row_h * (nr - 1)))
    tbl = shp.table
    tbl.first_row = True
    tbl.horz_banding = False
    if col_w:
        tot = sum(col_w)
        for i, cw in enumerate(col_w):
            tbl.columns[i].width = Emu(int(Inches(w) * cw / tot))
    tbl.rows[0].height = Inches(head_h)
    for r in range(1, nr):
        tbl.rows[r].height = Inches(row_h)
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            cell.margin_left = cell.margin_right = Inches(0.07)
            cell.margin_top = cell.margin_bottom = Inches(0.02)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = cell.text_frame; tf.word_wrap = True
            para = tf.paragraphs[0]
            para.alignment = PP_ALIGN.LEFT if c == 0 else PP_ALIGN.CENTER
            run = para.add_run(); run.text = str(val)
            f = run.font; f.name = BODY
            f.size = Pt(head_size if r == 0 else size)
            f.bold = (r == 0)
            f.color.rgb = WHITE if r == 0 else INK
            cell.fill.solid()
            if r == 0:
                cell.fill.fore_color.rgb = head_fill
            elif cell_colors and (r, c) in cell_colors:
                cell.fill.fore_color.rgb = cell_colors[(r, c)]
                f.bold = True
            else:
                cell.fill.fore_color.rgb = WHITE if r % 2 else TINT
    return tbl


def style_chart(ch, colors, legend=False, val_fmt='0.0', labels=True,
                label_pos=XL_LABEL_POSITION.OUTSIDE_END, font_size=10):
    ch.font.name = BODY
    ch.font.size = Pt(font_size)
    ch.has_title = False
    ch.has_legend = legend
    if legend:
        ch.legend.position = XL_LEGEND_POSITION.BOTTOM
        ch.legend.include_in_layout = False
        ch.legend.font.size = Pt(font_size)
    for i, plot_series in enumerate(ch.series):
        plot_series.format.fill.solid()
        plot_series.format.fill.fore_color.rgb = colors[i % len(colors)]
        plot_series.format.line.fill.background()
    plot = ch.plots[0]
    plot.gap_width = 60
    if labels:
        plot.has_data_labels = True
        dl = plot.data_labels
        dl.font.size = Pt(font_size - 0.5)
        dl.font.name = BODY
        dl.font.color.rgb = INK
        dl.number_format = val_fmt
        dl.number_format_is_linked = False
        try:
            dl.position = label_pos
        except Exception:
            pass
    try:
        ch.category_axis.format.line.color.rgb = MIDGREY
        ch.category_axis.tick_labels.font.size = Pt(font_size)
        ch.category_axis.tick_labels.font.color.rgb = INK
        ch.value_axis.has_major_gridlines = True
        ch.value_axis.major_gridlines.format.line.color.rgb = RGBColor(0xE4,0xE4,0xE4)
        ch.value_axis.major_gridlines.format.line.width = Pt(0.75)
        ch.value_axis.tick_labels.font.size = Pt(font_size)
        ch.value_axis.tick_labels.font.color.rgb = GREY
        ch.value_axis.format.line.fill.background()
    except Exception:
        pass
    return ch


def bar(s, x, y, w, h, cats, series, colors, horizontal=False, legend=False,
        val_fmt='0.0', font_size=10, gap=60, labels=True):
    cd = CategoryChartData()
    cd.categories = cats
    for name, vals in series:
        cd.add_series(name, vals)
    kind = XL_CHART_TYPE.BAR_CLUSTERED if horizontal else XL_CHART_TYPE.COLUMN_CLUSTERED
    gf = s.shapes.add_chart(kind, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    ch = gf.chart
    style_chart(ch, colors, legend=legend, val_fmt=val_fmt, labels=labels,
                label_pos=XL_LABEL_POSITION.OUTSIDE_END, font_size=font_size)
    ch.plots[0].gap_width = gap
    return ch


def footer(s, text, dark=False):
    textbox(s, 0.7, FOOTER_Y, W - 1.4, 0.26, text, size=9.5,
            color=MIDGREY if dark else GREY, italic=True)


def banner(s, y=None, text="", color=CHERRY, h=None, tcolor=WHITE, size=13):
    """A full-width conclusion block. Not a decorative stripe: it carries text."""
    y = BANNER_Y if y is None else y
    inner = W - 1.9
    h = (est_h(text, inner, size) + 0.26) if h is None else h
    c = card(s, 0.7, y, W - 1.4, h, fill=color)
    textbox(s, 0.95, y + 0.13, inner, h - 0.2, text, size=size, bold=True,
            color=tcolor, space_after=0)
    return c
