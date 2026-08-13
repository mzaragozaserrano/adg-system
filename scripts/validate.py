#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.validators import validate_pdf, validate_slides


def print_result(result, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return

    status = "CONFORME" if result.passed else f"{result.grave_count} GRAVE(S)"
    if result.posible_count:
        status += f", {result.posible_count} POSIBLE(S)"
    print(f"\n{result.source}: {status}")
    print(f"Diapositivas: {result.total_slides}\n")
    for issue in result.issues:
        print(f"  [{issue.severity.label}] [Diapositiva {issue.slide_number}] {issue.category}: {issue.message}")
        if issue.element:
            print(f"    Elemento: {issue.element}")
        if issue.location:
            print(f"    Ubicación: {issue.location}")
        print(f"    Esperado: {issue.expected}")
        print(f"    Actual:   {issue.actual}")
        if issue.text_preview:
            print(f"    Texto:    «{issue.text_preview}»")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Validar presentación contra manual de identidad ADG")
    subparsers = parser.add_subparsers(dest="command", required=True)

    pdf_parser = subparsers.add_parser("pdf", help="Validar archivo PDF")
    pdf_parser.add_argument("path", type=Path, help="Ruta al archivo PDF")

    slides_parser = subparsers.add_parser("slides", help="Validar Google Slides")
    slides_parser.add_argument("url_or_id", help="URL o ID de la presentación")

    parser.add_argument("--json", action="store_true", help="Salida en JSON")
    args = parser.parse_args()

    if args.command == "pdf":
        if not args.path.exists():
            print(f"Error: no se encontró {args.path}", file=sys.stderr)
            sys.exit(1)
        result = validate_pdf(args.path)
    else:
        try:
            result = validate_slides(args.url_or_id)
        except FileNotFoundError as exc:
            print(f"Error de autenticación Google: {exc}", file=sys.stderr)
            sys.exit(2)
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(2)

    print_result(result, args.json)
    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
