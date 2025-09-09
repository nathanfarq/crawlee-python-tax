"""Data validation for CRA tax information."""

import re
from typing import Any
from urllib.parse import urlparse

from marshmallow import Schema, ValidationError, fields, post_load, validate


class CRADataSchema(Schema):
    """Schema for validating CRA tax data."""

    url = fields.Url(required=True)
    title = fields.String(required=True, validate=validate.Length(min=1, max=500))
    content = fields.String(required=True, validate=validate.Length(min=50, max=10000))
    page_type = fields.String(load_default='general')
    tax_year = fields.String(allow_none=True)
    form_number = fields.String(allow_none=True)
    extracted_at = fields.DateTime(required=True)

    @post_load
    def clean_data(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        """Clean and normalize extracted data."""
        # Clean whitespace
        if 'title' in data:
            data['title'] = ' '.join(data['title'].split())

        if 'content' in data:
            data['content'] = ' '.join(data['content'].split())

        return data


class CRADataValidator:
    """Validator for CRA tax data with domain and content checks."""

    def __init__(self, *, allowed_domains: list[str] | None = None) -> None:
        self._allowed_domains = allowed_domains or ['canada.ca']
        self._schema = CRADataSchema()

        # Tax-related keywords for content relevance
        self._tax_keywords = {
            'general': ['tax', 'revenue', 'cra', 'income', 'deduction', 'credit'],
            'forms': ['form', 't1', 't2', 't3', 't4', 't5'],
            'business': ['business', 'self-employed', 'corporation', 'gst', 'hst'],
            'personal': ['personal', 'individual', 'rrsp', 'tfsa', 'pension'],
        }

    def validate_url(self, url: str) -> bool:
        """Check if URL is from allowed domains."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Check if domain ends with any allowed domain
            return any(domain.endswith(allowed) for allowed in self._allowed_domains)
        except Exception:
            return False

    def extract_tax_year(self, content: str) -> str | None:
        """Extract tax year from content."""
        # Look for 4-digit years (2020-2030)
        year_pattern = r'\b(20[2-3][0-9])\b'
        matches = re.findall(year_pattern, content)

        if matches:
            # Return the most recent year found
            return max(matches)

        return None

    def extract_form_number(self, content: str) -> str | None:
        """Extract CRA form number from content."""
        # Common CRA form patterns
        form_patterns = [
            r'\bT[1-5][A-Z]?\b',  # T1, T2, etc.
            r'\bT[1-5]\d{3}\b',  # T1234
            r'\bRC\d+\b',  # RC123
            r'\bNR\d+\b',  # NR123
        ]

        for pattern in form_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                return matches[0].upper()

        return None

    def determine_page_type(self, title: str, content: str) -> str:
        """Determine the type of tax page based on content."""
        title_lower = title.lower()
        content_lower = content.lower()

        # Use word boundaries to match whole words only
        combined_text = f'{title_lower} {content_lower}'

        # Check for form-related content
        if any(re.search(rf'\b{re.escape(keyword)}\b', combined_text) for keyword in self._tax_keywords['forms']):
            return 'forms'

        # Check for business content
        if any(re.search(rf'\b{re.escape(keyword)}\b', combined_text) for keyword in self._tax_keywords['business']):
            return 'business'

        # Check for personal tax content
        if any(re.search(rf'\b{re.escape(keyword)}\b', combined_text) for keyword in self._tax_keywords['personal']):
            return 'personal'

        return 'general'

    def is_relevant_content(self, title: str, content: str) -> bool:
        """Check if content is relevant to tax information."""
        title_lower = title.lower()
        content_lower = content.lower()

        # Must contain at least one tax-related keyword
        all_keywords = []
        for keywords in self._tax_keywords.values():
            all_keywords.extend(keywords)

        return any(keyword in title_lower or keyword in content_lower for keyword in all_keywords)

    def validate_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate and enrich extracted data."""
        try:
            # Basic schema validation
            validated_data = self._schema.load(data)

            # URL domain validation
            if not self.validate_url(validated_data['url']):
                raise ValidationError(f'URL not from allowed domains: {validated_data["url"]}')

            # Content relevance check
            if not self.is_relevant_content(validated_data['title'], validated_data['content']):
                raise ValidationError('Content not relevant to tax information')

            # Extract additional metadata
            validated_data['tax_year'] = self.extract_tax_year(validated_data['content'])
            validated_data['form_number'] = self.extract_form_number(validated_data['content'])
            validated_data['page_type'] = self.determine_page_type(validated_data['title'], validated_data['content'])

            return validated_data

        except ValidationError as e:
            raise ValidationError(f'Data validation failed: {e}')

    def get_validation_stats(self) -> dict[str, Any]:
        """Get validation statistics."""
        return {
            'allowed_domains': self._allowed_domains,
            'tax_keyword_categories': list(self._tax_keywords.keys()),
        }
