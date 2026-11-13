#!/usr/bin/env python3
"""Build the static site from reusable templates and JSON content."""

import argparse
import html
import json
import re
import shutil
import sys
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src"
COMPONENTS = SOURCE / "components"
DATA = SOURCE / "data"

ROUTES = {
    "home": ("index.html", "../index.html"),
    "about": ("pages/about.html", "about.html"),
    "products": ("pages/products.html", "products.html"),
    "mission": ("pages/mission-vision.html", "mission-vision.html"),
    "contact": ("pages/contact.html", "contact.html"),
    "privacy": ("pages/privacy-policy.html", "privacy-policy.html"),
    "terms": ("pages/terms.html", "terms.html"),
}
PAGE_TOKENS = {
    "header": "<!-- shared:header -->",
    "site-footer": "<!-- shared:site-footer -->",
    "legal-footer": "<!-- shared:legal-footer -->",
    "home-offers": "<!-- data:home-offers -->",
    "products": "<!-- data:products -->",
    "testimonials": "<!-- data:testimonials -->",
    "product-footer-links": "<!-- data:product-footer-links -->",
    "product-names": "<!-- data:product-names -->",
}


def read_json(path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def replace_values(template, values, label):
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)

    unresolved = re.search(r"\{\{[^{}]+\}\}", template)
    if unresolved:
        raise ValueError(f"Unresolved template value {unresolved.group(0)!r} in {label}")
    return template


def render_component(name, values):
    template = (COMPONENTS / f"{name}.html").read_text(encoding="utf-8")
    return replace_values(template, values, name)


def render_cards(component, items, values_for_item):
    template = (COMPONENTS / f"{component}.html").read_text(encoding="utf-8")
    return "\n".join(
        replace_values(template, values_for_item(item), component) for item in items
    )


def route_values(is_root):
    return {
        f"{name}_href": html.escape(paths[0 if is_root else 1], quote=True)
        for name, paths in ROUTES.items()
    }


class LocalReferenceParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.references = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ("href", "src") and value:
                self.references.append(value)


def validate_references(document, output_path, generated_paths):
    parser = LocalReferenceParser()
    parser.feed(document)
    parser.close()

    for reference in parser.references:
        if reference.startswith(("#", "//")) or re.match(r"^[a-z][a-z0-9+.-]*:", reference, re.I):
            continue
        target = reference.split("#", 1)[0].split("?", 1)[0]
        if not target:
            continue
        resolved = (ROOT / output_path.parent / target).resolve()
        if resolved in generated_paths:
            continue
        if not resolved.is_file():
            relative = resolved.relative_to(ROOT)
            raise ValueError(f"Missing local file {relative} referenced by {output_path}")


def sync_static_assets(check):
    static_paths = ("assets", "css", "js", "favicon.ico")
    for name in static_paths:
        source = ROOT / name
        destination = ROOT / "dist" / name
        if source.is_dir():
            for source_file in source.rglob("*"):
                if not source_file.is_file():
                    continue
                relative = source_file.relative_to(ROOT)
                destination_file = ROOT / "dist" / relative
                if check:
                    if (
                        not destination_file.is_file()
                        or source_file.read_bytes() != destination_file.read_bytes()
                    ):
                        raise ValueError(
                            f"dist/{relative} is missing or out of date; "
                            "run python scripts/build.py"
                        )
                else:
                    destination_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_file, destination_file)
        elif check:
            if not destination.is_file() or source.read_bytes() != destination.read_bytes():
                raise ValueError(f"dist/{name} is missing or out of date; run python scripts/build.py")
        else:
            shutil.copy2(source, destination)


def build_page(page, products, testimonials, generated_paths, check):
    source_path = SOURCE / page["source"]
    output_path = Path(page["output"])
    document = source_path.read_text(encoding="utf-8")

    is_root = source_path == SOURCE / "index.html"
    routes = route_values(is_root)
    component_values = {
        **routes,
        "asset_prefix": "" if is_root else "../",
    }
    active = page.get("active")
    for name in ("home", "about", "products", "mission", "contact"):
        component_values[f"current_{name}"] = (
            'aria-current="page"' if active == name else ""
        )
    component_values["current_privacy"] = (
        'aria-current="page"' if output_path.name == "privacy-policy.html" else ""
    )
    component_values["current_terms"] = (
        'aria-current="page"' if output_path.name == "terms.html" else ""
    )

    replacements = {
        PAGE_TOKENS["header"]: render_component("site-header", component_values),
    }
    footer = page["footer"]
    if footer == "site":
        replacements[PAGE_TOKENS["site-footer"]] = render_component(
            "site-footer", component_values
        )
        replacements[PAGE_TOKENS["product-footer-links"]] = render_cards(
            "product-footer-link",
            products,
            lambda product: {
                **component_values,
                "name": html.escape(product["name"]),
            },
        )
    elif footer == "legal":
        replacements[PAGE_TOKENS["legal-footer"]] = render_component(
            "legal-footer", component_values
        )
    else:
        raise ValueError(f"Unknown footer type {footer!r} in {page['source']}")

    if page.get("product_names"):
        replacements[PAGE_TOKENS["product-names"]] = render_cards(
            "product-name",
            products,
            lambda product: {"name": html.escape(product["name"])},
        )

    replacements[PAGE_TOKENS["home-offers"]] = render_cards(
        "offer-card",
        [product for product in products if product["featured"]],
        lambda product: {
            **component_values,
            "image": html.escape(product["image"], quote=True),
            "alt": html.escape(product["alt"], quote=True),
            "name": html.escape(product["name"]),
            "home_description": html.escape(product["home_description"]),
        },
    )
    replacements[PAGE_TOKENS["products"]] = render_cards(
        "product-card",
        products,
        lambda product: {
            **component_values,
            "image": html.escape(product["image"], quote=True),
            "alt": html.escape(product["alt"], quote=True),
            "name": html.escape(product["name"]),
            "description": html.escape(product["description"]),
        },
    )
    replacements[PAGE_TOKENS["testimonials"]] = render_cards(
        "testimonial-card",
        testimonials,
        lambda item: {
            "rating": str(item["rating"]),
            "stars": html.escape(item["stars"]),
            "quote": html.escape(item["quote"]),
            "customer": html.escape(item["customer"]),
        },
    )

    for marker, replacement in replacements.items():
        document = document.replace(marker, replacement)
    for marker in PAGE_TOKENS.values():
        if marker in document:
            raise ValueError(f"Unresolved component marker {marker!r} in {page['source']}")

    validate_references(document, output_path, generated_paths)
    destination = ROOT / output_path
    if check:
        if not destination.is_file() or destination.read_text(encoding="utf-8") != document:
            raise ValueError(f"{output_path} is out of date; run python scripts/build.py")
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(document, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Build the GH MAX static website.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify generated HTML is current without writing files",
    )
    args = parser.parse_args()

    manifest = read_json(DATA / "pages.json")
    products = read_json(DATA / "products.json")
    testimonials = read_json(DATA / "testimonials.json")
    generated_paths = {
        (ROOT / page["output"]).resolve() for page in manifest["pages"]
    }
    sync_static_assets(args.check)
    for page in manifest["pages"]:
        build_page(page, products, testimonials, generated_paths, args.check)

    action = "Verified" if args.check else "Built"
    print(f"{action} {len(manifest['pages'])} pages.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Build failed: {error}", file=sys.stderr)
        sys.exit(1)
