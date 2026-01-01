import os
import subprocess

from datadog_checks.base import AgentCheck


class Helloworld2TimeMachineMount(AgentCheck):
    def check(self, instance):
        mountpoint = instance.get("mountpoint", "/Volumes/SEAGATE TIME MACHINE 5T")
        tags = list(instance.get("tags", []))
        tags.append(f"mountpoint:{mountpoint}")

        # Always emit heartbeat (for monitoring)
        self.gauge("helloworld2.timemachine.heartbeat", 1, tags=tags)

        # Default
        mounted = 0

        try:
            out = subprocess.check_output(["/sbin/mount"], text=True)
            mounted = 1 if any(f" on {mountpoint} (" in line for line in out.splitlines()) else 0
        except Exception as e:
            self.service_check("helloworld2.timemachine.mount.check", self.CRITICAL, message=str(e), tags=tags)
            mounted = 0  # keep going, still emit metric

        # Always emit
        self.gauge("helloworld2.timemachine.disk_mounted", mounted, tags=tags)



        # Optional: service check that mirrors the state
        status = self.OK if mounted else self.CRITICAL
        msg = "Time Machine disk is mounted" if mounted else "Time Machine disk is NOT mounted"
        self.service_check("helloworld2.timemachine.disk.mounted", status, message=msg, tags=tags)