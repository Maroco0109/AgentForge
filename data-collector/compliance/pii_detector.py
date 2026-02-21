"""Korean PII (Personal Identifiable Information) detector."""

import logging
import re

logger = logging.getLogger(__name__)


# Korean PII patterns
PII_PATTERNS = {
    "phone": [
        re.compile(r"01[0-9]-?\d{3,4}-?\d{4}"),  # Mobile
        re.compile(r"0[2-6][0-9]{0,2}-?\d{3,4}-?\d{4}"),  # Landline
    ],
    "email": [
        re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    ],
    "ssn": [
        re.compile(r"\d{6}-?[1-4]\d{6}"),  # Korean SSN (주민등록번호)
    ],
    "card_number": [
        re.compile(r"\d{4}-?\d{4}-?\d{4}-?\d{4}"),  # Credit card
    ],
    "name_pattern": [
        re.compile(
            r"[가-힣]{2,4}\s*(?:씨|님|선생|교수|박사|대표|사장|이사)"
        ),  # Korean name + title
    ],
    "address": [
        re.compile(r"[가-힣]+(?:시|도)\s+[가-힣]+(?:구|군|시)\s+[가-힣]+(?:동|읍|면|로|길)\s*\d*"),
    ],
}


class PIIDetectionResult:
    """Result of PII detection."""

    def __init__(self):
        self.found: list[dict] = []
        self.has_pii: bool = False
        self.pii_types: set[str] = set()

    def add_match(self, pii_type: str, value: str, start: int, end: int):
        self.found.append(
            {
                "type": pii_type,
                "value": value,
                "start": start,
                "end": end,
            }
        )
        self.has_pii = True
        self.pii_types.add(pii_type)

    def to_dict(self) -> dict:
        return {
            "has_pii": self.has_pii,
            "pii_count": len(self.found),
            "pii_types": list(self.pii_types),
            "details": self.found,
        }


class PIIDetector:
    """Detect Korean PII in text."""

    def __init__(self):
        self.patterns = PII_PATTERNS

    def detect(self, text: str) -> PIIDetectionResult:
        """Detect all PII in the given text."""
        result = PIIDetectionResult()

        for pii_type, patterns in self.patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    result.add_match(
                        pii_type=pii_type,
                        value=match.group(),
                        start=match.start(),
                        end=match.end(),
                    )

        if result.has_pii:
            logger.info(f"PII detected: {len(result.found)} items of types {result.pii_types}")

        return result

    def has_pii(self, text: str) -> bool:
        """Quick check if text contains any PII."""
        for patterns in self.patterns.values():
            for pattern in patterns:
                if pattern.search(text):
                    return True
        return False


pii_detector = PIIDetector()
