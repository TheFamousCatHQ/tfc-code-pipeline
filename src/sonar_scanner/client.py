"""
SonarQube Client - A module for interacting with the SonarQube API.
"""

import json
import ssl
import urllib.error
import urllib.request
from typing import Dict, Any, Optional

from logging_utils import get_logger


class SonarQubeClient:
    """
    A client for interacting with the SonarQube API.
    """

    def __init__(self, host: str, token: str, verify_ssl: bool = True):
        """
        Initialize the SonarQube client.

        Args:
            host (str): SonarQube host URL.
            token (str): SonarQube API token.
            verify_ssl (bool): Whether to verify SSL certificates. Default is True.
        """
        self.host = host
        self.token = token
        self.verify_ssl = verify_ssl
        self.logger = get_logger()

        # Create SSL context based on verify_ssl setting
        if not self.verify_ssl:
            self.logger.warning("SSL certificate verification is disabled. This is insecure and should only be used for testing.")
            self.ssl_context = ssl._create_unverified_context()
        else:
            self.ssl_context = None

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
        response_data = None

        # Keep fetching pages until we've got all issues
        while total_issues is None or len(all_issues) < total_issues:
            url = f"{self.host}/api/issues/search?componentKeys={project}&projectKeys={project}&p={page}&ps={page_size}"

            self.logger.debug(f"Fetching issues page {page} from {url}")
            request = urllib.request.Request(url)
            if self.token:
                request.add_header("Authorization", f"Bearer {self.token}")

            try:
                with urllib.request.urlopen(request, context=self.ssl_context) as response:
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
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    self.logger.error("Authentication failed: Invalid or missing token. Please provide a valid SonarQube token.")
                else:
                    self.logger.error(f"HTTP Error {e.code}: {e.reason}")
                raise
            except urllib.error.URLError as e:
                self.logger.error(f"URL Error: {e.reason}")
                raise

        # Return the original response structure but with all issues
        if response_data:
            response_data['issues'] = all_issues
            return response_data
        else:
            # Return an empty structure if we couldn't get any data
            return {"issues": [], "paging": {"total": 0}}

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
        self.logger.debug(f"Fetching measures from {url}")
        if not self.token:
            self.logger.warning("No SonarQube token provided. Authentication may fail.")

        request = urllib.request.Request(url)
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")

        try:
            with urllib.request.urlopen(request, context=self.ssl_context) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 401:
                self.logger.error("Authentication failed: Invalid or missing token. Please provide a valid SonarQube token.")
            else:
                self.logger.error(f"HTTP Error {e.code}: {e.reason}")
            raise
        except urllib.error.URLError as e:
            self.logger.error(f"URL Error: {e.reason}")
            raise

    def fetch_file_measures(self, project: str) -> Dict[str, Any]:
        """
        Fetch all measures for all files in a project from SonarQube API.

        Args:
            project (str): Project name or key.

        Returns:
            Dict[str, Any]: JSON response from SonarQube API with all file measures.

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

        # Set a reasonable page size
        page_size = 500
        page = 1
        all_components = []
        total_components = None
        base_component = None

        # Keep fetching pages until we've got all components
        while total_components is None or len(all_components) < total_components:
            # Use component_tree endpoint to get metrics for all files
            url = f"{self.host}/api/measures/component_tree?component={project}&metricKeys={all_metrics}&qualifiers=FIL&p={page}&ps={page_size}"

            self.logger.debug(f"Fetching file measures page {page} from {url}")
            request = urllib.request.Request(url)
            if self.token:
                request.add_header("Authorization", f"Bearer {self.token}")

            try:
                with urllib.request.urlopen(request, context=self.ssl_context) as response:
                    response_data = json.loads(response.read().decode('utf-8'))

                    # Save the base component from the first page
                    if base_component is None:
                        base_component = response_data.get('baseComponent', {})

                    # Get the total number of components if this is the first page
                    if total_components is None:
                        total_components = response_data.get('paging', {}).get('total', 0)
                        self.logger.info(f"Total file components to fetch: {total_components}")

                    # Add components from this page to our collection
                    components = response_data.get('components', [])
                    all_components.extend(components)
                    self.logger.info(f"Fetched {len(components)} file components from page {page}, total so far: {len(all_components)}/{total_components}")

                    # If this page had fewer components than the page size, we're done
                    if len(components) < page_size:
                        break

                    # Move to the next page
                    page += 1
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    self.logger.error("Authentication failed: Invalid or missing token. Please provide a valid SonarQube token.")
                else:
                    self.logger.error(f"HTTP Error {e.code}: {e.reason}")
                raise
            except urllib.error.URLError as e:
                self.logger.error(f"URL Error: {e.reason}")
                raise

        # Return the original response structure but with all components
        return {
            "paging": {
                "pageIndex": 1,
                "pageSize": len(all_components),
                "total": total_components
            },
            "baseComponent": base_component,
            "components": all_components
        }
