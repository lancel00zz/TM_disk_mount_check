import os
import subprocess
from datadog_checks.base import AgentCheck


class TimeMachineMountCheck(AgentCheck):
    def check(self, instance):
        mountpoint = instance.get("mountpoint", "/Volumes/SEAGATE TIME MACHINE 5T")
        tags = instance.get("tags", [])
        tags = list(tags) + [f"mountpoint:{mountpoint}"]

        # 1) Quick path existence check (cheap)
        path_exists = os.path.isdir(mountpoint)

        # 2) Stronger check: confirm it's in the mount table (prevents false positives)
        is_mounted = 0
        try:
            out = subprocess.check_output(["/sbin/mount", "-p"], text=True)
            # mount -p includes mountpoint as a field; look for exact mountpoint token
            for line in out.splitlines():
                if f" {mountpoint} " in f" {line} ":
                    is_mounted = 1
                    break
        except Exception as e:
            # If we can't query mounts, mark the check itself as critical (different from "disk missing")
            self.service_check("timemachine.mount.check", self.CRITICAL, message=str(e), tags=tags)
            return

        # If the path exists but isn't mounted, treat as not mounted.
        mounted = 1 if (path_exists and is_mounted) else 0

        # Metric: stable 0/1 signal every run
        self.gauge("timemachine.disk_mounted", mounted, tags=tags)

        # Service check: nice for straightforward monitors
        status = self.OK if mounted == 1 else self.CRITICAL
        msg = "Time Machine disk is mounted" if mounted == 1 else "Time Machine disk is NOT mounted"
        self.service_check("timemachine.disk.mounted", status, message=msg, tags=tags)