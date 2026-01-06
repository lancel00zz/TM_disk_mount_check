import os
import re
import subprocess
from datetime import datetime, timezone

from datadog_checks.base import AgentCheck


class Helloworld2TimeMachineLatestBackup(AgentCheck):
    """
    Datadog custom check for macOS Time Machine.

    Emits:
      - helloworld2.timemachine.latest_backup_heartbeat (always 1)
      - helloworld2.timemachine.latest_backup_seconds (seconds since latest completed backup)
      - service check helloworld2.timemachine.latest_backup (OK/CRITICAL)
    """

    # Matches Time Machine timestamps like: 2025-09-30-012615
    TM_TS_RE = re.compile(r"(\d{4}-\d{2}-\d{2}-\d{6})")

    def check(self, instance):
        tags = list(instance.get("tags", []))

        # Heartbeat: proves the check is executing and can emit metrics
        self.gauge("helloworld2.timemachine.latest_backup_heartbeat", 1, tags=tags)

        latest_backup_seconds = -1  # -1 means "unknown / could not determine"

        try:
            # Example output can look like:
            # /Volumes/.timemachine/<UUID>/2025-09-30-012615.backup/2025-09-30-012615.backup
            out = subprocess.check_output(
                ["/usr/bin/tmutil", "latestbackup"],
                text=True
            ).strip()

            # Find a Time Machine timestamp anywhere in the output
            m = self.TM_TS_RE.search(out)
            if not m:
                raise ValueError(f"Could not find a Time Machine timestamp in output: {out}")

            ts = m.group(1)  # e.g. 2025-09-30-012615

            # NOTE: tmutil outputs timestamps in local time; for monitoring "age" this is fine.
            # If you want absolute timezone correctness, we can switch to filesystem metadata.
            backup_dt = datetime.strptime(ts, "%Y-%m-%d-%H%M%S")

            # Compute age in seconds (use local time consistently)
            now = datetime.now()
            latest_backup_seconds = int((now - backup_dt).total_seconds())

            if latest_backup_seconds < 0:
                # Guard against clock skew / timezone quirks
                latest_backup_seconds = 0

            # Service check OK: we successfully computed an age
            self.service_check("helloworld2.timemachine.latest_backup", self.OK, tags=tags)

        except Exception as e:
            # Service check CRITICAL: we could not compute an age
            self.service_check(
                "helloworld2.timemachine.latest_backup",
                self.CRITICAL,
                message=str(e),
                tags=tags,
            )

        # Always emit the metric, even on failure (-1)
        self.gauge("helloworld2.timemachine.latest_backup_seconds", latest_backup_seconds, tags=tags)