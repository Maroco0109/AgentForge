"""PII anonymization for collected data."""

from ..compliance.pii_detector import PIIDetectionResult, pii_detector


class Anonymizer:
    """Anonymize PII in text data."""

    REPLACEMENT_MAP = {
        "phone": "[전화번호]",
        "email": "[이메일]",
        "ssn": "[주민번호]",
        "card_number": "[카드번호]",
        "name_pattern": "[이름]",
        "address": "[주소]",
    }

    def anonymize(self, text: str) -> tuple[str, PIIDetectionResult]:
        """Anonymize all PII in text.

        Returns: (anonymized_text, detection_result)
        """
        result = pii_detector.detect(text)

        if not result.has_pii:
            return text, result

        # Sort matches by position (reverse) to replace from end to start
        sorted_matches = sorted(result.found, key=lambda m: m["start"], reverse=True)

        anonymized = text
        for match in sorted_matches:
            replacement = self.REPLACEMENT_MAP.get(match["type"], "[개인정보]")
            anonymized = anonymized[: match["start"]] + replacement + anonymized[match["end"] :]

        return anonymized, result


anonymizer = Anonymizer()
