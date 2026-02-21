from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas
import sys

try:
    print("Registering font...")
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
    print("Creating canvas...")
    c = canvas.Canvas("test_font.pdf")
    print("Setting font...")
    c.setFont("HeiseiKakuGo-W5", 12)
    print("Drawing string...")
    c.drawString(100, 100, "日本語テスト (Japanese Test)")
    print("Saving...")
    c.save()
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)
