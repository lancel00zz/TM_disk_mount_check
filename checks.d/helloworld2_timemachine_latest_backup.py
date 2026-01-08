import re
import subprocess
from datetime import datetime

from datadog_checks.base import AgentCheck


class Helloworld2TimeMachineLatestBackup(AgentCheck):
    """
    Datadog custom check for macOS Time Machine.

    Emits:
      - helloworld2.timemachine.latest_backup_heartbeat (always 1)
      - helloworld2.timemachine.latest_backup_seconds (seconds since latest completed backup to external disk)
      - helloworld2.timemachine.latest_snapshot_seconds (seconds since latest local snapshot)
      - service check helloworld2.timemachine.latest_backup (OK/CRITICAL)
      - service check helloworld2.timemachine.latest_snapshot (OK/CRITICAL)

    The two metrics answer different questions:
      - latest_backup_seconds: "How durable is my backup?" (external disk persistence)
      - latest_snapshot_seconds: "Is Time Machine logically running?" (local snapshot freshness)
    """

    # Matches Time Machine timestamps like: 2025-09-30-012615
    TM_TS_RE = re.compile(r"(\d{4}-\d{2}-\d{2}-\d{6})")

    # Matches local snapshot dates like: 2025-09-30-012615 (from listlocalsnapshotdates)
    SNAPSHOT_TS_RE = re.compile(r"(\d{4}-\d{2}-\d{2}-\d{6})")

    def check(self, instance):
        tags = list(instance.get("tags", []))

        # Heartbeat: proves the check is executing and can emit metrics
        self.gauge("helloworld2.timemachine.latest_backup_heartbeat", 1, tags=tags)

        # Get current time once for consistent calculations
        now = datetime.now()

        # --- External disk backup age ---
        latest_backup_seconds = self._get_latest_backup_age(tags, now)
        self.gauge("helloworld2.timemachine.latest_backup_seconds", latest_backup_seconds, tags=tags)

        # --- Local snapshot age ---
        latest_snapshot_seconds = self._get_latest_snapshot_age(tags, now)
        self.gauge("helloworld2.timemachine.latest_snapshot_seconds", latest_snapshot_seconds, tags=tags)

    def _get_latest_backup_age(self, tags, now):
        """
        Get the age of the latest backup on the external Time Machine disk.
        Returns seconds since last backup, or -1 if unknown.
        """
        try:
            # Example output:
            # /Volumes/.timemachine/<UUID>/2025-09-30-012615.backup/2025-09-30-012615.backup
            out = subprocess.check_output(
                ["/usr/bin/tmutil", "latestbackup"],
                text=True
            ).strip()

            m = self.TM_TS_RE.search(out)
            if not m:
                raise ValueError(f"Could not find a Time Machine timestamp in output: {out}")

            ts = m.group(1)  # e.g. 2025-09-30-012615
            backup_dt = datetime.strptime(ts, "%Y-%m-%d-%H%M%S")
            age_seconds = int((now - backup_dt).total_seconds())

            if age_seconds < 0:
                age_seconds = 0

            self.service_check("helloworld2.timemachine.latest_backup", self.OK, tags=tags)
            return age_seconds

        except Exception as e:
            self.service_check(
                "helloworld2.timemachine.latest_backup",
                self.CRITICAL,
                message=str(e),
                tags=tags,
            )
            return -1

    def _get_latest_snapshot_age(self, tags, now):
        """
        Get the age of the latest local Time Machine snapshot.
        Returns seconds since last snapshot, or -1 if unknown.

        Local snapshots are stored on the main disk and created hourly.
        They represent Time Machine's "logical" operation even when the
        external disk is unavailable.
        """
        try:
            # tmutil listlocalsnapshotdates / outputs timestamps like:
            # 2025-09-30-012615
            # 2025-09-30-022615
            # (one per line, oldest first)
            out = subprocess.check_output(
                ["/usr/bin/tmutil", "listlocalsnapshotdates", "/"],
                text=True
            ).strip()

            if not out:
                raise ValueError("No local snapshots found")

            # Get all timestamps and find the most recent (last line)
            lines = out.strip().split("\n")
            # Filter to only lines that match the timestamp pattern
            timestamps = [line.strip() for line in lines if self.SNAPSHOT_TS_RE.match(line.strip())]

            if not timestamps:
                raise ValueError("No valid timestamps in local snapshots output")

            # Last one is the most recent
            latest_ts = timestamps[-1]
            snapshot_dt = datetime.strptime(latest_ts, "%Y-%m-%d-%H%M%S")
            age_seconds = int((now - snapshot_dt).total_seconds())

            if age_seconds < 0:
                age_seconds = 0

            self.service_check("helloworld2.timemachine.latest_snapshot", self.OK, tags=tags)
            return age_seconds

        except Exception as e:
            self.service_check(
                "helloworld2.timemachine.latest_snapshot",
                self.CRITICAL,
                message=str(e),
                tags=tags,
            )
            return -1