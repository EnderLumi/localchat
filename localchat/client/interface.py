# Terminal interface for text input

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.patch_stdout import patch_stdout
except ImportError:
    pass

class ChatInterface:
    def __init__(self, client, use_prompt_toolkit = False):
        self.client = client
        self.use_prompt_toolkit = use_prompt_toolkit

    def start(self):
        if self.use_prompt_toolkit:
            self._interactive_loop_promt_toolkit()
        else:
            self._interactive_loop_basic()

    def _interactive_loop_promt_toolkit(self):
        session = PromptSession('> ')
        with patch_stdout():
            while True:
                msg = session.prompt()
                if msg.lower() in ("/exit", "/quit", "/leave", "/close"):
                    break
                self.client.send_message(msg)

    def _interactive_loop_basic(self):
        while True:
            msg = input()
            if msg.lower() in ("/exit", "/quit", "/leave", "/close"):
                break
            self.client.send_message(msg)