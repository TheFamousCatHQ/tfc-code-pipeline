"""Tests for the XML serialization of BugAnalysisReport.

This module contains tests for the to_xml method of the BugAnalysisReport class,
which converts a BugAnalysisReport object to an XML element.
"""

import unittest
from datetime import datetime

from bug_analyzer import BugAnalysis, BugAnalysisReport


class TestBugAnalysisReportXML(unittest.TestCase):
    """Tests for the XML serialization of BugAnalysisReport."""

    def test_to_xml(self):
        """Test that to_xml converts a BugAnalysisReport to the expected XML."""
        # Create a BugAnalysisReport object
        bug = BugAnalysis(
            file_path="src/example.py",
            line_number="42",
            description="This is a bug",
            severity="high",
            confidence="medium",
            suggested_fix="Fix it",
            code_snippet="print('Hello, world!')"
        )
        report = BugAnalysisReport(
            commit_id="abc123",
            timestamp=datetime.now().isoformat(),
            affected_files=["src/example.py"],
            bugs=[bug],
            summary="Found 1 bug"
        )

        # Convert to XML
        root = report.to_xml()

        # Check that the root element is correct
        self.assertEqual(root.tag, "bug_analysis_report")

        # Check that the commit_id element is correct
        commit_id_elem = root.find("commit_id")
        self.assertIsNotNone(commit_id_elem)
        self.assertEqual(commit_id_elem.text, "abc123")

        # Check that the timestamp element is correct
        timestamp_elem = root.find("timestamp")
        self.assertIsNotNone(timestamp_elem)
        self.assertEqual(timestamp_elem.text, report.timestamp)

        # Check that the affected_files element is correct
        affected_files_elem = root.find("affected_files")
        self.assertIsNotNone(affected_files_elem)
        file_elems = affected_files_elem.findall("file")
        self.assertEqual(len(file_elems), 1)
        self.assertEqual(file_elems[0].text, "src/example.py")

        # Check that the bugs element is correct
        bugs_elem = root.find("bugs")
        self.assertIsNotNone(bugs_elem)
        bug_elems = bugs_elem.findall("bug")
        self.assertEqual(len(bug_elems), 1)

        # Check that the bug element is correct
        bug_elem = bug_elems[0]
        self.assertEqual(bug_elem.find("file_path").text, "src/example.py")
        self.assertEqual(bug_elem.find("line_number").text, "42")
        self.assertEqual(bug_elem.find("description").text, "This is a bug")
        self.assertEqual(bug_elem.find("severity").text, "high")
        self.assertEqual(bug_elem.find("confidence").text, "medium")
        self.assertEqual(bug_elem.find("suggested_fix").text, "Fix it")
        self.assertEqual(bug_elem.find("code_snippet").text, "print('Hello, world!')")

        # Check that the summary element is correct
        summary_elem = root.find("summary")
        self.assertIsNotNone(summary_elem)
        self.assertEqual(summary_elem.text, "Found 1 bug")

    def test_to_xml_empty_bugs(self):
        """Test that to_xml handles an empty bugs list correctly."""
        # Create a BugAnalysisReport object with no bugs
        report = BugAnalysisReport(
            commit_id="abc123",
            timestamp=datetime.now().isoformat(),
            affected_files=["src/example.py"],
            bugs=[],
            summary="No bugs found"
        )

        # Convert to XML
        root = report.to_xml()

        # Check that the bugs element is empty
        bugs_elem = root.find("bugs")
        self.assertIsNotNone(bugs_elem)
        bug_elems = bugs_elem.findall("bug")
        self.assertEqual(len(bug_elems), 0)

    def test_to_xml_no_summary(self):
        """Test that to_xml handles a report with no summary correctly."""
        # Create a BugAnalysisReport object with no summary
        report = BugAnalysisReport(
            commit_id="abc123",
            timestamp=datetime.now().isoformat(),
            affected_files=["src/example.py"],
            bugs=[]
        )

        # Convert to XML
        root = report.to_xml()

        # Check that the summary element doesn't exist
        summary_elem = root.find("summary")
        self.assertIsNone(summary_elem)


if __name__ == "__main__":
    unittest.main()
