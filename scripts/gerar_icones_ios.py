#!/usr/bin/env python3
"""Gera ícones PNG para iOS a partir do SVG do manifest."""
import base64, os, sys

SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <rect width="512" height="512" fill="#1F4E79" rx="0"/>
  <rect x="64" y="296" width="96" height="160" rx="12" fill="#C9A84C"/>
  <rect x="208" y="192" width="96" height="264" rx="12" fill="rgba(255,255,255,.85)"/>
  <rect x="352" y="86" width="96" height="370" rx="12" fill="rgba(255,255,255,.6)"/>
</svg>"""

try:
    import cairosvg
    sizes = [20, 29, 40, 58, 60, 76, 80, 87, 120, 152, 167, 180, 1024]
    out_dir = os.path.join(os.path.dirname(__file__), '..', 'ios-icons')
    os.makedirs(out_dir, exist_ok=True)
    for s in sizes:
        cairosvg.svg2png(bytestring=SVG.encode(), write_to=f"{out_dir}/icon-{s}.png", output_width=s, output_height=s)
        print(f"  ✓ icon-{s}.png")
    print(f"\nÍcones salvos em: {out_dir}/")
except ImportError:
    print("cairosvg não instalado. Instale com: pip install cairosvg")
    print("Alternativamente, use o site https://appicon.co para gerar ícones a partir do SVG abaixo:\n")
    print(SVG)
