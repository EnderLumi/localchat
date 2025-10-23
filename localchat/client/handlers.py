# Verarbeitung eingehender Pakete
def dispatch_packet(packet, display_func):
    ptype = packet.get('type')
    if ptype == 'public':
        handle_public(packet, display_func)
    elif ptype == 'system':
        handle_system(packet, display_func)
    else:
        display_func(f"[UNKNOWN PACKET TYPE] {ptype}")


def handle_public(packet, display_func):
    sender = packet.get('from')
    message = packet.get("payload", {}).get("message", "")
    display_func(f"{sender}: {message}")

def handle_system(packet, display_func):
    message = packet.get("payload", {}).get("message", "")
    display_func(f"{message}")