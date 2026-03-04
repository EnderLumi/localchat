import argparse
import sys
from uuid import uuid4

from localchat.client.UIImpl.simple import SimpleUI
from localchat.client.logicImpl import TcpChatInformation, TcpClientLogic
from localchat.client.logicImpl.testing import TestLogic
from localchat.config.defaults import DEFAULT_HOST, DEFAULT_PORT


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
    start.add_argument(
        "--server-host",
        default=DEFAULT_HOST,
        help="bootstrap server host for tcp mode (default: 0.0.0.0)",
    )
    start.add_argument(
        "--server-port",
        type=int,
        default=DEFAULT_PORT,
        help=f"bootstrap server port for tcp mode (default: {DEFAULT_PORT})",
    )
    start.add_argument(
        "--server-name",
        default="default-server",
        help="bootstrap server name shown in server search for tcp mode",
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

    if args.server_port <= 0 or args.server_port > 65535:
        parser.error("--server-port must be in range 1..65535")

    logic = TcpClientLogic()
    bootstrap_info = TcpChatInformation(
        uuid4(),
        args.server_name,
        args.server_host,
        args.server_port,
    )
    logic.create_chat(bootstrap_info, online=True, port=args.server_port)
    return _wire_and_run(logic)

if __name__ == "__main__":
    raise SystemExit(main())
