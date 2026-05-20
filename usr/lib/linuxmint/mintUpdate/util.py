import threading

import gi
from gi.repository import Gio, GLib


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
