"""
Session-level update routines for Cinnamon spices and Flatpaks.

Called by mintUpdate.py from a forked subprocess on the session-update
timer so one-shot imports (cinnamon.UpdateManager, mintcommon.installer)
don't grow the main process's memory footprint.
"""

import gettext
import os
import subprocess
import sys
import time

import gi
gi.require_version('Notify', '0.7')
from gi.repository import Gio, Notify
from multiprocess import Process

import xapp.os

_ = gettext.gettext

SUBPROCESS_TIMEOUT = 600
OVERALL_TIMEOUT = 60 * 60


def process_cinnamon_spices(settings):
    if not settings.get_boolean("auto-update-cinnamon-spices"):
        return
    if not os.path.exists("/usr/bin/cinnamon"):
        return
    print("Updating Cinnamon Spices")
    try:
        import cinnamon
        updater = cinnamon.UpdateManager()
        updater.refresh_all_caches()
        updates = updater.get_updates()
        if not updates:
            return

        msg = _("The following spices were automatically updated:") + "\n"
        need_cinnamon_restart = False
        for update in updates:
            updater.upgrade(update)
            msg += "\n- %s (%s)" % (update.uuid, update.spice_type)
            try:
                if updater.spice_is_enabled(update):
                    need_cinnamon_restart = True
            except:
                need_cinnamon_restart = True

        if need_cinnamon_restart and xapp.os.is_desktop_cinnamon():
            subprocess.call(["cinnamon-dbus-command", "RestartCinnamon", "0"])
            time.sleep(10) # Give cinnamon some time, otherwise it won't show our notification.
            notification = Notify.Notification.new(
                _("Cinnamon was restarted"), msg, "cinnamon-symbolic")
            notification.set_urgency(2)
            notification.set_timeout(Notify.EXPIRES_NEVER)
            notification.show()
    except Exception as e:
        print("An error occurred while updating cinnamon spices: %s" % e, file=sys.stderr)


def process_flatpaks(settings):
    if not os.path.exists("/usr/bin/flatpak"):
        return

    # Remove unused flatpak runtimes first so we don't update unused ones.
    try:
        print("Purging unused flatpaks")
        out = subprocess.run(
            ["flatpak", "uninstall", "--unused", "-y"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=SUBPROCESS_TIMEOUT)
        print(out.stdout.decode())
    except Exception as e:
        print("An error occurred while purging unused flatpaks: %s" % e, file=sys.stderr)

    if settings.get_boolean("auto-update-flatpaks"):
        print("Updating flatpaks")
        try:
            out = subprocess.run(
                ["flatpak", "update", "-y"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=SUBPROCESS_TIMEOUT)
            print(out.stdout.decode())
        except Exception as e:
            print("An error occurred while updating flatpaks: %s" % e, file=sys.stderr)

    # Install theme if needed
    try:
        gi.require_version('Flatpak', '1.0')
        from gi.repository import Flatpak
        from mintcommon.installer import _flatpak

        theme_refs = _flatpak.get_updated_theme_refs()
        if theme_refs is not None:
            print("Installing new theme to match local theme")
            for ref in theme_refs:
                out = subprocess.run(
                    ["flatpak", "install", "-y", "--system",
                     ref.get_remote_name(), ref.get_name()],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    timeout=SUBPROCESS_TIMEOUT)
                print(out.stdout.decode())
    except Exception as e:
        print("An error occurred checking for a new flatpak theme: %s" % e, file=sys.stderr)


def run_all(settings):
    process_cinnamon_spices(settings)
    process_flatpaks(settings)


def run():
    """Run session-update routines in a forked subprocess so one-shot imports
    don't grow the caller's memory footprint. Returns None on success, or an
    error string."""
    process = Process(target=_run_in_child)
    process.start()
    process.join(timeout=OVERALL_TIMEOUT)
    if process.is_alive():
        process.terminate()
        process.join(timeout=10)
        if process.is_alive():
            process.kill()
        return "Automatic Flatpak/Spice updates exceeded timeout; terminated"
    if process.exitcode != 0:
        return f"Automatic Flatpak/Spice updates child exited with code {process.exitcode}"
    return None


def _run_in_child():
    # Re-init Notify so the child gets its own session-bus connection (the
    # inherited one shares an FD with the parent post-fork), and create a
    # fresh Gio.Settings.
    Notify.init("Update Manager")
    settings = Gio.Settings(schema_id="com.linuxmint.updates")
    run_all(settings)
