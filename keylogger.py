# pip install pynput
#pip install psutil

#!/usr/bin/env python3
"""
keylogger.py  (friendly toolkit)

Two safe tools:
  1) typing  - consent-based typing session logger (requires pynput)
  2) audit   - snapshot current processes + network connections (requires psutil)

If no command-line mode is given, the script shows an interactive menu.
"""

import argparse
import pathlib
import time
from datetime import datetime
import csv
import threading
import sys

# Optional imports: check availability and give friendly error if missing
try:
    from pynput import keyboard
except Exception:
    keyboard = None

try:
    import psutil
except Exception:
    psutil = None


# -----------------------
# Utility helpers
# -----------------------
def safe_timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_out_dir(path: str):
    p = pathlib.Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


# -----------------------
# Typing session logger
# -----------------------
def run_typing_session(out_dir="outputs", filename_prefix="typing_session_"):
    if keyboard is None:
        print("ERROR: pynput is required for typing mode. Install with: pip install pynput")
        return

    out_dir = ensure_out_dir(out_dir)
    filename = f"{filename_prefix}{safe_timestamp()}.txt"
    out_path = out_dir / filename

    session_active = {"value": False}

    def on_press(key):
        # Only log while session_active is True
        if not session_active["value"]:
            return

        try:
            char = key.char
        except AttributeError:
            char = f"<{getattr(key, 'name', str(key))}>"

        # Print to stdout and append to file
        print(char, end="", flush=True)
        try:
            with out_path.open("a", encoding="utf-8") as f:
                f.write(char)
        except Exception as e:
            print("\nFailed to write keystroke to file:", e)

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    print("\n--- CONSENT REQUIRED ---")
    print("This typing session will record keystrokes to a local file ONLY while you explicitly start the session.")
    resp = input("Type 'yes' to CONFIRM and start the session (or anything else to cancel): ").strip().lower()
    if resp not in ("y", "yes"):
        print("Session cancelled by user.")
        listener.stop()
        return

    # Start session
    session_active["value"] = True
    print(f"Session started. Typing will be saved to: {out_path.resolve()}")
    print("Press ESC to stop the session.")

    # Wait for ESC to stop
    try:
        with keyboard.Events() as events:
            for event in events:
                if isinstance(event, keyboard.Events.Press):
                    k = getattr(event, "key", None)
                    name = getattr(k, "name", None)
                    if name == "esc" or str(k) == "Key.esc":
                        break
    except KeyboardInterrupt:
        print("\nInterrupted by user (Ctrl-C).")
    finally:
        session_active["value"] = False
        listener.stop()
        print("\nSession stopped. Saved to:", out_path.resolve())


# -----------------------
# Process snapshot (audit)
# -----------------------
def get_proc_connections(proc):
    """
    Try preferred API proc.net_connections(); fall back to proc.connections() if needed.
    """
    try:
        return proc.net_connections(kind="inet")
    except AttributeError:
        return proc.connections(kind="inet")


def snapshot_processes(out_dir="outputs", prefix="process_snapshot_"):
    if psutil is None:
        print("ERROR: psutil is required for audit mode. Install with: pip install psutil")
        return

    out_dir = ensure_out_dir(out_dir)
    filename = f"{prefix}{safe_timestamp()}.csv"
    out_file = out_dir / filename

    header = ["timestamp", "pid", "name", "exe", "username", "status", "connections_summary"]

    try:
        with out_file.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header)
            timestamp = datetime.now().isoformat(timespec="seconds")
            for proc in psutil.process_iter(["pid", "name", "exe", "username", "status"]):
                try:
                    conns = get_proc_connections(proc)
                    conn_str = "; ".join(
                        f"{getattr(c, 'laddr', '')}->{getattr(c, 'raddr', '')}({getattr(c, 'status', '')})"
                        for c in conns if getattr(c, "raddr", None)
                    )
                    writer.writerow([
                        timestamp,
                        proc.info.get("pid"),
                        proc.info.get("name"),
                        proc.info.get("exe"),
                        proc.info.get("username"),
                        proc.info.get("status"),
                        conn_str
                    ])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # skip processes we cannot inspect
                    continue
    except OSError as e:
        print("Failed to write snapshot:", e)
        return

    print("Snapshot saved to", out_file.resolve())


# -----------------------
# Interactive menu (fallback)
# -----------------------
def interactive_menu():
    print("No mode provided. Choose an option:")
    print("  1) typing  - Consent-based typing session logger")
    print("  2) audit   - Take process & network snapshot")
    print("  q) Quit")

    choice = input("Enter 1, 2, or q: ").strip().lower()
    if choice == "1":
        run_typing_session()
    elif choice == "2":
        snapshot_processes()
    else:
        print("Exiting.")


# -----------------------
# CLI
# -----------------------
def main():
    parser = argparse.ArgumentParser(
        description="Toolkit: consent typing logger + process snapshot (safe, Python-only)."
    )
    sub = parser.add_subparsers(dest="mode")  # removed required=True to allow fallback

    p_typing = sub.add_parser("typing", help="Consent-based typing session logger (pynput required)")
    p_typing.add_argument("--out-dir", default="outputs", help="Directory to write typing logs")
    p_typing.add_argument("--prefix", default="typing_session_", help="Filename prefix for typing logs")

    p_audit = sub.add_parser("audit", help="Take a snapshot of current processes and network connections (psutil required)")
    p_audit.add_argument("--out-dir", default="outputs", help="Directory to write audit CSVs")
    p_audit.add_argument("--prefix", default="process_snapshot_", help="Filename prefix for snapshots")

    args = parser.parse_args()

    if args.mode == "typing":
        run_typing_session(out_dir=args.out_dir, filename_prefix=args.prefix)
    elif args.mode == "audit":
        snapshot_processes(out_dir=args.out_dir, prefix=args.prefix)
    else:
        # no mode provided -> interactive menu
        interactive_menu()


if __name__ == "__main__":
    main()
