import unittest

from npcjason_app.scheduler import ManagedTkScheduler
from tests.helpers import FakeLogger, FakeRoot


class SchedulerTests(unittest.TestCase):
    def test_repeating_loop_logs_exception_and_keeps_rescheduling(self):
        root = FakeRoot()
        logger = FakeLogger()
        scheduler = ManagedTkScheduler(root, logger=logger)
        call_count = {"value": 0}

        def loop():
            call_count["value"] += 1
            if call_count["value"] == 1:
                raise RuntimeError("boom")
            if call_count["value"] == 3:
                return None
            return 25

        scheduler.schedule_loop("heartbeat", loop, initial_delay_ms=10, default_delay_ms=40, owner="tests")

        root.run_next()
        self.assertEqual(1, call_count["value"])
        self.assertEqual(["Loop callback 'heartbeat' failed"], logger.messages["exception"])
        self.assertTrue(root.scheduled)

        root.run_next()
        self.assertEqual(2, call_count["value"])
        self.assertTrue(root.scheduled)

        root.run_next()
        self.assertEqual(3, call_count["value"])
        self.assertFalse(root.scheduled)

    def test_schedule_replaces_existing_job_with_same_name(self):
        root = FakeRoot()
        scheduler = ManagedTkScheduler(root)
        calls = []

        scheduler.schedule("save", 10, lambda: calls.append("old"), owner="tests")
        scheduler.schedule("save", 15, lambda: calls.append("new"), owner="tests")

        self.assertEqual(1, len(root.scheduled))
        root.run_next()
        self.assertEqual(["new"], calls)

    def test_dispatch_queue_runs_on_dispatch_loop(self):
        root = FakeRoot()
        scheduler = ManagedTkScheduler(root)
        values = []

        scheduler.start()
        scheduler.dispatch(values.append, "ran")
        root.run_next()

        self.assertEqual(["ran"], values)
        self.assertTrue(root.scheduled)

    def test_shutdown_cancels_all_jobs(self):
        root = FakeRoot()
        scheduler = ManagedTkScheduler(root)

        scheduler.schedule("save", 10, lambda: None, owner="tests")
        scheduler.schedule_loop("heartbeat", lambda: 50, owner="tests")
        scheduler.shutdown()

        self.assertFalse(root.scheduled)

    def test_describe_jobs_reports_run_and_failure_counts(self):
        root = FakeRoot()
        scheduler = ManagedTkScheduler(root)
        call_count = {"value": 0}

        def loop():
            call_count["value"] += 1
            if call_count["value"] == 1:
                raise RuntimeError("boom")
            return 25

        scheduler.schedule_loop("heartbeat", loop, default_delay_ms=25, error_delay_ms=25, owner="tests")
        root.run_next()
        description = scheduler.describe_jobs()

        self.assertEqual(1, len(description))
        self.assertEqual("heartbeat", description[0]["name"])
        self.assertEqual(1, description[0]["failure_count"])
        self.assertEqual(50, description[0]["last_delay_ms"])

    def test_dispatch_warns_when_queue_depth_grows(self):
        root = FakeRoot()
        logger = FakeLogger()
        scheduler = ManagedTkScheduler(root, logger=logger, dispatch_warn_depth=8)
        scheduler.start()

        for _ in range(8):
            scheduler.dispatch(lambda: None)

        self.assertTrue(any("Dispatch queue depth is high" in message for message in logger.messages["warning"]))


if __name__ == "__main__":
    unittest.main()
