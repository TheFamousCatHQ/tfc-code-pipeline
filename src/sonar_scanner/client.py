"""
SonarQube Client - A module for interacting with the SonarQube API.
"""

import json
import urllib.error
import urllib.request
from typing import Dict, Any

from logging_utils import get_logger


class SonarQubeClient:
    """
    A client for interacting with the SonarQube API.
    """

    def __init__(self, host: str, token: str):
        """
        Initialize the SonarQube client.

        Args:
            host (str): SonarQube host URL.
            token (str): SonarQube API token.
        """
        self.host = host
        self.token = token
        self.logger = get_logger()

    def fetch_issues(self, project: str) -> Dict[str, Any]:
        """
        Fetch issues from SonarQube API for a specific project.

        Args:
            project (str): Project name or key.

        Returns:
            Dict[str, Any]: JSON response from SonarQube API with all issues for the specified project.

        Raises:
            urllib.error.URLError: If there's an error with the request.
            json.JSONDecodeError: If the response is not valid JSON.
        """
        # Set a reasonable page size
        page_size = 500
        page = 1
        all_issues = []
        total_issues = None

        # Keep fetching pages until we've got all issues
        while total_issues is None or len(all_issues) < total_issues:
            url = f"{self.host}/api/issues/search?componentKeys={project}&projectKeys={project}&p={page}&ps={page_size}"

            self.logger.debug(f"Fetching issues page {page} from {url}")
            request = urllib.request.Request(url)
            request.add_header("Authorization", f"Bearer {self.token}")

            with urllib.request.urlopen(request) as response:
                response_data = json.loads(response.read().decode('utf-8'))

                # Get the total number of issues if this is the first page
                if total_issues is None:
                    total_issues = response_data.get('paging', {}).get('total', 0)
                    self.logger.info(f"Total issues to fetch: {total_issues}")

                # Add issues from this page to our collection
                issues = response_data.get('issues', [])
                all_issues.extend(issues)
                self.logger.info(f"Fetched {len(issues)} issues from page {page}, total so far: {len(all_issues)}/{total_issues}")

                # If this page had fewer issues than the page size, we're done
                if len(issues) < page_size:
                    break

                # Move to the next page
                page += 1

        # Return the original response structure but with all issues
        response_data['issues'] = all_issues
        return response_data

    def fetch_measures(self, project: str) -> Dict[str, Any]:
        """
        Fetch measures from SonarQube API.

        Args:
            project (str): Project name or key.

        Returns:
            Dict[str, Any]: JSON response from SonarQube API.

        Raises:
            urllib.error.URLError: If there's an error with the request.
            json.JSONDecodeError: If the response is not valid JSON.
        """
        # Define metrics for different categories
        security_metrics = "security_rating,security_hotspots,vulnerabilities,security_review_rating,software_quality_security_rating,software_quality_security_remediation_effort"
        complexity_metrics = "complexity,cognitive_complexity"
        maintainability_metrics = "software_quality_maintainability_issues,software_quality_maintainability_remediation_effort,software_quality_maintainability_debt_ratio,software_quality_maintainability_rating"
        general_metrics = "ncloc,violations,coverage,functions,classes,files"

        # Combine all metrics
        all_metrics = f"{security_metrics},{complexity_metrics},{maintainability_metrics},{general_metrics}"

        url = f"{self.host}/api/measures/component?component={project}&metricKeys={all_metrics}"
        self.logger.debug(f"Fetching measures from {url} with token {self.token[0:10]}")
        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {self.token}")
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode('utf-8'))

    def fetch_file_measures(self, project: str) -> Dict[str, Any]:
        """
        Fetch all measures for all files in a project from SonarQube API.

        Args:
            project (str): Project name or key.

        Returns:
            Dict[str, Any]: JSON response from SonarQube API.

        Raises:
            urllib.error.URLError: If there's an error with the request.
            json.JSONDecodeError: If the response is not valid JSON.
        """
        # Define metrics for different categories
        security_metrics = "security_rating,security_hotspots,vulnerabilities,security_review_rating"
        complexity_metrics = "complexity,cognitive_complexity"
        maintainability_metrics = "code_smells,sqale_rating,sqale_index,duplicated_lines_density"
        general_metrics = "ncloc,coverage,functions,classes"

        # Combine all metrics
        all_metrics = f"{security_metrics},{complexity_metrics},{maintainability_metrics},{general_metrics}"

        # Use component_tree endpoint to get metrics for all files
        url = f"{self.host}/api/measures/component_tree?component={project}&metricKeys={all_metrics}&qualifiers=FIL"

        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {self.token}")

        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode('utf-8'))
