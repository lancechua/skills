"""
Sends a notification to a person. The actual delivery mechanism is
host-specific (this skill doesn't know what's installed on your machine), so
it's configured in config.json next to the database. Supported methods:

  "shell"   - runs a shell command template with {message} substituted.
              e.g. on Linux with notify-send:
                "notify-send \"Cycle update\" \"{message}\""
              e.g. calling a personal ntfy.sh topic:
                "curl -s -d \"{message}\" ntfy.sh/your-private-topic"

  "webhook" - POSTs {"message": "..."} as JSON to a URL. Works well with
              ntfy.sh, Pushover proxies, Telegram-bot-to-webhook bridges,
              Home Assistant, etc. Set "url" in the profile's config.

  "stdout"  - just prints the message. This is the default so the skill
              works out of the box; swap it out once you know how you want
              to actually be notified on your machine.

config.json shape (lives at $MCC_DATA_DIR/config.json):
{
  "profiles": {
    "alex": {"method": "shell", "command": "notify-send \"{title}\" \"{message}\""},
    "sam":  {"method": "webhook", "url": "https://ntfy.sh/private-topic"}
  }
}

If a profile has no entry, falls back to "stdout".
"""

import json
import os
import subprocess
import urllib.request

import db


def get_config_path():
    return os.path.join(db.get_data_dir(), "config.json")


# Default value for module-level compatibility
CONFIG_PATH = get_config_path()


def _load_config():
    path = get_config_path()
    if not os.path.exists(path):
        return {"profiles": {}}
    with open(path) as f:
        return json.load(f)


def send(profile_name, message, title="Cycle update"):
    config = _load_config()
    profile_config = config.get("profiles", {}).get(
        profile_name, {"method": "stdout"}
    )
    method = profile_config.get("method", "stdout")

    if method == "shell":
        cmd = profile_config["command"].format(message=message, title=title)
        subprocess.run(cmd, shell=True, check=False)
    elif method == "webhook":
        data = json.dumps({"message": message, "title": title}).encode()
        req = urllib.request.Request(
            profile_config["url"],
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:  # noqa
            print(f"[notify] webhook failed for {profile_name}: {e}")
    else:
        print(f"[notify -> {profile_name}] {title}: {message}")


def write_default_config_if_missing():
    path = get_config_path()
    if os.path.exists(path):
        return
    os.makedirs(db.get_data_dir(), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"profiles": {}}, f, indent=2)
