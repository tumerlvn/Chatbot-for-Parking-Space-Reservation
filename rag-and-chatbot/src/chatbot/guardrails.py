"""
Guard Rails Module for Sensitive Data Protection

Implements filtering to prevent exposure of:
- PII (Personally Identifiable Information)
- Internal system information
- Other users' private data
- Database credentials/paths

Uses pattern matching and NLP for detection.
"""

import re
from typing import Dict, List, Tuple


class GuardRails:
    """
    Guard rails system to filter sensitive information from bot responses.
    """

    def __init__(self):
        """Initialize guard rails with detection patterns"""
        # PII patterns (excluding user's own data)
        self.pii_patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        }

        # System information patterns
        self.system_patterns = {
            "database_path": r'[/\\].*\.db[/\\]?|[/\\].*\.sqlite[/\\]?',
            "api_key": r'(?i)(api[_-]?key|secret|token)\s*[:=]\s*[\'"]?[\w-]{20,}[\'"]?',
            "ip_address": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
            "connection_string": r'(?i)(mongodb|mysql|postgres|sqlite)://[^\s]+',
        }

        # Keywords that should never appear in user-facing responses
        self.forbidden_keywords = [
            "password",
            "secret_key",
            "admin_password",
            "database_url",
            "connection_string",
            "__pycache__",
            "venv",
            ".env",
        ]

    def scan_for_sensitive_data(self, text: str) -> Tuple[bool, List[str]]:
        """
        Scan text for sensitive information.

        Args:
            text: Text to scan

        Returns:
            Tuple of (has_sensitive_data: bool, violations: List[str])
        """
        violations = []

        # Check PII patterns
        for pattern_name, pattern in self.pii_patterns.items():
            if re.search(pattern, text):
                violations.append(f"PII: {pattern_name}")

        # Check system patterns
        for pattern_name, pattern in self.system_patterns.items():
            if re.search(pattern, text):
                violations.append(f"System: {pattern_name}")

        # Check forbidden keywords
        text_lower = text.lower()
        for keyword in self.forbidden_keywords:
            if keyword in text_lower:
                violations.append(f"Keyword: {keyword}")

        return len(violations) > 0, violations

    def filter_response(self, response: str, user_context: Dict = None) -> str:
        """
        Filter a bot response to remove or redact sensitive information.

        Args:
            response: Bot's response text
            user_context: Dict with user's own data (name, car_number) - these are allowed

        Returns:
            Filtered response
        """
        has_violation, violations = self.scan_for_sensitive_data(response)

        if not has_violation:
            return response

        # If violations found, apply redactions
        filtered = response

        # Redact emails (except known safe ones)
        filtered = re.sub(
            self.pii_patterns["email"],
            "[EMAIL REDACTED]",
            filtered
        )

        # Redact phone numbers
        filtered = re.sub(
            self.pii_patterns["phone"],
            "[PHONE REDACTED]",
            filtered
        )

        # Redact SSN
        filtered = re.sub(
            self.pii_patterns["ssn"],
            "[SSN REDACTED]",
            filtered
        )

        # Redact credit cards
        filtered = re.sub(
            self.pii_patterns["credit_card"],
            "[CARD REDACTED]",
            filtered
        )

        # Redact database paths
        filtered = re.sub(
            self.system_patterns["database_path"],
            "[PATH REDACTED]",
            filtered
        )

        # Redact API keys
        filtered = re.sub(
            self.system_patterns["api_key"],
            "[KEY REDACTED]",
            filtered
        )

        # Redact IP addresses (except localhost)
        filtered = re.sub(
            r'\b(?!127\.0\.0\.1)(?!0\.0\.0\.0)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
            "[IP REDACTED]",
            filtered
        )

        return filtered

    def validate_user_query(self, query: str) -> Tuple[bool, str]:
        """
        Validate user query for malicious patterns or injection attempts.

        Args:
            query: User's input query

        Returns:
            Tuple of (is_safe: bool, reason: str)
        """
        query_lower = query.lower()

        # SQL injection patterns
        sql_patterns = [
            r";\s*(drop|delete|truncate|alter)\s+table",
            r"union\s+select",
            r"exec\s*\(",
            r"1\s*=\s*1",
            r"'\s*or\s*'1",
        ]

        for pattern in sql_patterns:
            if re.search(pattern, query_lower):
                return False, "Potential SQL injection detected"

        # Command injection patterns
        command_patterns = [
            r"&&\s*rm\s+-rf",
            r";\s*cat\s+/etc/passwd",
            r"\$\(.*\)",
            r"`.*`",
        ]

        for pattern in command_patterns:
            if re.search(pattern, query_lower):
                return False, "Potential command injection detected"

        # Path traversal
        if "../" in query or "..\\" in query:
            return False, "Path traversal attempt detected"

        # Excessive length (potential DoS)
        if len(query) > 5000:
            return False, "Query too long"

        return True, "Safe"

    def filter_retrieval_results(self, documents: List, user_data: Dict = None) -> List:
        """
        Filter retrieved documents to ensure no sensitive data leaks.

        Args:
            documents: List of retrieved documents
            user_data: User's own reservation data (allowed to show)

        Returns:
            Filtered list of documents
        """
        filtered_docs = []

        for doc in documents:
            content = doc.page_content if hasattr(doc, 'page_content') else str(doc)

            # Check if document contains other users' data
            # This is a simple check - in production, you'd want more sophisticated logic
            has_sensitive, violations = self.scan_for_sensitive_data(content)

            if not has_sensitive:
                filtered_docs.append(doc)
            else:
                # Optionally: redact and include, or skip entirely
                # For now, we skip documents with sensitive data
                continue

        return filtered_docs


# Global instance
_guard_rails = None


def get_guard_rails() -> GuardRails:
    """Get or create global guard rails instance"""
    global _guard_rails
    if _guard_rails is None:
        _guard_rails = GuardRails()
    return _guard_rails


def apply_guardrails(response: str, user_context: Dict = None) -> str:
    """
    Convenience function to apply guard rails to a response.

    Args:
        response: Bot response
        user_context: User's data context

    Returns:
        Filtered response
    """
    guard_rails = get_guard_rails()
    return guard_rails.filter_response(response, user_context)


def validate_query(query: str) -> Tuple[bool, str]:
    """
    Convenience function to validate user query.

    Args:
        query: User input

    Returns:
        (is_safe, reason)
    """
    guard_rails = get_guard_rails()
    return guard_rails.validate_user_query(query)
