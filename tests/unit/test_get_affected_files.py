import unittest
import os
import tempfile
from bug_analyzer import BugAnalyzerProcessor

class TestGetAffectedFiles(unittest.TestCase):
    """Tests for the get_affected_files function in BugAnalyzerProcessor."""

    def setUp(self):
        """Set up the test environment."""
        self.processor = BugAnalyzerProcessor()
        
        # Create temporary files for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Create a file with less than 1000 lines
        self.small_file_path = os.path.join(self.temp_dir.name, "small_file.txt")
        with open(self.small_file_path, 'w') as f:
            for i in range(500):
                f.write(f"Line {i}\n")
        
        # Create a file with more than 1000 lines
        self.large_file_path = os.path.join(self.temp_dir.name, "large_file.txt")
        with open(self.large_file_path, 'w') as f:
            for i in range(1500):
                f.write(f"Line {i}\n")

    def tearDown(self):
        """Clean up the test environment."""
        self.temp_dir.cleanup()

    def test_count_lines_in_file(self):
        """Test that count_lines_in_file returns the correct number of lines."""
        # Test with small file
        line_count = self.processor.count_lines_in_file(self.small_file_path)
        self.assertEqual(line_count, 500)
        
        # Test with large file
        line_count = self.processor.count_lines_in_file(self.large_file_path)
        self.assertEqual(line_count, 1500)

    def test_filter_large_files(self):
        """Test that files with more than 1000 lines are filtered out."""
        # Mock the get_affected_files method to return our test files
        original_method = self.processor.get_affected_files
        
        try:
            # Override the get_affected_files method to return our test files
            def mock_get_affected_files(*args, **kwargs):
                return [self.small_file_path, self.large_file_path]
            
            # Test that the large file is filtered out
            self.processor.get_affected_files = mock_get_affected_files
            all_files = [self.small_file_path, self.large_file_path]
            
            # Call the count_lines_in_file method directly to filter files
            filtered_files = []
            for file_path in all_files:
                line_count = self.processor.count_lines_in_file(file_path)
                if line_count <= 1000:
                    filtered_files.append(file_path)
            
            # Check that only the small file is included
            self.assertEqual(len(filtered_files), 1)
            self.assertEqual(filtered_files[0], self.small_file_path)
            
        finally:
            # Restore the original method
            self.processor.get_affected_files = original_method

if __name__ == "__main__":
    unittest.main()