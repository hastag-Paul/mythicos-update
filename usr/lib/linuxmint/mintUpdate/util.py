import threading

import gi
from gi.repository import Gio, GLib


# Used as a decorator to run things in the background
def _async(func):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread
    return wrapper


# Used as a decorator to run things in the main loop, from another thread
def _idle(func):
    def wrapper(*args):
        GLib.idle_add(func, *args)
    return wrapper


def on_battery():
    # Query UPower over the system D-Bus. Works for both root (system services)
    # and user contexts; UPower's default policy allows property reads from any uid.
    # Returns False if UPower is unavailable (fail open — assume AC connected).
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        proxy = Gio.DBusProxy.new_sync(
            bus, Gio.DBusProxyFlags.NONE, None,
            "org.freedesktop.UPower",
            "/org/freedesktop/UPower",
            "org.freedesktop.UPower",
            None)
        prop = proxy.get_cached_property("OnBattery")
        if prop is None:
            return False
        return prop.unpack()
    except GLib.Error:
        return False
