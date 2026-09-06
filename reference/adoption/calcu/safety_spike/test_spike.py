from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from spike import SafetyStore


class SafetySpikeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SafetyStore(self.path)
        self.assertTrue(self.store.seed(grant_id="g", grant_hash="h", lineage_id="L",
                                        session_id="s", hard_limit=2))

    def tearDown(self):
        self.store.close(); self.tmp.cleanup()

    def test_atomic_limit_and_fence_shared_by_concurrent_connections(self):
        results = []
        barrier = threading.Barrier(4, timeout=5)  # three workers plus the test thread
        def worker(i):
            db = SafetyStore(self.path); barrier.wait()
            results.append(db.admit(session_id="s", expected_generation=1,
                                    grant_id="g", grant_hash="h").outcome)
            db.close()
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
        for t in threads: t.start()
        barrier.wait()
        for t in threads: t.join(timeout=5)
        self.assertTrue(all(not t.is_alive() for t in threads))
        self.assertEqual(results.count("admitted"), 2)
        self.assertEqual(results.count("guard_triggered"), 1)
        reopened = SafetyStore(self.path)
        self.assertEqual(reopened.new_session(session_id="new", lineage_id="L",
                         grant_id="g", grant_hash="h"), "denied_fenced")
        reopened.close()

    def test_revoke_is_authoritative_and_prior_admission_is_not_rollback(self):
        prior = self.store.admit(session_id="s", expected_generation=1, grant_id="g", grant_hash="h")
        self.assertEqual(prior.outcome, "admitted")
        revoker = SafetyStore(self.path)
        self.assertTrue(revoker.revoke("g"))
        after = self.store.admit(session_id="s", expected_generation=1, grant_id="g", grant_hash="h")
        self.assertEqual(after.outcome, "denied_grant_revoked")
        self.assertEqual(prior.outcome, "admitted")  # no rollback claim
        revoker.close()

    def test_revoke_vs_admit_two_connection_race_then_denies(self):
        barrier = threading.Barrier(3, timeout=5)
        outcomes = []
        def revoke():
            db = SafetyStore(self.path); barrier.wait()
            outcomes.append(("revoke", db.revoke("g"))); db.close()
        def admit():
            db = SafetyStore(self.path); barrier.wait()
            outcomes.append(("admit", db.admit(session_id="s", expected_generation=1,
                                                grant_id="g", grant_hash="h").outcome)); db.close()
        threads = [threading.Thread(target=revoke), threading.Thread(target=admit)]
        for t in threads: t.start()
        barrier.wait()
        for t in threads: t.join(timeout=5)
        self.assertTrue(all(not t.is_alive() for t in threads))
        self.assertIn(("revoke", True), outcomes)
        self.assertIn(dict(outcomes)["admit"], {"admitted", "denied_grant_revoked"})
        self.assertEqual(self.store.admit(session_id="s", expected_generation=1,
                         grant_id="g", grant_hash="h").outcome, "denied_grant_revoked")

    def test_new_session_consumes_same_lineage_counter(self):
        self.assertEqual(self.store.admit(session_id="s", expected_generation=1,
                         grant_id="g", grant_hash="h").outcome, "admitted")
        self.assertEqual(self.store.new_session(session_id="new", lineage_id="L",
                         grant_id="g", grant_hash="h"), "session_created")
        self.assertEqual(self.store.admit(session_id="new", expected_generation=1,
                         grant_id="g", grant_hash="h").outcome, "admitted")
        self.assertEqual(self.store.admit(session_id="new", expected_generation=1,
                         grant_id="g", grant_hash="h").outcome, "guard_triggered")

    def test_stale_and_future_generation_rejected(self):
        self.assertTrue(self.store.interrupt("s"))
        self.assertEqual(self.store.resume("s", 1), "resumed")
        self.assertEqual(self.store.admit(session_id="s", expected_generation=1, grant_id="g", grant_hash="h").outcome,
                         "denied_generation_invalid")
        self.assertEqual(self.store.admit(session_id="s", expected_generation=3, grant_id="g", grant_hash="h").outcome,
                         "denied_generation_invalid")

    def test_resume_cannot_reactivate_revoked_grant(self):
        self.assertTrue(self.store.interrupt("s"))
        self.assertTrue(self.store.revoke("g"))
        self.assertEqual(self.store.resume("s", 1), "denied_grant_revoked")
        self.assertEqual(self.store.db.execute(
            "SELECT generation, state FROM sessions WHERE session_id='s'"
        ).fetchone(), (1, "interrupted"))

    def test_resume_cannot_bypass_lineage_fence(self):
        for _ in range(3):
            self.store.admit(session_id="s", expected_generation=1, grant_id="g", grant_hash="h")
        self.assertTrue(self.store.interrupt("s"))
        self.assertEqual(self.store.resume("s", 1), "denied_fenced")

    def test_fence_and_count_survive_restart(self):
        for _ in range(2):
            self.assertEqual(self.store.admit(session_id="s", expected_generation=1, grant_id="g", grant_hash="h").outcome, "admitted")
        self.assertEqual(self.store.admit(session_id="s", expected_generation=1, grant_id="g", grant_hash="h").outcome, "guard_triggered")
        self.store.close()
        reopened = SafetyStore(self.path)
        self.assertEqual(reopened.new_session(session_id="restart", lineage_id="L", grant_id="g", grant_hash="h"), "denied_fenced")
        reopened.close()

    def test_partial_count_survives_connection_reopen(self):
        self.assertEqual(self.store.admit(session_id="s", expected_generation=1,
                         grant_id="g", grant_hash="h").outcome, "admitted")
        self.store.close()
        reopened = SafetyStore(self.path)
        try:
            self.assertEqual(reopened.admit(session_id="s", expected_generation=1,
                             grant_id="g", grant_hash="h").outcome, "admitted")
            self.assertEqual(reopened.admit(session_id="s", expected_generation=1,
                             grant_id="g", grant_hash="h").outcome, "guard_triggered")
        finally:
            reopened.close()

    def test_failed_write_rolls_back_and_releases_lock(self):
        self.assertEqual(self.store.new_session(session_id="s", lineage_id="L",
                         grant_id="g", grant_hash="h"), "storage_unavailable")
        other = SafetyStore(self.path)
        try:
            self.assertTrue(other.revoke("g"))
            self.assertEqual(self.store.admit(session_id="s", expected_generation=1,
                             grant_id="g", grant_hash="h").outcome, "denied_grant_revoked")
        finally:
            other.close()

    def test_unavailable_or_corrupt_storage_fails_closed(self):
        self.store.close()
        self.assertEqual(self.store.admit(session_id="s", expected_generation=1, grant_id="g", grant_hash="h").outcome, "storage_unavailable")
        corrupt = Path(self.tmp.name) / "corrupt.sqlite3"
        corrupt.write_bytes(b"not sqlite")
        broken = SafetyStore(corrupt)
        self.assertEqual(broken.admit(session_id="s", expected_generation=1, grant_id="g", grant_hash="h").outcome, "storage_unavailable")
        broken.close()


if __name__ == "__main__":
    unittest.main()
