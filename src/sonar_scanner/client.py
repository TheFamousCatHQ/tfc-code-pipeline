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
        Fetch issues from SonarQube API.

        Args:
            project (str): Project name or key.

        Returns:
            Dict[str, Any]: JSON response from SonarQube API.

        Raises:
            urllib.error.URLError: If there's an error with the request.
            json.JSONDecodeError: If the response is not valid JSON.
        """
        url = f"{self.host}/api/issues/search?component={project}"

        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {self.token}")

        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode('utf-8'))

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
