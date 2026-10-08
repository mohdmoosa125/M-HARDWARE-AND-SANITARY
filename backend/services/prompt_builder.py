"""
prompt_builder.py
-----------------
Builds a category-aware text-to-image prompt from the product's real database fields.
Only fields that exist are used; nothing is invented. Brand and SKU are deliberately
left out of the prompt so the model does not paint fake logos or labels.

    build_prompt(product, research=None) -> (prompt, negative_prompt)
"""

NEGATIVE_PROMPT = (
    "text, watermark, logo, fake brand, fake label, signature, people, hands, fingers, "
    "extra objects, duplicate product, distorted geometry, malformed object, blurry, "
    "low resolution, jpeg artifacts, cropped product, cartoon, illustration, "
    "unrealistic proportions, random text, AI artifacts"
)

STYLE = (
    "Professional commercial e-commerce catalog photograph, photorealistic, sharp, "
    "high detail, soft controlled studio lighting, centred composition, realistic contact "
    "shadow, clean light neutral background (#f4f8fb), single product only"
)

AUTHENTICITY = (
    "generic unbranded product, no logos, no labels, no printed text, "
    "no model numbers, no certification marks"
)

# keyword in name -> hint (checked before the category hint)
NAME_HINTS = [
    (("tap", "cock", "mixer", "faucet", "shower"),
     "realistic polished chrome or brass with accurate metallic reflections, three-quarter view, "
     "clean bathroom-product photography, realistic proportions, no running water"),
]

CATEGORY_HINTS = {
    "pipes": "plumbing pipe with accurate geometry and realistic plastic material, "
             "horizontal or slightly diagonal orientation, cut ends visible",
    "fittings": "small plumbing fitting with accurate geometry and realistic material, "
                "three-quarter view, single piece",
    "sanitary": "ceramic sanitaryware with realistic glossy finish, correct shape, three-quarter "
                "product view, neutral showroom feel",
    "tiles": "flat tile sample with accurate geometry and surface, front-facing catalog view, "
             "no perspective distortion, pattern centred and consistent",
    "hardware": "macro product photography of the hardware item, realistic metal, accurate "
                "shape, isolated presentation, sharp details",
    "tools": "hand tool with correct geometry and realistic steel and handle material, "
             "appropriate angle, sharp details",
    "machines": "industrial product photography of the machine, realistic proportions, "
                "accurate shape, strong controlled lighting, no loose cables",
    "construction materials": "construction material shown in its realistic form or packaging "
                              "(no printed text on packaging), neutral background",
    "accessories": "small plumbing/hardware accessory, realistic material, isolated, sharp details",
}


def _root_and_sub(product):
    cat = product.category
    sub = cat.name if cat else ""
    while cat is not None and cat.parent is not None:
        cat = cat.parent
    return (cat.name if cat else ""), sub


def category_key(product):
    return _root_and_sub(product)[0].lower()


def build_prompt(product, research=None):
    root, sub = _root_and_sub(product)
    details = []
    for label, value in (("material", product.material), ("colour", product.color),
                         ("size", product.size), ("finish", product.finish),
                         ("thickness", product.thickness)):
        if value and str(value).strip() not in ("-", "Standard"):
            details.append(f"{label}: {value}")

    subject = f"{product.name}"
    if sub and sub.lower() not in product.name.lower():
        subject += f" ({sub})"
    parts = [f"A {subject}"]
    if details:
        parts.append(", ".join(details))
    short = (product.short_description or "").strip()
    brand = (product.brand or "").strip().lower()
    if short and short != product.name and not (brand and brand in short.lower()):
        parts.append(short)                      # skipped when it mentions the brand (logo risk)
    if research and research.get("shape") and research["shape"] != "single product":
        parts.append(f"shape: {research['shape']}")

    hint = next((h for words, h in NAME_HINTS if any(w in product.name.lower() for w in words)), None)
    hint = hint or CATEGORY_HINTS.get(root.lower(), "")

    prompt = ". ".join(p for p in parts + [hint, STYLE, AUTHENTICITY] if p) + "."
    return prompt, NEGATIVE_PROMPT
