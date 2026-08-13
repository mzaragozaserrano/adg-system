#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.validators import validate_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description="Validar PDF contra manual de identidad ADG")
    parser.add_argument("pdf", type=Path, help="Ruta al archivo PDF")
    parser.add_argument("--json", action="store_true", help="Salida en JSON")
    args = parser.parse_args()

    if not args.pdf.exists():
        print(f"Error: no se encontró {args.pdf}", file=sys.stderr)
        sys.exit(1)

    result = validate_pdf(args.pdf)

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        status = "CONFORME" if result.passed else f"{result.grave_count} GRAVE(S)"
        if result.posible_count:
            status += f", {result.posible_count} POSIBLE(S)"
        print(f"\n{args.pdf.name}: {status}")
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

    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
