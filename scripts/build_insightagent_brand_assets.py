"""Build the InsightAgent logo asset set from the canonical transparent mark."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MARK = ROOT / "assets" / "branding" / "insightagent-mark.png"
FONT_REGULAR = Path("C:/Windows/Fonts/segoeui.ttf")
FONT_SEMIBOLD = Path("C:/Windows/Fonts/seguisb.ttf")

INDIGO = "#27336B"
TEAL = "#20C7B7"
AMBER = "#FFB84D"
INK = "#18213D"
MUTED = "#52607A"
OFF_WHITE = "#F7F9FF"


def canonical_mark() -> Image.Image:
    source = Image.open(SOURCE_MARK).convert("RGBA")
    alpha_box = source.getchannel("A").getbbox()
    if alpha_box is None:
        raise ValueError(f"No visible pixels in {SOURCE_MARK}")
    return source.crop(alpha_box)


def contain_mark(mark: Image.Image, size: tuple[int, int], padding: int) -> Image.Image:
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    available = (size[0] - padding * 2, size[1] - padding * 2)
    fitted = mark.copy()
    fitted.thumbnail(available, Image.Resampling.LANCZOS)
    position = ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2)
    canvas.alpha_composite(fitted, position)
    return canvas


def wordmark(
    mark: Image.Image,
    size: tuple[int, int],
    *,
    dark: bool = False,
) -> Image.Image:
    width, height = size
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    pad_y = max(8, round(height * 0.11))
    icon_size = height - pad_y * 2
    icon = contain_mark(mark, (icon_size, icon_size), max(2, round(icon_size * 0.035)))
    canvas.alpha_composite(icon, (round(height * 0.08), pad_y))

    font_size = round(height * 0.43)
    font = ImageFont.truetype(str(FONT_SEMIBOLD), font_size)
    text = "InsightAgent"
    draw = ImageDraw.Draw(canvas)
    text_color = OFF_WHITE if dark else INK
    text_x = round(height * 0.08) + icon_size + round(height * 0.10)
    box = draw.textbbox((0, 0), text, font=font)
    text_y = (height - (box[3] - box[1])) // 2 - box[1]
    draw.text((text_x, text_y), text, fill=text_color, font=font)
    return canvas


def banner(mark: Image.Image, size: tuple[int, int] = (2340, 1180)) -> Image.Image:
    width, height = size
    canvas = Image.new("RGB", size, OFF_WHITE)
    draw = ImageDraw.Draw(canvas)

    # Restrained geometric background using the brand colors at low opacity.
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.ellipse(
        (width * 0.57, -height * 0.34, width * 1.08, height * 0.68),
        fill=(39, 51, 107, 22),
    )
    overlay_draw.ellipse(
        (width * 0.66, height * 0.44, width * 1.02, height * 1.17),
        fill=(32, 199, 183, 26),
    )
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(canvas)

    icon = contain_mark(mark, (560, 560), 18)
    canvas.alpha_composite(icon, (170, 310))

    title_font = ImageFont.truetype(str(FONT_SEMIBOLD), 190)
    subtitle_font = ImageFont.truetype(str(FONT_REGULAR), 68)
    draw.text((820, 395), "InsightAgent", fill=INK, font=title_font)
    draw.text(
        (830, 650),
        "Agentic intelligence for enterprise data",
        fill=MUTED,
        font=subtitle_font,
    )
    draw.rounded_rectangle((830, 770, 1500, 788), radius=9, fill=TEAL)
    draw.rounded_rectangle((1518, 770, 1662, 788), radius=9, fill=AMBER)
    return canvas.convert("RGB")


def save(image: Image.Image, path: Path, **kwargs: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, **kwargs)


def main() -> None:
    mark = canonical_mark()

    small = contain_mark(mark, (512, 512), 34)
    compact = wordmark(mark, (633, 157))
    wide = wordmark(mark, (856, 160))
    dark_wide = wordmark(mark, (2638, 657), dark=True)
    docs_light = wordmark(mark, (1266, 314))
    docs_dark = wordmark(mark, (1266, 314), dark=True)
    hero = banner(mark)

    for root in (
        ROOT / "web" / "public",
        ROOT / "packages" / "dbgpt-app" / "src" / "dbgpt_app" / "static" / "web",
        ROOT / "packages" / "dbgpt-app" / "src" / "dbgpt_app" / "static" / "old_web",
    ):
        save(small, root / "LOGO_SMALL.png")
        save(wide, root / "LOGO.png")
        save(compact, root / "LOGO_1.png")
        save(compact, root / "logo_zh_latest.png")
        save(dark_wide, root / "logo_s_latest.png")
        if root.name == "old_web":
            save(dark_wide, root / "WHITE_LOGO.png")
        save(small.resize((512, 512), Image.Resampling.LANCZOS), root / "pictures" / "logo.png")
        favicon = small.resize((128, 128), Image.Resampling.LANCZOS)
        save(favicon, root / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)])

    save(wide.convert("RGB"), ROOT / "assets" / "LOGO.png")
    save(small, ROOT / "assets" / "LOGO_SMALL.png")
    save(hero, ROOT / "assets" / "InsightAgent.png", quality=95)
    save(hero, ROOT / "assets" / "insightagent.png", quality=95)

    doc_roots = (
        ROOT / "docs" / "static" / "img",
        ROOT / "docs" / "i18n" / "zh-CN" / "docusaurus-plugin-content-docs" / "static" / "img",
    )
    for root in doc_roots:
        save(docs_light, root / "insightagent_logo.png")
        save(docs_dark, root / "insightagent_logo_white.png")
        save(hero, root / "insightagent_banner.png", quality=95)


if __name__ == "__main__":
    main()
