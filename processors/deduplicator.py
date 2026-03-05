import json
import logging
import os
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "state", "seen_posts.json")
MAX_AGE_DAYS = 14


class Deduplicator:
    def __init__(self, state_file: str = STATE_FILE):
        self.state_file = os.path.abspath(state_file)
        self._state: dict = {"version": 1, "last_updated": None, "seen": {}}

    def load(self) -> None:
        if not os.path.exists(self.state_file):
            logger.warning("State file not found, starting fresh: %s", self.state_file)
            return
        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)
            if isinstance(data.get("seen"), dict):
                self._state = data
                logger.info("Loaded %d seen IDs from state file", len(self._state["seen"]))
            else:
                logger.warning("State file has unexpected format, starting fresh")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load state file (%s), starting fresh", e)

    def is_seen(self, opp_id: str) -> bool:
        return opp_id in self._state["seen"]

    def mark_seen(self, opp_id: str) -> None:
        self._state["seen"][opp_id] = datetime.now(timezone.utc).isoformat()

    def save(self) -> None:
        self.prune_old_entries()
        self._state["last_updated"] = datetime.now(timezone.utc).isoformat()
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        try:
            with open(self.state_file, "w") as f:
                json.dump(self._state, f, indent=2)
            logger.info("Saved %d seen IDs to state file", len(self._state["seen"]))
        except OSError as e:
            logger.error("Failed to save state file: %s", e)

    def prune_old_entries(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
        before = len(self._state["seen"])
        self._state["seen"] = {
            k: v
            for k, v in self._state["seen"].items()
            if _parse_dt(v) > cutoff
        }
        pruned = before - len(self._state["seen"])
        if pruned:
            logger.info("Pruned %d old entries from state file", pruned)


def _parse_dt(iso_str: str) -> datetime:
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return datetime.min.replace(tzinfo=timezone.utc)
