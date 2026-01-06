import shutil

from datadog_checks.base import AgentCheck


class Helloworld2TimeMachineDiskSpace(AgentCheck):
    """
    Datadog custom check for Time Machine disk space.

    Emits:
      - helloworld2.timemachine.disk.total_bytes
      - helloworld2.timemachine.disk.used_bytes
      - helloworld2.timemachine.disk.free_bytes
      - helloworld2.timemachine.disk.used_percent
      - service check helloworld2.timemachine.disk.accessible (OK/CRITICAL)
    """

    def check(self, instance):
        mountpoint = instance.get("mountpoint", "/Volumes/SEAGATE TIME MACHINE 5T")
        tags = list(instance.get("tags", []))
        tags.append(f"mountpoint:{mountpoint}")

        try:
            usage = shutil.disk_usage(mountpoint)

            self.gauge("helloworld2.timemachine.disk.total_bytes", usage.total, tags=tags)
            self.gauge("helloworld2.timemachine.disk.used_bytes", usage.used, tags=tags)
            self.gauge("helloworld2.timemachine.disk.free_bytes", usage.free, tags=tags)
            self.gauge("helloworld2.timemachine.disk.used_percent", (usage.used / usage.total) * 100, tags=tags)

            self.service_check("helloworld2.timemachine.disk.accessible", self.OK, tags=tags)

        except Exception as e:
            self.service_check(
                "helloworld2.timemachine.disk.accessible",
                self.CRITICAL,
                message=str(e),
                tags=tags,
            )

