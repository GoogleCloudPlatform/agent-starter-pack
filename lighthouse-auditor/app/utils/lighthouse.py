"""Lighthouse audit utilities and tools."""

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from bs4 import BeautifulSoup
from pydantic import BaseModel


class LighthouseConfig(BaseModel):
    """Configuration for Lighthouse audit."""
    categories: List[str] = ["performance", "accessibility", "best-practices", "seo"]
    output_format: str = "json"
    only_categories: Optional[List[str]] = None
    chrome_flags: List[str] = ["--headless", "--no-sandbox"]
    throttling: Dict[str, Any] = {
        "cpuSlowdownMultiplier": 4,
        "networkSlowdownMultiplier": 2,
    }


@dataclass
class AuditIssue:
    """Represents a Lighthouse audit issue."""
    title: str
    description: str
    score: float
    impact: str
    suggestions: List[str]
    code_snippet: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None


class LighthouseRunner:
    """Handles running Lighthouse audits and processing results."""
    
    def __init__(self, config: Optional[LighthouseConfig] = None):
        self.config = config or LighthouseConfig()
        # Set environment variable for chrome-launcher
        chrome_path = "/usr/bin/google-chrome"
        os.environ["CHROME_PATH"] = chrome_path
        
    def run_audit(self, url: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Run a Lighthouse audit on the specified URL.
        
        Args:
            url: The URL to audit
            output_path: Optional path to save the report
            
        Returns:
            Dict containing the audit results
        """
        # Use absolute paths and additional Chrome flags
        chrome_launcher_config = {
            "chromePath": "/usr/bin/google-chrome",
            "chromeFlags": [
                "--headless",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-software-rasterizer"
            ]
        }
        chrome_launcher_json = json.dumps(chrome_launcher_config)
        
        # Convert Windows-style paths to Linux if needed
        if output_path:
            output_path = output_path.replace('\\', '/')
            if ':' in output_path:  # Remove Windows drive letter if present
                output_path = output_path.split(':', 1)[1]
            # Ensure the output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir:  # Only create directories if there's a path
                os.makedirs(output_dir, exist_ok=True)
        
        lighthouse_path = os.path.join(os.getcwd(), "node_modules", ".bin", "lighthouse")
        
        command = [
            lighthouse_path,
            url,
            "--output=json",
            "--output-path=" + (output_path if output_path else "stdout"),
            f"--chrome-flags={' '.join(chrome_launcher_config['chromeFlags'])}",
            "--quiet"
        ]
        
        # Add categories if specified
        if self.config.only_categories:
            command.append("--only-categories=" + ",".join(self.config.only_categories))
            
        try:
            print("Executing command:", " ".join(command))
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            if not result.stdout:
                raise RuntimeError("No output from Lighthouse")
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                raise RuntimeError(f"Failed to parse Lighthouse output. Output was: {result.stdout}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Lighthouse audit failed. Error: {e.stderr}\nOutput: {e.stdout}")

    def extract_issues(self, report: Union[str, Dict[str, Any]]) -> List[AuditIssue]:
        """Extract actionable issues from a Lighthouse report.
        
        Args:
            report: Either a JSON string or dict containing the Lighthouse report
            
        Returns:
            List of AuditIssue objects
        """
        if isinstance(report, str):
            try:
                report_data = json.loads(report)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON report")
        else:
            report_data = report
            
        issues = []
        audits = report_data.get("audits", {})
        
        for audit_id, audit_data in audits.items():
            if audit_data.get("score", 1) < 1:  # Only process failed audits
                issue = AuditIssue(
                    title=audit_data.get("title", "Unknown Issue"),
                    description=audit_data.get("description", ""),
                    score=audit_data.get("score", 0),
                    impact=self._calculate_impact(audit_data),
                    suggestions=self._extract_suggestions(audit_data),
                    code_snippet=self._extract_code_snippet(audit_data)
                )
                issues.append(issue)
                
        return issues

    def _calculate_impact(self, audit_data: Dict[str, Any]) -> str:
        """Calculate the impact level of an audit issue."""
        score = audit_data.get("score", 0)
        weight = audit_data.get("weight", 0)
        
        if score < 0.5 and weight > 3:
            return "high"
        elif score < 0.8:
            return "medium"
        else:
            return "low"

    def _extract_suggestions(self, audit_data: Dict[str, Any]) -> List[str]:
        """Extract improvement suggestions from audit data."""
        suggestions = []
        
        # Extract from description
        if "description" in audit_data:
            suggestions.append(audit_data["description"])
            
        # Extract from details
        details = audit_data.get("details", {})
        if "items" in details:
            for item in details["items"]:
                if isinstance(item, dict):
                    for key in ["suggestion", "recommendation", "message"]:
                        if key in item:
                            suggestions.append(item[key])
                            
        return list(set(suggestions))  # Remove duplicates

    def _extract_code_snippet(self, audit_data: Dict[str, Any]) -> Optional[str]:
        """Extract relevant code snippet from audit data if available."""
        details = audit_data.get("details", {})
        
        # Try to find code snippets in items
        if "items" in details:
            for item in details["items"]:
                if isinstance(item, dict):
                    # Look for common code-related fields
                    for key in ["snippet", "source", "code"]:
                        if key in item:
                            # Clean HTML if present
                            snippet = item[key]
                            if isinstance(snippet, str):
                                soup = BeautifulSoup(snippet, 'html.parser')
                                return soup.get_text()
                            return str(snippet)
                            
        return None


class ReportChunker:
    """Handles chunking large Lighthouse reports into manageable pieces."""
    
    @staticmethod
    def chunk_report(report: Dict[str, Any], max_chunk_size: int = 8000) -> List[Dict[str, Any]]:
        """Split a large report into smaller chunks while maintaining context.
        
        Args:
            report: The full Lighthouse report
            max_chunk_size: Maximum size of each chunk in characters
            
        Returns:
            List of report chunks
        """
        chunks = []
        current_chunk = {
            "metadata": report.get("metadata", {}),
            "audits": {}
        }
        current_size = 0
        
        for audit_id, audit_data in report.get("audits", {}).items():
            # Estimate size of this audit
            audit_size = len(json.dumps(audit_data))
            
            # If adding this audit would exceed chunk size, start a new chunk
            if current_size + audit_size > max_chunk_size and current_chunk["audits"]:
                chunks.append(current_chunk)
                current_chunk = {
                    "metadata": report.get("metadata", {}),
                    "audits": {}
                }
                current_size = 0
                
            # Add audit to current chunk
            current_chunk["audits"][audit_id] = audit_data
            current_size += audit_size
            
        # Add final chunk if not empty
        if current_chunk["audits"]:
            chunks.append(current_chunk)
            
        return chunks
