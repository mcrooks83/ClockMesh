#!/usr/bin/env python3
"""Create the ClockMesh Developer Tutorial in ReportLab.

This is a clean-room reconstruction of the ReportLab generator used to produce
ClockMesh_Developer_Tutorial.pdf. The original Python script was not retained.
The layout, typography, text and vector examples follow the finished document,
though the regenerated PDF is not guaranteed to be pixel-identical.

Requirements:
    python -m pip install reportlab

Usage:
    python clockmesh_reportlab_source.py
    python clockmesh_reportlab_source.py --output My_ClockMesh_Tutorial.pdf

Optional system fonts (never bundled or distributed):
    Lato Regular/Bold/Heavy, DejaVu Sans Mono
If those are unavailable, the program uses built-in PDF fonts instead.

Authoring architecture:
    - ReportLab canvas, in A4 portrait
    - Top-origin coordinates to simplify precise editorial page layout
    - One coherent typography/colour/spacing system
    - Reusable panels, tables, paragraphs, and code blocks
    - 100% vector function-flow diagram and zero-baseline graph
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Iterable, Sequence

from reportlab.lib.colors import HexColor, Color
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


@dataclass(frozen=True)

class Palette:
    NAVY: str = '#071D28'
    NAVY2: str = '#2A2E4D'
    TEAL: str = '#19D3EB'
    CORAL: str = '#545DF7' # this is the n3 blue / purple. 
    N3_BLUE:    str = '#545DF7'
    N3_ACCENT: str = '#616CAB'
    PALE_TEAL: str = '#E6EFF4'
    PALE_CORAL: str = '#E9EAFE'
    OFF_WHITE: str = '#F6F6F6'
    PANEL: str = '#F0F3F6'
    LINE: str = '#D4DFE5'
    MUTED: str = '#616CAB'
    WHITE: str = '#FFFFFF'
    LIGHT_INK: str = '#E6EFF4'



C = Palette()
W, H = A4
M = 48.0
CW = W - 2 * M


def install_fonts() -> dict[str, str]:
    """Use installed fonts, never require shipping font files."""
    candidates = {
        'LatoBody': [
            '/usr/share/fonts/truetype/lato/Lato-Regular.ttf',
            '/usr/local/share/fonts/Lato-Regular.ttf',
        ],
        'LatoBold': [
            '/usr/share/fonts/truetype/lato/Lato-Bold.ttf',
            '/usr/local/share/fonts/Lato-Bold.ttf',
        ],
        'LatoHeavy': [
            '/usr/share/fonts/truetype/lato/Lato-Heavy.ttf',
            '/usr/share/fonts/truetype/lato/Lato-Black.ttf',
        ],
        'CodeMono': [
            '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
        ],
    }
    fallbacks = {
        'body': 'Helvetica',
        'bold': 'Helvetica-Bold',
        'heavy': 'Helvetica-Bold',
        'mono': 'Courier',
    }
    output = dict(fallbacks)
    role = {'LatoBody': 'body', 'LatoBold': 'bold',
            'LatoHeavy': 'heavy', 'CodeMono': 'mono'}
    for name, paths in candidates.items():
        existing = next((p for p in paths if Path(p).is_file()), None)
        if existing:
            pdfmetrics.registerFont(TTFont(name, existing))
            output[role[name]] = name
    # Inline markup in Paragraph (<b>) is only used when paired faces exist.
    if output['body'] != 'Helvetica' and output['bold'] != 'Helvetica-Bold':
        pdfmetrics.registerFontFamily(output['body'], normal=output['body'],
                                      bold=output['bold'], italic=output['body'],
                                      boldItalic=output['bold'])
    return output


class Tutorial:
    """PDF drawing helpers, with all vertical positions measured from page top."""

    def __init__(self, output_path: str) -> None:
        self.font = install_fonts()
        self.pdf = canvas.Canvas(output_path, pagesize=A4, pageCompression=1)
        self.pdf.setTitle('ClockMesh | Developer Tutorial')
        self.pdf.setSubject('An API-first guide to affine relationships between clocks')
        self.pdf.setAuthor('Rightstep: Nexus N3')

    @staticmethod
    def col(hex_value: str):
        return HexColor(hex_value)

    @staticmethod
    def y(top: float) -> float:
        return H - top

    def box(self, x: float, top: float, width: float, height: float,
            fill: str, radius: float = 8, stroke: str | None = None,
            stroke_width: float = 0.6) -> None:
        p = self.pdf
        p.saveState()
        p.setFillColor(self.col(fill))
        if stroke:
            p.setStrokeColor(self.col(stroke))
            p.setLineWidth(stroke_width)
        p.roundRect(x, self.y(top + height), width, height, radius,
                    fill=1, stroke=int(bool(stroke)))
        p.restoreState()

    def bar(self, x: float, top: float, width: float, height: float,
            fill: str) -> None:
        self.pdf.setFillColor(self.col(fill))
        self.pdf.rect(x, self.y(top + height), width, height, stroke=0, fill=1)

    def rule(self, x1: float, top1: float, x2: float, top2: float,
             colour: str = C.LINE, thickness: float = 0.65,
             dash: Sequence[float] | None = None) -> None:
        p = self.pdf
        p.saveState()
        p.setStrokeColor(self.col(colour))
        p.setLineWidth(thickness)
        if dash:
            p.setDash(dash)
        p.line(x1, self.y(top1), x2, self.y(top2))
        p.restoreState()

    def text(self, value: str, x: float, top: float, size: float = 10,
             font: str = 'body', color: str = C.NAVY,
             align: str = 'left', tracking: float = 0) -> None:
        p = self.pdf
        face = self.font[font]
        p.saveState()
        p.setFillColor(self.col(color))
        p.setFont(face, size)
        if tracking:
            # canvas.drawString does not have a char spacing parameter.
            obj = p.beginText()
            obj.setFont(face, size)
            obj.setCharSpace(tracking)
            obj.setTextOrigin(x, self.y(top + size))
            obj.textOut(value)
            p.drawText(obj)
        else:
            baseline = self.y(top + size)
            if align == 'right':
                p.drawRightString(x, baseline, value)
            elif align == 'center':
                p.drawCentredString(x, baseline, value)
            else:
                p.drawString(x, baseline, value)
        p.restoreState()

    def para(self, value: str, x: float, top: float, width: float,
             size: float = 9.0, leading: float | None = None,
             font: str = 'body', color: str = C.NAVY,
             markup: bool = False) -> float:
        """Draw wrapped text and return occupied height."""
        if not markup:
            value = escape(value).replace('\n', '<br/>')
        lineheight = leading if leading is not None else size * 1.46
        style = ParagraphStyle(
            '_inline', fontName=self.font[font], fontSize=size,
            leading=lineheight, textColor=self.col(color), alignment=TA_LEFT,
            spaceAfter=0, spaceBefore=0, allowWidows=0, allowOrphans=0,
        )
        p = Paragraph(value, style)
        _, height = p.wrap(width, H)
        p.drawOn(self.pdf, x, self.y(top + height))
        return height

    def tag(self, text: str, top: float, x: float = M,
            color: str = C.N3_BLUE, size: float = 8.2) -> None:
        self.text(text, x, top, size=size, font='bold', color=color,
                  tracking=0.25)

    def callout(self, top: float, title: str, content: str,
                height: float, fill: str = C.N3_BLUE,
                accent: str = C.N3_BLUE, x: float = M,
                width: float = CW, text_size: float = 8.6) -> None:
        self.box(x, top, width, height, fill, radius=7)
        self.bar(x, top, 3.4, height, accent)
        self.text(title.upper(), x + 13, top + 10, size=7.2,
                  font='bold', color=accent, tracking=0.32)
        self.para(content, x + 13, top + 26, width - 26,
                  size=text_size, leading=text_size * 1.39)

    def code(self, top: float, lines: str | Sequence[str],
             height: float | None = None, x: float = M,
             width: float = CW, size: float = 8.3,
             lineheight: float = 12.3, label: str | None = None,
             dark: bool = True) -> float:
        """Draw a code block with source-preserving indentation.

        Lines are never syntax-highlighted by an external dependency; comments
        are shown in subdued teal to stay legible against navy.
        """
        rows = lines.splitlines() if isinstance(lines, str) else list(lines)
        inset_top = 27 if label else 15
        required = inset_top + len(rows) * lineheight + 10
        h = height or required
        self.box(x, top, width, h, C.NAVY if dark else C.PANEL, radius=9)
        if label:
            self.text(label.upper(), x + 13, top + 10, size=7.4,
                      font='bold', color=C.LIGHT_INK if dark else C.TEAL)
        for i, line in enumerate(rows):
            # Avoid overflow: shrink font for this block if the longest line
            # exceeds the available width. This preserves every character.
            content_width = width - 26
            base_size = size
            if pdfmetrics.stringWidth(line, self.font['mono'], base_size) > content_width:
                fit = content_width / max(
                    pdfmetrics.stringWidth(line, self.font['mono'], 1), 0.01)
                base_size = max(5.0, min(base_size, fit))
            ink = C.LIGHT_INK if dark else C.NAVY
            if line.lstrip().startswith('#'):
                ink = '#99BEC4' if dark else C.MUTED
            self.text(line, x + 13, top + inset_top + i * lineheight,
                      size=base_size, font='mono', color=ink)
        return h

    def bullet(self, top: float, text: str, x: float = M,
               width: float = CW, size: float = 8.9) -> float:
        self.pdf.setFillColor(self.col(C.N3_BLUE))
        self.pdf.circle(x + 5, self.y(top + 8), 2.5, stroke=0, fill=1)
        return self.para(text, x + 17, top, width - 17, size=size,
                         leading=size * 1.44)

    def section(self, number: str, eyebrow: str, title: str,
                intro: str, idx: int, category: str = 'CLOCK DOMAINS - AFFINE MAPPING') -> None:
        self.text('CLOCKMESH / DEVELOPER TUTORIAL', M, 34,
                  size=7.3, font='bold', color=C.N3_BLUE)
        self.text(category, W - M, 34, size=7.0, font='body',
                  color=C.MUTED, align='right')
        self.rule(M, 52, W - M, 52, C.N3_BLUE, 1.65)
        self.tag(f'{number} / {eyebrow.upper()}', 83)
        self.text(title, M, 111, size=25.8, font='heavy')
        self.para(intro, M, 153, CW, size=9.0, leading=13.0, color=C.MUTED)
        self.footer(idx)

    def footer(self, idx: int) -> None:
        self.rule(M, 795, W - M, 795, C.LINE, 0.75)
        self.text('clock-mesh 0.1.0',
                  M, 810, size=6.9, font='body', color=C.MUTED)
        self.text(f'{idx:02d} / 08', W - M, 810, size=7.1,
                  font='bold', color=C.N3_BLUE, align='right')

    def finish_page(self) -> None:
        self.pdf.showPage()

    def save(self) -> None:
        self.pdf.save()


def cover(d: Tutorial) -> None:
    p = d.pdf
    d.bar(0, 0, W, 302, C.NAVY)
    # Original design's quiet diagonal technical lines.
    for n in range(8):
        x = 320 + n * 32
        d.rule(x, 22, x + 150, 292, '#545DF7', 0.55)
    d.text('CLOCKMESH / DEVELOPER GUIDE', M, 62, 8.6,
           'bold', '#D3E9EC', tracking=0.55)
    d.text('Clock alignment,', M, 99, 34.2, 'heavy', C.WHITE)
    d.text('explained.', M, 140, 34.2, 'heavy', C.WHITE)
    d.para('Creating a shared timeline for multiple sensors',
           M, 199, CW - 48, size=11, leading=16, color='#DAE8EB')
    d.box(M, 252, 95, 24, '#545DF7', radius=12)
    d.text('PYTHON 3.10+', M + 12, 258, 8.4, 'bold', C.WHITE)
    d.box(M + 109, 252, 106, 24, '#545DF7', radius=12)
    d.text('CLOCKMESH 0.1.0', M + 121, 258, 8.0, 'bold', C.WHITE)

    d.bar(0, 302, W, H - 302, C.OFF_WHITE)
    d.tag('THE CORE IDEA', 329)
    d.box(M, 355, CW, 171, C.WHITE, radius=13, stroke=C.LINE)
    d.box(M + 18, 377, 143, 83, C.N3_ACCENT, radius=8)
    d.text('SOURCE CLOCK', M + 29, 389, 8.1, 'bold', C.WHITE)
    d.text('32,000,000', M + 29, 421, 14.5, 'mono', C.WHITE)
    d.box(M + CW - 164, 377, 143, 83, C.N3_ACCENT, radius=8)
    d.text('REFERENCE CLOCK', M + CW - 153, 389, 8.1, 'bold', C.WHITE)
    d.text('50,000,000,000', M + CW - 153, 421, 11.8, 'mono', C.WHITE)
    x1, x2, yy = M + 168, M + CW - 175, 418
    d.rule(x1, yy, x2, yy, C.N3_BLUE, 1.7)
    p.setFillColor(d.col(C.N3_BLUE))
    path = p.beginPath()
    path.moveTo(x2, d.y(yy))
    path.lineTo(x2 - 8, d.y(yy - 4))
    path.lineTo(x2 - 8, d.y(yy + 4))
    path.close()
    p.drawPath(path, fill=1, stroke=0)
    d.text('affine fit', (x1+x2)/2, 390, 8.0,
           'bold', C.N3_BLUE, align='center')
    d.text('reference_ns = scale * source_time + offset',
           W / 2, 482, 10.1, 'mono', C.NAVY, align='center')

    desc = [
        ('01 / RATE', 'How regression estimates ns per source unit.'),
        ('02 / TIMELINE', 'How the accepted mapping converts timestamps.'),
    ]
    for i, (label, definition) in enumerate(desc):
        top = 548 + i*64
        d.box(M, top, CW, 54, C.WHITE, radius=8, stroke=C.LINE)
        d.text(label, M+17, top+18, 8.3, 'bold', C.N3_BLUE)
        d.text(definition, M+148, top+18, 9.4, 'body', C.NAVY)
    d.rule(M, 771, W-M, 771, C.LINE)
    d.text('clock-mesh 0.1.0',
           M, 787, 8.0, 'body', C.MUTED)
    d.text('OCTOBER 2026', W-M, 787, 7.7, 'bold', C.N3_BLUE, align='right')
    d.finish_page()


def concept_page(d: Tutorial) -> None:
    d.section('01', 'Concept', 'Two clocks, one relationship',
              'A caller supplies pairs of corresponding timestamps. ClockMesh learns '
              'how the source clock advances relative to a chosen reference clock.', 2)
    d.box(M, 207, CW, 69, C.PALE_TEAL)
    d.tag('THE AFFINE RELATIONSHIP', 218, M+15, size=7.7)
    d.text('reference_time = a * source_time + b', M+15, 239,
           13.2, 'mono')

    cgap=14
    cardw=(CW-cgap)/2
    d.box(M, 292, cardw, 107, C.OFF_WHITE)
    d.box(M+cardw+cgap, 292, cardw, 107, C.OFF_WHITE)
    d.tag('a / SCALE', 307, M+15, size=9)
    d.para('Clock rate: how many reference nanoseconds pass for one source unit.',
           M+15, 333, cardw-30, size=9.2, leading=14)
    d.tag('b / OFFSET', 307, M+cardw+cgap+15, color=C.TEAL, size=9)
    d.para('Clock placement: where a source timestamp lands on the reference timeline.',
           M+cardw+cgap+15, 333, cardw-30, size=9.2, leading=14)

    d.bar(M, 412, 3.1, 17, C.N3_BLUE)
    d.text('A two-pair example', M+13, 412, 13.0, 'bold')
    d.para('Assume the source reports microsecond-like counts and the reference '
           'reports integer nanoseconds.', M, 443, CW, size=8.9)
    headers = ['PAIR', 'SOURCE TIME', 'REFERENCE TIME (ns)']
    xcols = [M+12, M+127, M+278]
    d.box(M, 473, CW, 35, C.NAVY2, radius=5)
    for x, header in zip(xcols, headers):
        d.text(header, x, 485, 7.6, 'bold', C.WHITE)
    for idx,(name,src,ref) in enumerate([
        ('First','32,000,000','50,000,000,000'),
        ('Second','33,000,000','51,000,000,000'),
    ]):
        top=508+idx*39
        d.box(M, top, CW, 39, C.PANEL if idx%2==0 else C.WHITE, radius=0)
        d.text(name, xcols[0],top+12,9.0)
        d.text(src, xcols[1],top+12,9.0)
        d.text(ref, xcols[2],top+12,9.0)

    d.box(M, 605, CW, 94, C.PALE_TEAL)
    d.tag('RATE', 618, M+14, size=7.9)
    d.text('a = (51e9 - 50e9) / (33e6 - 32e6) = 1,000',
           M+14, 634, 9.8, 'mono')
    d.tag('MAPPING', 652, M+14, size=7.9)
    d.text('R(34e6) = 50e9 + 1,000 * (34e6 - 32e6) = 52e9',
           M+14, 668, 9.25, 'mono')
    d.callout(714, 'Interpretation',
              'ClockMesh does not require the name of the source unit. Its learned '
              'scale is measured in reference nanoseconds per source unit. A shared '
              'timeline is whichever reference clock the caller selected.', 64,
              text_size=8.6, fill=C.WHITE, accent=C.N3_BLUE)
    d.finish_page()


def flow_page(d: Tutorial) -> None:
    d.section('02', 'API flow', 'From a client call to a timestamp',
              'Only a few methods are called by an application. Most of the work '
              'happens inside observe(), with explicit acceptance of later candidates.', 3)
    top=214
    d.box(M, top, CW, 34, C.NAVY2, radius=5)
    d.text('WHAT THE CLIENT CALLS', M+13, top+10, 8.1, 'bold', C.WHITE)
    d.text('WHAT CLOCKMESH DOES INTERNALLY', M+241, top+10, 8.0, 'bold', C.WHITE)
    rows = [
        ('AffineClockModel(config)', '__init__() creates UNOBSERVED state and empty windows.'),
        ('observe(first_pair)', 'Stores source / reference anchor; state becomes ANCHORED.'),
        ('observe(more_pairs)', '_calculate_affine_fit() estimates slope; RATE_ESTIMATING.'),
        ('observe(until ready)', '_ready_to_align() -> _accept_learned_mapping(); ALIGNED.'),
        ('observe(later_pairs)', 'map() predicts; logs error; fits candidate; TRACKING.'),
        ('candidate_is_eligible(pivot)', 'Checks count, span, positive scale and latest-pair pivot.'),
        ('accept_full_candidate()\nor accept_candidate()',
         'Accept full fit or update only the slope with continuity.'),
        ('map(source_time)', 'Returns reference nanoseconds using the applied fit.'),
    ]
    rtop=248
    height=47.0
    for i,(call,inside) in enumerate(rows):
        y=rtop+i*height
        if i%2==0:
            d.box(M,y,CW,height,C.PANEL,radius=3)
        d.box(M+10,y+10,29,25,C.PALE_TEAL,radius=12)
        d.text(f'{i+1:02d}', M+24.5,y+16,8.5,'bold',C.N3_BLUE, align='center')
        d.para(call,M+49,y+12,185,size=8.2,leading=11.2)
        d.para(inside,M+241,y+12,CW-254,size=8.1,leading=11.5)
    states_top=643
    d.rule(M,states_top-10,W-M,states_top-10,C.LINE,0.75)
    d.tag('STATE PROGRESSION',states_top)
    labels=['UNOBSERVED','ANCHORED','RATE ESTIMATING','ALIGNED','TRACKING']
    widths=[87,76,111,65,76]
    x=M
    for i,(label,width) in enumerate(zip(labels,widths)):
        d.box(x,666,width,27,C.PALE_TEAL if i>=3 else C.PANEL,radius=3)
        d.text(label,x+width/2,674,7.3,'bold',C.N3_BLUE if i>=3 else C.NAVY,
               align='center')
        x+=width
        if i<len(labels)-1:
            d.text('>',x+5,674,9.0,'bold',C.MUTED)
            x+=19
    d.callout(716,'Division of responsibility',
              'observe() automatically applies the initial learned fit when ready. '
              'Later tracking fits remain candidates until the client calls an '
              'acceptance method. map() never silently adopts an unaccepted candidate.',
              67, text_size=8.5, fill=C.WHITE, accent=C.N3_BLUE)
    d.finish_page()


def estimation_page(d: Tutorial) -> None:
    d.section('03','Estimation','Inside the affine fit',
              'The internal helper _calculate_affine_fit() performs ordinary least '
              'squares (OLS) on anchored timestamp differences.',4)
    d.bar(M,204,3,18,C.N3_BLUE)
    d.text('Step 1 / Subtract the first pair',M+13,201,12.4,'bold')
    d.para('For every observation (s, r), define deltas x = s - s0 and y = r - r0. '
           'This keeps large absolute clock values out of the regression.',
           M,229,CW,size=8.8,leading=12.8)
    d.box(M,270,CW,55,C.PANEL)
    d.text('x_i = source_i - source_0',M+17,286,9.4,'mono')
    d.text('y_i = reference_i - reference_0',M+262,286,8.5,'mono')

    d.bar(M,341,3,18,C.N3_BLUE)
    d.text('Step 2 / Fit slope and relative offset',M+13,338,12.4,'bold')
    d.para('Every retained pair has equal weight. OLS finds the straight line '
           'that minimizes squared residuals across those pairs.',
           M,365,CW,size=8.8,leading=12.8)
    d.box(M,409,CW,90,C.PALE_TEAL)
    d.text('a = sum[(x_i - mean(x)) * (y_i - mean(y))]',
           M+17,423,9.1,'mono')
    d.text('    / sum[(x_i - mean(x)) ** 2]',
           M+17,441,9.1,'mono')
    d.text('c = mean(y) - a * mean(x)',M+17,470,9.4,'mono')

    d.bar(M,518,3,18,C.N3_BLUE)
    d.text('Step 3 / Evaluate the applied model',M+13,515,12.4,'bold')
    d.para('After initial alignment or later acceptance, map(source_time) uses '
           'the stored anchor, accepted scale and relative offset:',
           M,542,CW,size=8.8,leading=12.8)
    d.box(M,581,CW,45,C.NAVY2)
    d.text('R(s) = r0 + round(c + a * (s - s0))',
           M+15,595,10.3,'mono',C.WHITE)

    d.bar(M,645,3,18,C.N3_BLUE)
    d.text('Short worked example',M+13,642,12.0,'bold')
    d.para('With source pairs 32e6, 33e6 and reference pairs 50e9, 51e9, '
           'the rate is a = 1,000 ns per source unit. Here the fitted '
           'relative offset is c = 0.',
           M,669,CW,size=8.8,leading=12.7)
    d.box(M,706,CW,43,C.PANEL)
    d.text('R(34,000,000) = 50,000,000,000 +',M+15,715,9.2,'mono')
    d.text('                1,000 * 2,000,000 = 52,000,000,000 ns',
           M+15,731,8.6,'mono')
    d.text('OFFSET IS NOT THE ZERO BASELINE',M,762,7.3,'bold',C.N3_BLUE)
    d.para('The anchored offset c can be zero while the equivalent global intercept '
           'b = r0 + c - a*s0 is nonzero.',M,775,CW,size=7.7,leading=10.2)
    d.finish_page()


def tracking_page(d: Tutorial) -> None:
    d.section('04','Tracking','New candidates versus the accepted model',
              'After initial alignment, each observation is compared with the '
              'currently applied mapping. A second fit is maintained without altering map().',5)
    d.bar(M,210,3,18,C.N3_BLUE)
    d.text('What a tracking observation triggers',M+13,207,12.1,'bold')
    d.code(239,[
        'predicted_ns = map(source_time)',
        'error_ns = observed_reference_ns - predicted_ns',
        'candidate = _calculate_affine_fit(tracking_window)',
    ],height=80,dark=False,size=8.6,lineheight=18)
    d.para('The applied fit powers map(). The candidate powers map_candidate(). '
           'Reading a candidate does not accept it.',M,334,CW,8.7,12.9)

    gap=14; width=(CW-gap)/2
    d.box(M,375,width,239,C.PALE_TEAL)
    d.box(M+width+gap,375,width,239,C.PALE_CORAL)
    d.tag('FULL ACCEPTANCE',391,M+15,size=8.2)
    d.text('accept_full_candidate(pivot)',M+15,417,8.5,'mono')
    d.para('Accepts the candidate scale and offset. The mapped timestamp at '
           'the pivot may jump.',M+15,446,width-30,8.9,13)
    d.text('At the pivot (illustrative):',M+15,514,8.8,'bold')
    d.text('old: 55.000000 s',M+15,537,8.9,'mono')
    d.text('new: 54.985964 s',M+15,555,8.9,'mono')
    d.text('jump: -14.036 ms',M+15,580,8.5,'bold',C.N3_BLUE)

    x=M+width+gap
    d.tag('CONTINUOUS ACCEPTANCE',391,x+15,color=C.N3_BLUE,size=8.0)
    d.text('accept_candidate(pivot)',x+15,417,8.5,'mono')
    d.para('Accepts the candidate scale only. Re-anchors at the old mapped '
           'pivot time.',x+15,446,width-30,8.9,13)
    d.text('At the same pivot:',x+15,514,8.8,'bold')
    d.text('old: 55.000000 s',x+15,537,8.9,'mono')
    d.text('new: 55.000000 s',x+15,555,8.9,'mono')
    d.text('jump: 0 ms',x+15,580,8.5,'bold',C.N3_BLUE)

    d.bar(M,628,3,17,C.N3_BLUE)
    d.text('When is a candidate eligible?',M+13,626,12,'bold')
    d.para('The library checks TRACKING state, minimum retained pairs, sufficient '
           'reference-time span, a positive finite slope, and a pivot equal to '
           'the latest observed source timestamp.',M,650,CW,8.5,12.1)
    d.box(M,685,CW,42,C.PANEL)
    d.tag('DEFAULTS',695,M+12,size=7.2)
    d.para('Initial alignment: 2 s and at least 5 pairs. Candidate acceptance: 30 s '
           'of retained reference span. Calibration history reuse: off by default.',
           M+12,705,CW-24,size=7.9,leading=10.6)
    
    d.callout(740,'Client policy',
              'Eligibility is not a statistical quality test. The client must decide '
              'whether jitter, latency, outliers, model drift and application phase '
              'boundaries make acceptance appropriate.',41, text_size=7.5, fill=C.WHITE, accent=C.N3_BLUE)
    d.finish_page()


def zero_baseline_chart(d: Tutorial, top: float, height: float) -> None:
    """Draw a vector chart: baseline = initial - initial, candidate = candidate - initial.

    These curves are illustrative mappings, NOT measurements:
        initial(t)   = 50 + t                 seconds
        candidate(t) = 49.989964 + .9992 * t seconds
    At t=5: (54.985964 - 55) * 1000 = -14.036 ms.
    """
    d.box(M,top,CW,height,C.OFF_WHITE,radius=8,stroke=C.LINE)
    d.text('Difference (ms)',M+15,top+13,7.4,'body',C.MUTED)
    d.rule(M+115,top+20,M+134,top+20,C.TEAL,2.0)
    d.text('Initial vs itself',M+139,top+15,7.9,'body',C.MUTED)
    d.rule(M+265,top+20,M+283,top+20,C.CORAL,2.0)
    d.text('Candidate - initial',M+289,top+15,7.9,'body',C.MUTED)

    x0, x1 = M + 48, W - M - 20
    y0, y1 = top+44, top+height-27

    def X(t: float) -> float:
        return x0 + (x1-x0)*t/5

    def Y(diff_ms: float) -> float:
        return y0 + (1.0-diff_ms)*(y1-y0)/17.0

    for yy in (0,-5,-10,-15):
        d.rule(x0,Y(yy),x1,Y(yy),C.LINE,0.75,[2,3])
        d.text(str(yy),x0-14,Y(yy)-4,7.7,'body',C.MUTED,align='right')
    for tt in range(6):
        d.text(str(tt),X(tt),y1+8,7.6,'body',C.MUTED,align='center')
    # Teal zero-baseline across every sample.
    d.rule(X(0),Y(0),X(5),Y(0),C.TEAL,2.35)
    # Candidate minus the initial map; -10.036ms at t=0 and -14.036 at 5.
    for i in range(5):
        diff0=-10.036-0.8*i
        diff1=-10.036-0.8*(i+1)
        d.rule(X(i),Y(diff0),X(i+1),Y(diff1),C.CORAL,2.15)
    for i in range(6):
        p=d.pdf
        p.saveState(); p.setFillColor(d.col(C.CORAL))
        p.circle(X(i),d.y(Y(-10.036-0.8*i)),2.2,stroke=0,fill=1)
        p.restoreState()
    d.rule(X(5),Y(0)+4,X(5),Y(-14.036)-4,C.CORAL,0.8,[2,3])
    d.box(x1-83,Y(-14.036)-18,91,19,C.PALE_CORAL,radius=4)
    d.text('-14.036 ms',x1-76,Y(-14.036)-14,8.7,'bold',C.CORAL)


def baseline_page(d: Tutorial) -> None:
    d.section('05','Plot interpretation','Why the baseline is exactly zero',
              'A zero-baseline plot usually shows a difference between mappings, '
              'not the absolute timestamps produced by the original mapping.',6)
    d.box(M,201,CW,76,C.PALE_TEAL)
    d.text('initial_line(t)   = initial_map(t) - initial_map(t) = 0',
           M+13,215,8.6,'mono')
    d.text('candidate_line(t) = candidate_map(t) - initial_map(t)',
           M+13,245,8.6,'mono')

    zero_baseline_chart(d,291,255)
    d.para('Illustrative only. The accepted initial mapping is the comparison '
           'reference. Its plotted difference is zero by definition, even though '
           'absolute timestamps are around 50-55 seconds.',
           M,552,CW,size=8.0,leading=10.8,color=C.MUTED)
    d.box(M,592,CW,69,C.OFF_WHITE,stroke=C.LINE)
    d.text('initial(t) = 50.000000 + 1.000000 * t   seconds',
           M+12,600,8.7,'mono')
    d.text('candidate(t) = 49.989964 + 0.999200 * t   seconds',
           M+12,621,8.5,'mono')
    d.text('at t = 5: 54.985964 - 55.000000 = -14.036 ms',
           M+12,644,8.5,'mono',C.CORAL)
    d.code(674,[
        'def initial(t):   return 50.0 + t',
        'def candidate(t): return 49.989964 + 0.9992 * t',
        '',
        'for t in range(6):',
        '    baseline_ms = (initial(t) - initial(t)) * 1000',
        '    delta_ms = (candidate(t) - initial(t)) * 1000',
        '    print(t, round(baseline_ms, 3), round(delta_ms, 3))',
    ],height=104,label='ZERO-BASELINE EXAMPLE / PYTHON',size=7.55,lineheight=10.2)
    d.finish_page()


def quickstart_page(d: Tutorial) -> None:
    d.section('06','Quickstart','Get started with the library',
              'The package is installed from the repository. This short script '
              'feeds synthetic matching timestamp pairs and explicitly accepts '
              'the five-second full candidate.',7)
    d.bar(M,207,3,17,C.N3_BLUE)
    d.text('1 / Install',M+13,205,12.0,'bold')
    d.code(232,[
        'git clone https://github.com/mcrooks83/ClockMesh.git',
        'cd ClockMesh',
        'python3 -m venv .venv',
        'source .venv/bin/activate',
        'python -m pip install -e .',
    ],height=97,label='TERMINAL',size=8.2,lineheight=12)

    d.bar(M,345,3,17,C.N3_BLUE)
    d.text('2 / Create quickstart.py',M+13,343,12.0,'bold')
    d.code(372,[
        'from clock_mesh import AffineClockModel, ClockAlignmentConfig',
        '',
        'config = ClockAlignmentConfig(',
        '    target_calibration_span_ns=1_000_000_000,',
        '    min_tracking_acceptance_span_ns=5_000_000_000,',
        '    reuse_calibration_history=True,',
        ')',
        'model = AffineClockModel(config)',
        '',
        '# 301 pairs: 60 Hz over five seconds (both endpoints)',
        'for i in range(301):',
        '    source_us = round(i * 1_000_000 / 60)',
        '    ref_ns = 50_000_000_000 + round(i * 1_000_000_000 / 60)',
        '    model.observe(source_us, ref_ns)',
        '',
        'print(model.mapping_available)   # True',
        'print(model.state.value)         # tracking',
        'print(model.estimated_scale_ns_per_source_unit)  # ~1000',
        '',
        'pivot = source_us   # latest observed source timestamp',
        'if model.candidate_is_eligible(pivot):',
        '    model.accept_full_candidate(pivot)  # official boundary',
        '',
        'print(model.map(pivot))          # ~55e9 ns',
    ],height=323,label='PYTHON / QUICKSTART.PY',size=7.1,lineheight=11.65)

    d.bar(M,712,3,16,C.N3_BLUE)
    d.text('3 / Run and interpret',M+13,709,11.3,'bold')
    d.para('Run python quickstart.py. The source values act like microseconds; '
           'the reference is nanoseconds. The model aligns automatically after '
           'about one second, then has a five-second retained history.',
           M,731,CW,size=8.1,leading=11.4)
    d.finish_page()


def reference_page(d: Tutorial) -> None:
    d.section('07','Reference','Apply ClockMesh safely',
              'ClockMesh is deliberately generic: it models one continuous '
              'relationship between a source clock and a reference clock. '
              'The application owns the rest.',8)
    d.bar(M,208,3,17,C.N3_BLUE)
    d.text('API reference at a glance',M+13,205,12.0,'bold')
    d.box(M,237,CW,34,C.NAVY2,radius=5)
    d.text('ENTRY POINT',M+10,248,8.0,'bold',C.WHITE)
    d.text('ROLE',M+258,248,8.0,'bold',C.WHITE)
    rows=[
        ('observe(source, reference_ns)',
         'Add a correspondence; calibrate or update the candidate fit.'),
        ('map(source)', 'Use the currently applied mapping; may return None.'),
        ('map_candidate(source)', 'Preview the full candidate without accepting it.'),
        ('candidate_is_eligible(pivot)', 'Check minimum evidence and latest-pair pivot.'),
        ('accept_full_candidate(pivot)', 'Apply candidate scale and offset; may cause a time jump.'),
        ('accept_candidate(pivot)', 'Apply scale but preserve mapped time at the pivot.'),
    ]
    height=39
    for i,(name,meaning) in enumerate(rows):
        top=271+i*height
        d.box(M,top,CW,height,C.PANEL if i%2==0 else C.WHITE,radius=0)
        d.para(name,M+10,top+11,240,size=8.0,leading=11,font='mono')
        d.para(meaning,M+258,top+11,CW-269,size=8.1,leading=11)
        d.rule(M,top+height,W-M,top+height,C.LINE,0.55)

    d.bar(M,522,3,17,C.N3_BLUE)
    d.text('What the caller must provide',M+13,519,12.0,'bold')
    bullets=[
        'Consistent pairs. Each pair must refer to corresponding events. '
        'Transport delay and queuing can bias the fitted offset.',
        'Clean clock epochs. ClockMesh does not unwrap rollover, handle resets, '
        'or reject outliers automatically.',
        'A reference domain. Reference nanoseconds may be monotonic time; '
        'they are not necessarily UTC.',
        'An acceptance policy. Evaluate error, jitter and drift before promoting '
        'a candidate.',
    ]
    for y,text in zip((550,588,624,660),bullets):
        d.bullet(y,text,size=8.4)

    d.callout(710,'More than two clocks?',
              'A sensor-to-gateway fit and a gateway-to-host fit can be composed '
              'to express sensor time in host time. ClockMesh does not compose '
              'or maintain a global graph of clocks for you.',50,text_size=8.0, fill=C.WHITE, accent=C.N3_BLUE)
    d.text('SOURCE & VERIFICATION',M,773,7.0,'bold',C.N3_BLUE)
    d.para('Repository: github.com/mcrooks83/ClockMesh | '
           'implementation: src/clock_mesh/model.py | '
           'configuration: config.py | tests: tests/',
           M,784,CW,size=6.8,leading=8.9,color=C.MUTED)
    d.finish_page()


def build(path: str) -> None:
    dest=Path(path)
    dest.parent.mkdir(parents=True,exist_ok=True)
    doc=Tutorial(str(dest))
    cover(doc)
    concept_page(doc)
    flow_page(doc)
    estimation_page(doc)
    tracking_page(doc)
    baseline_page(doc)
    quickstart_page(doc)
    reference_page(doc)
    doc.save()
    print(f'Wrote {dest}')


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output','-o',default='ClockMesh_Developer_Tutorial_Recreated.pdf',
                        help='Output PDF filename or path')
    args=parser.parse_args()
    build(args.output)


if __name__ == '__main__':
    main()