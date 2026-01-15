

class UI:
    """
    Die UI-Klasse ist eine austauschbare Komponente, die
    die Kommunikation zwischen der Client-Logik und dem
    Benutzer abwickelt.

    Der Lebenszyklus einer UI-Klasse läuft wie folgt:

    1. 'set_logic' der Client-UI wird extern mit einer Instanz von Client-Logik als Argument aufgerufen.
    2. Die Client-Logik wird extern über 'start' gestartet.
    3. Die Client-Logik ruft 'start' der Client-UI auf, sobald sie bereit ist Befehle von dieser zu empfangen.
    4. Die Client-UI ruft 'ui_initialized' in der Client-Logik auf, sobald sie bereit ist
       auf Events von der Client-Logik zu reagieren.

    Die Client-UI kann nun über die Client-Logik Chats beitreten,
    Nachrichten senden, etc. Sobald die UI bereit ist das Programm zu beenden,
    muss sie 'shutdown' in der Client-Logik aufrufen.
    Die Client-UI muss jedoch weiter auf Events aus der Client-Logik reagieren,
    bis diese wiederum 'shutdown' in der Client-UI aufruft.
    Dann kann die Client-UI ihre Arbeit einstellen.
    """

    def __init__(self): ...

    def set_logic(self, logic : object): ...

    def start(self) -> None: ...
    def shutdown(self) -> None: ...
