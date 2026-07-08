"""CLI do Post Engine."""
from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Post Engine")
    parser.add_argument(
        "--gui",
        action="store_true",
        help="executa a interface React em um servidor HTTP local",
    )
    parser.add_argument("--gui-host", default="127.0.0.1")
    parser.add_argument("--gui-port", type=int, default=8765)
    args = parser.parse_args(argv)
    if args.gui:
        from gui import run_gui_server

        run_gui_server(host=args.gui_host, port=args.gui_port)
        return
    raise SystemExit("TUI removida. Use --gui para a interface web.")


if __name__ == "__main__":
    main()
