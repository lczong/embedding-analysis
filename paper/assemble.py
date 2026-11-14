#!/usr/bin/env python3
"""Assemble existing paper panels into vector PDF pages."""
import argparse
import io
import json
import subprocess
import sys
from pathlib import Path

import cairosvg
from PIL import Image, ImageChops
from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.generic import RectangleObject
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from embedding_analysis.artifacts import file_digest
from embedding_analysis.publication.render import refresh_previews


def prepare(source, cache):
    digest = file_digest(source)
    pdf = source
    if source.suffix == '.svg':
        pdf = cache/f'{digest}.pdf'
        if not pdf.exists():
            cairosvg.svg2pdf(url=str(source), write_to=str(pdf))
    reader = PdfReader(pdf)
    if len(reader.pages) != 1:
        raise ValueError(f'Expected one page: {source}')
    page = reader.pages[0]
    preview = cache/f'{digest}.png'
    if not preview.exists():
        subprocess.run(['pdftoppm', '-singlefile', '-scale-to', '1800', '-png',
                        str(pdf), str(preview.with_suffix(''))], check=True, capture_output=True)
    with Image.open(preview) as image:
        rgb = image.convert('RGB')
        # Ignore near-white antialiasing, retain all visible plot content.
        diff = ImageChops.difference(rgb, Image.new('RGB', rgb.size, 'white'))
        bounds = diff.convert('L').point(lambda x: 255 if x > 8 else 0).getbbox()
        if bounds is None:
            raise ValueError(f'Blank panel: {source}')
        l, t, r, b = bounds
        l, t, r, b = max(0,l-3), max(0,t-3), min(rgb.width,r+3), min(rgb.height,b+3)
        box = page.mediabox
        x0, y0 = float(box.left), float(box.bottom)
        w, h = float(box.width), float(box.height)
        crop = (x0+l/rgb.width*w, y0+(1-b/rgb.height)*h,
                x0+r/rgb.width*w, y0+(1-t/rgb.height)*h)
    page.cropbox = RectangleObject(crop)
    return reader, page, crop, digest


def assemble(config_path, output):
    config = json.loads(config_path.read_text())
    output.mkdir(parents=True, exist_ok=True)
    cache = ROOT/'.cache'/'paper-assembly'
    cache.mkdir(parents=True, exist_ok=True)
    width, height = config['page_size']
    combined = PdfWriter()
    records = {}
    # pypdf keys cloned objects by reader identity; retain owners throughout merging.
    owners = []
    for figure, layout in config['figures'].items():
        writer = PdfWriter()
        owners.append(writer)
        target = writer.add_blank_page(width, height)
        inputs = []
        for item in layout['items']:
            stem = ROOT/'outputs'/'paper'/figure/item['source']
            candidates = [stem] if stem.suffix else [stem.with_suffix(ext) for ext in ('.pdf','.svg')]
            source = next((p for p in candidates if p.is_file()), None)
            if source is None:
                raise FileNotFoundError(f'Missing panel: {stem}')
            reader, panel, crop, digest = prepare(source, cache)
            owners.append(reader)
            x,y,w,h = item['box']  # Top-left coordinates, points.
            if min(x,y,w,h) < 0 or x+w > width or y+h > height:
                raise ValueError(f'Panel outside page: {figure}/{source.name}')
            l,b,r,t = crop
            scale = min(w/(r-l), h/(t-b))
            tx = x+(w-(r-l)*scale)/2-l*scale
            ty = height-y-h+(h-(t-b)*scale)/2-b*scale
            target.merge_transformed_page(panel, Transformation().scale(scale).translate(tx,ty))
            inputs.append({'file':str(source.relative_to(ROOT)), 'sha256':digest,
                           'box':item['box'], 'crop':crop})
        overlay = io.BytesIO()
        draw = canvas.Canvas(overlay, pagesize=(width,height))
        draw.setFont('Helvetica-Bold', config['label_size'])
        for label, x, y in layout['labels']:
            draw.drawString(x,height-y-config['label_size']*.8,label)
        draw.save()
        overlay_reader = PdfReader(overlay)
        owners.append(overlay_reader)
        target.merge_page(overlay_reader.pages[0])
        path = output/f'{figure}.pdf'
        writer.write(path)
        combined.add_page(target)
        records[figure] = {'inputs':inputs, 'pdf_sha256':file_digest(path)}
        subprocess.run(['pdftoppm','-singlefile','-scale-to','1800','-png',
                        str(path),str(output/figure)],check=True,capture_output=True)
        print(f'Assembled: {path}')
    combined.write(output/'figures2-5.pdf')
    (output/'manifest.json').write_text(json.dumps({
        'layout':config, 'layout_sha256':file_digest(config_path),
        'code_sha256':file_digest(Path(__file__)), 'figures':records},indent=2)+'\n')
    refresh_previews()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--layout',type=Path,default=ROOT/'paper/layouts/figures2-5.json')
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/paper/assembled')
    args = parser.parse_args()
    assemble(args.layout,args.output)
