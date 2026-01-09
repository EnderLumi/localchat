from localchat.util import Chat, User, UserMessage
from localchat.util.event import EventListener, Event


class MessagePostedListener(EventListener[UserMessage]):
    def __init__(self, chat: Chat):
        self._chat = chat

    def on_event(self, event: Event[UserMessage]):
        user_message = event.value()
        if user_message.sender() == self._chat.get_server_user():
            print(f"[SERVER] (public announcement): {user_message.message()}")
        else:
            print(f"{user_message.sender().get_name()} said: {user_message.message()}")


class ReceivedPrivateMessageListener(EventListener[UserMessage]):
    def __init__(self, chat: Chat):
        self._chat = chat

    def on_event(self, event: Event[UserMessage]):
        user_message = event.value()
        if user_message.sender() == self._chat.get_server_user():
            print(f"[SERVER] (directly to you): {user_message.message()}")
        else:
            print(f"{user_message.sender().get_name()} said to you: {user_message.message()}")


class UserJoinedListener(EventListener[User]):
    def __init__(self): ...

    def on_event(self, event: Event[User]):
        print(f"User Joined: {event.value().get_name()}")


class UserLeftListener(EventListener[User]):
    def __init__(self): ...

    def on_event(self, event: Event[User]):
        print(f"User Left: {event.value().get_name()}")


def on_help():
    print("""say  -post a message to the chat""")


class SimpleChatUI(EventListener[str]):
    def __init__(self, chat: Chat):
        super(EventListener,self).__init__()
        self.chat = chat
        self.message_posted_listener = MessagePostedListener(self.chat)
        self.user_send_private_message_listener = ReceivedPrivateMessageListener(self.chat)
        self.user_joined_listener = UserJoinedListener()
        self.user_left_listener = UserLeftListener()

    def _activate_listeners(self):
        self.chat.on_user_posted_message().add_listener(self.message_posted_listener)
        self.chat.on_user_send_private_message().add_listener(self.user_send_private_message_listener)
        self.chat.on_user_joined().add_listener(self.user_joined_listener)
        self.chat.on_user_left().add_listener(self.user_left_listener)

    def _deactivate_listeners(self):
        self.chat.on_user_posted_message().remove_listener(self.message_posted_listener)
        self.chat.on_user_send_private_message().remove_listener(self.user_send_private_message_listener)
        self.chat.on_user_joined().remove_listener(self.user_joined_listener)
        self.chat.on_user_left().remove_listener(self.user_left_listener)

    def join(self, appearance: User):
        self._activate_listeners()
        try:
            self.chat.join(appearance)
        except IOError as e:
            self._deactivate_listeners()
            raise

    def leave(self):
        try:
            self.chat.leave()
        finally:
            self._deactivate_listeners()

    def on_event(self, event : Event[str]):
        raw_command = event.value()
        if raw_command.strip() == "": return
        raw_command_parts = raw_command.split()
        command = raw_command_parts[0]
        args = raw_command_parts[1:]
        if command == "help": on_help()
        elif command == "say":
            message = " ".join(args)
            self.chat.post_message(message)
            print(f"You say: \"{message}\"")

    def update_appearance(self, appearance: User):
        self.chat.update_appearance(appearance)



