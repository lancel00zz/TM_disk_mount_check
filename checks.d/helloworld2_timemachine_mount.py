import subprocess

from datadog_checks.base import AgentCheck


class Helloworld2TimeMachineMount(AgentCheck):
    def check(self, instance):
        # Configure the Time Machine APFS Volume UUID (recommended over mountpoint name)
        volume_uuid = instance.get("volume_uuid", "AC05F583-4BDF-498A-AB2D-AB5A307869EC")

        tags = list(instance.get("tags", []))
        tags.append(f"volume_uuid:{volume_uuid}")

        # Always emit heartbeat (for monitoring)
        self.gauge("helloworld2.timemachine.heartbeat", 1, tags=tags)

        mounted = 0

        # On macOS, /sbin/mount output typically does NOT include the APFS Volume UUID.
        # diskutil is UUID-aware and is the most reliable way to check mount/presence.
        try:
            subprocess.check_output(
                ["/usr/sbin/diskutil", "info", volume_uuid],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            mounted = 1
        except Exception as e:
            # Keep going, still emit metrics + service checks
            self.service_check(
                "helloworld2.timemachine.mount.check",
                self.CRITICAL,
                message=f"diskutil info failed for UUID {volume_uuid}: {e}",
                tags=tags,
            )
            mounted = 0

        # Always emit
        self.gauge("helloworld2.timemachine.disk_mounted", mounted, tags=tags)

        # Service check mirrors the state
        status = self.OK if mounted else self.CRITICAL
        msg = "Time Machine disk is mounted" if mounted else "Time Machine disk is NOT mounted"
        self.service_check("helloworld2.timemachine.disk.mounted", status, message=msg, tags=tags)