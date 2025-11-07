# Terminal interface for text input
from localchat.client import client

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.output import create_output
    from prompt_toolkit.patch_stdout import patch_stdout
except ImportError:
    PromptSession = None
    patch_stdout = None
    create_output = None

class ChatInterface:
    def __init__(self, client, use_prompt_toolkit = False):
        self.client = client
        self.use_prompt_toolkit = use_prompt_toolkit
        self.closed = False

    def start(self):
        if self.use_prompt_toolkit:
            self._interactive_loop_prompt_toolkit()
        else:
            self._interactive_loop_basic()


    def _interactive_loop_prompt_toolkit(self):
        session = PromptSession('> ')
        with patch_stdout():
            while True:
                msg = session.prompt()
                self.input_handler(msg)
                if self.closed == True:
                    break

    def _interactive_loop_basic(self):
        while True:
            msg = input()
            self.input_handler(msg)
            if self.closed == True:
                break


    def input_handler(self, msg, closed=None):
            if msg.lower() in ("localchat stop", "localchat close", "localchat exit", "localchat quit"):
                self.closed = True
            if msg.startswith("/"):
                print("bis jetzt noch nicht implementiert")
            else:
                self.client.send_message(msg)

