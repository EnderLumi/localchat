import argparse
import sys

from localchat.client.UIImpl.simple import SimpleUI
from localchat.client.logicImpl import TcpClientLogic
from localchat.client.logicImpl.testing import TestLogic


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="localchat", description="localchat CLI")
    sub = parser.add_subparsers(dest="command")

    start = sub.add_parser("start", help="start localchat")
    start.add_argument(
        "--mode",
        choices=["tcp", "test"],
        default="tcp",
        help="runtime mode (default: tcp)",
    )

    return parser


def _wire_and_run(logic) -> int:
    ui = SimpleUI()
    logic.set_ui(ui)
    ui.set_logic(logic)
    logic.start()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    command = args.command or "start"
    if command != "start":
        parser.error("unsupported command")

    if args.mode == "test":
        logic = TestLogic()
        return _wire_and_run(logic)

    logic = TcpClientLogic()
    return _wire_and_run(logic)


if __name__ == "__main__":
    raise SystemExit(main())
