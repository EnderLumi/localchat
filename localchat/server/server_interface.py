from localchat.client.client_interface import ChatInterface
from localchat.server.commands import ServerCommandHandler

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.output import create_output
    from prompt_toolkit.patch_stdout import patch_stdout
except ImportError:
    PromptSession = None
    patch_stdout = None
    create_output = None


class ServerInterface:
    def __init__(self, client, use_prompt_toolkit):
        self.client = client
        self.use_prompt_toolkit = use_prompt_toolkit
        self.start(client, use_prompt_toolkit)
        self.closed = False

    def start(self, client, use_prompt_toolkit):
        client_ui = ChatInterface(client, use_prompt_toolkit)
        client_ui.start()
        if self.use_prompt_toolkit:
            self._serverchat_loop_prompt_toolkit()
        else:
            self._serverchat_loop_basic()
        """
        if self.use_prompt_toolkit:
            self._serverchat_loop_prompt_toolkit()
        else:
            self._serverchat_loop_basic()
        """

    def _serverchat_loop_prompt_toolkit(self):
        session = PromptSession('> ')
        with patch_stdout():
            while True:
                msg = session.prompt()
                self.command_handler(msg)
                if self.closed is True:
                    break

    def _serverchat_loop_basic(self):
        while True:
            msg = input()
            self.command_handler(msg)
            if self.closed is True:
                break

    def command_handler(self, msg, closed = None):
        if msg.lower() in ("localchat stop", "localchat close", "localchat exit", "localchat quit"):
            self.closed = True
        if msg.startswith("/"):
            ServerCommandHandler(msg)
        else:
            return
