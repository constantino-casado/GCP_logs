import hashlib
import unittest

from gcp_logs_desktop.filters import build_bigquery_log_filter, normalize_project_names
from gcp_logs_desktop.processor import flatten_bigquery_log_entry, hash_query_literals, spark_sha2_256


class ProcessorTests(unittest.TestCase):
    def test_hash_matches_spark_sha2_256(self) -> None:
        email = "User.Name@example.com"
        expected = hashlib.sha256(email.encode("utf-8")).hexdigest()
        self.assertEqual(spark_sha2_256(email), expected)

    def test_project_names_are_normalized(self) -> None:
        self.assertEqual(
            normalize_project_names(["my-project", "projects/another-project", " "]),
            ["projects/my-project", "projects/another-project"],
        )

    def test_filter_matches_notebook_query(self) -> None:
        log_filter = build_bigquery_log_filter()
        self.assertIn("severity=INFO", log_filter)
        self.assertIn('resource.type="bigquery_resource"', log_filter)
        self.assertIn('protoPayload.methodName="jobservice.jobcompleted"', log_filter)
        self.assertRegex(log_filter, r'timestamp >= "\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"')

    def test_query_literals_are_hashed_deterministically(self) -> None:
        query = "select 'secret', 'secret', \"other\", 'alice@example.com'"
        hashed = hash_query_literals(query)

        secret_hash = hashlib.sha256(b"secret").hexdigest()
        other_hash = hashlib.sha256(b"other").hexdigest()
        email_hash = hashlib.sha256(b"alice@example.com").hexdigest()
        self.assertEqual(hashed.count(secret_hash), 2)
        self.assertIn(other_hash, hashed)
        self.assertIn(email_hash, hashed)
        self.assertNotIn("secret", hashed)
        self.assertNotIn("other", hashed)
        self.assertNotIn("alice@example.com", hashed)

    def test_flatten_entry_extracts_and_anonymizes_nested_fields(self) -> None:
        entry = {
            "timestamp": "2026-05-16T09:00:00Z",
            "logName": "projects/test/logs/cloudaudit.googleapis.com%2Fdata_access",
            "insertId": "abc123",
            "severity": "INFO",
            "resource": {"type": "bigquery_resource", "labels": {"project_id": "test"}},
            "protoPayload": {
                "authenticationInfo": {"principalEmail": "user@example.com"},
                "methodName": "jobservice.jobcompleted",
                "requestMetadata": {"callerSuppliedUserAgent": "agent"},
                "resourceName": "projects/test/jobs/job_1",
                "serviceName": "bigquery.googleapis.com",
                "serviceData": {
                    "jobCompletedEvent": {
                        "job": {
                            "jobName": {"projectId": "test", "location": "EU", "jobId": "job_1"},
                            "jobConfiguration": {
                                "query": {
                                    "statementType": "SELECT",
                                    "query": "select 'secret', owner from table where email='user@example.com'",
                                    "referencedTables": [{"projectId": "test", "datasetId": "ds", "tableId": "tbl"}],
                                }
                            },
                            "jobStatistics": {
                                "totalBilledBytes": "10",
                                "totalProcessedBytes": "20",
                                "totalSlotMs": "30",
                            },
                        }
                    }
                },
            },
        }

        row = flatten_bigquery_log_entry(entry)

        self.assertEqual(row["principalEmail"], hashlib.sha256(b"user@example.com").hexdigest())
        self.assertEqual(row["statementType"], "SELECT")
        self.assertEqual(row["projectId"], "test")
        self.assertEqual(row["location"], "EU")
        self.assertNotIn("secret", row["query"])
        self.assertNotIn("user@example.com", row["query"])
        self.assertIn("referencedTables", row)


if __name__ == "__main__":
    unittest.main()
