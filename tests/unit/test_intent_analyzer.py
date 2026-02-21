"""Tests for Intent Analyzer - Natural language to structured intent."""

import json
from unittest.mock import AsyncMock, MagicMock

from backend.discussion.intent_analyzer import IntentAnalyzer, IntentResult
from backend.pipeline.llm_router import LLMResponse, LLMRouter, TaskComplexity


class TestIntentResult:
    """Test IntentResult dataclass."""

    def test_default_values(self):
        """Test IntentResult has correct default values."""
        result = IntentResult()
        assert result.task == "custom"
        assert result.source_type == "none"
        assert result.source_hints == []
        assert result.output_format == "text"
        assert result.needs_clarification is False
        assert result.clarification_questions == []
        assert result.confidence == 0.0
        assert result.estimated_complexity == "simple"
        assert result.summary == ""
        assert result.raw_response == ""

    def test_custom_values(self):
        """Test IntentResult with custom values."""
        result = IntentResult(
            task="sentiment_analysis",
            source_type="web_reviews",
            source_hints=["naver"],
            output_format="report",
            confidence=0.85,
        )
        assert result.task == "sentiment_analysis"
        assert result.source_type == "web_reviews"
        assert result.source_hints == ["naver"]
        assert result.output_format == "report"
        assert result.confidence == 0.85


class TestIntentAnalyzer:
    """Test IntentAnalyzer functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_router = MagicMock(spec=LLMRouter)
        self.analyzer = IntentAnalyzer(router=self.mock_router)

    async def test_analyze_with_llm_success(self):
        """Test analyze with successful LLM response."""
        mock_response = LLMResponse(
            content=json.dumps(
                {
                    "task": "sentiment_analysis",
                    "source_type": "web_reviews",
                    "source_hints": ["naver_shopping"],
                    "output_format": "report",
                    "needs_clarification": False,
                    "clarification_questions": [],
                    "confidence": 0.9,
                    "estimated_complexity": "standard",
                    "summary": "네이버 쇼핑 리뷰 감성 분석",
                }
            ),
            model="gpt-4o-mini",
            provider="openai",
            usage={"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
            cost_estimate=0.0001,
        )

        self.mock_router.generate = AsyncMock(return_value=mock_response)

        result = await self.analyzer.analyze("네이버 쇼핑 리뷰 감성 분석해주세요")

        assert result.task == "sentiment_analysis"
        assert result.source_type == "web_reviews"
        assert result.source_hints == ["naver_shopping"]
        assert result.output_format == "report"
        assert result.confidence == 0.9
        assert result.estimated_complexity == "standard"

        # Verify LLM was called with correct parameters
        self.mock_router.generate.assert_called_once()
        call_args = self.mock_router.generate.call_args
        assert call_args.kwargs["complexity"] == TaskComplexity.SIMPLE
        assert call_args.kwargs["temperature"] == 0.3
        assert call_args.kwargs["max_tokens"] == 1024

    async def test_analyze_with_json_code_block(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        mock_response = LLMResponse(
            content="```json\n"
            + json.dumps({"task": "translation", "confidence": 0.8})
            + "\n```",
            model="gpt-4o-mini",
            provider="openai",
            usage={"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
            cost_estimate=0.0001,
        )

        self.mock_router.generate = AsyncMock(return_value=mock_response)

        result = await self.analyzer.analyze("Translate this document")

        assert result.task == "translation"
        assert result.confidence == 0.8

    async def test_analyze_with_plain_code_block(self):
        """Test parsing JSON wrapped in plain code blocks."""
        mock_response = LLMResponse(
            content="```\n"
            + json.dumps({"task": "summarization", "confidence": 0.75})
            + "\n```",
            model="gpt-4o-mini",
            provider="openai",
            usage={"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
            cost_estimate=0.0001,
        )

        self.mock_router.generate = AsyncMock(return_value=mock_response)

        result = await self.analyzer.analyze("요약해주세요")

        assert result.task == "summarization"
        assert result.confidence == 0.75

    async def test_analyze_with_invalid_json(self):
        """Test handling of invalid JSON response."""
        mock_response = LLMResponse(
            content="This is not valid JSON {invalid}",
            model="gpt-4o-mini",
            provider="openai",
            usage={"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
            cost_estimate=0.0001,
        )

        self.mock_router.generate = AsyncMock(return_value=mock_response)

        result = await self.analyzer.analyze("Some request")

        # Should return fallback result with clarification needed
        assert result.task == "custom"
        assert result.needs_clarification is True
        assert len(result.clarification_questions) > 0
        assert result.confidence == 0.1

    async def test_analyze_with_runtime_error_fallback(self):
        """Test fallback to pattern matching when LLM is unavailable."""
        self.mock_router.generate = AsyncMock(
            side_effect=RuntimeError("No LLM provider")
        )

        result = await self.analyzer.analyze("네이버 리뷰 감성 분석해주세요")

        # Should use pattern matching fallback
        assert result.task == "sentiment_analysis"
        assert result.source_type == "web_reviews"
        assert "naver" in result.source_hints

    def test_pattern_match_fallback_sentiment_analysis(self):
        """Test pattern matching for sentiment analysis (Korean)."""
        result = self.analyzer._pattern_match_fallback("리뷰 감성 분석해주세요")
        assert result.task == "sentiment_analysis"

        result = self.analyzer._pattern_match_fallback("감정 분석이 필요해요")
        assert result.task == "sentiment_analysis"

    def test_pattern_match_fallback_sentiment_analysis_english(self):
        """Test pattern matching for sentiment analysis (English)."""
        result = self.analyzer._pattern_match_fallback("sentiment analysis of reviews")
        assert result.task == "sentiment_analysis"

    def test_pattern_match_fallback_data_collection(self):
        """Test pattern matching for data collection."""
        result = self.analyzer._pattern_match_fallback("데이터 수집해주세요")
        assert result.task == "data_collection"

        result = self.analyzer._pattern_match_fallback("웹사이트 크롤링 필요")
        assert result.task == "data_collection"

        result = self.analyzer._pattern_match_fallback("scrape this website")
        assert result.task == "data_collection"

    def test_pattern_match_fallback_comparison(self):
        """Test pattern matching for comparison."""
        result = self.analyzer._pattern_match_fallback("제품 비교해주세요")
        assert result.task == "comparison"

        result = self.analyzer._pattern_match_fallback("compare product A vs B")
        assert result.task == "comparison"

    def test_pattern_match_fallback_translation(self):
        """Test pattern matching for translation."""
        result = self.analyzer._pattern_match_fallback("문서 번역해주세요")
        assert result.task == "translation"

        result = self.analyzer._pattern_match_fallback("translate this document")
        assert result.task == "translation"

    def test_pattern_match_fallback_summarization(self):
        """Test pattern matching for summarization."""
        result = self.analyzer._pattern_match_fallback("이 글을 요약해주세요")
        assert result.task == "summarization"

        result = self.analyzer._pattern_match_fallback("summarize this article")
        assert result.task == "summarization"

    def test_pattern_match_fallback_report_generation(self):
        """Test pattern matching for report generation."""
        result = self.analyzer._pattern_match_fallback("리포트 작성해주세요")
        assert result.task == "report_generation"

        result = self.analyzer._pattern_match_fallback("보고서가 필요합니다")
        assert result.task == "report_generation"

    def test_pattern_match_source_type_naver(self):
        """Test pattern matching for Naver source."""
        result = self.analyzer._pattern_match_fallback("네이버 쇼핑 리뷰 분석")
        assert result.source_type == "web_reviews"
        assert "naver" in result.source_hints

    def test_pattern_match_source_type_web(self):
        """Test pattern matching for web sources."""
        result = self.analyzer._pattern_match_fallback("웹사이트에서 데이터 수집")
        assert result.source_type == "web_reviews"

        result = self.analyzer._pattern_match_fallback("https://example.com 분석")
        assert result.source_type == "web_reviews"

    def test_pattern_match_source_type_pdf(self):
        """Test pattern matching for PDF source."""
        result = self.analyzer._pattern_match_fallback("PDF 파일 분석해주세요")
        assert result.source_type == "pdf"

    def test_pattern_match_source_type_csv(self):
        """Test pattern matching for CSV/Excel source."""
        result = self.analyzer._pattern_match_fallback("CSV 파일을 분석해주세요")
        assert result.source_type == "file"

        result = self.analyzer._pattern_match_fallback("엑셀 데이터 처리")
        assert result.source_type == "file"

    def test_pattern_match_source_type_api(self):
        """Test pattern matching for API source."""
        result = self.analyzer._pattern_match_fallback("API 데이터를 가져와주세요")
        assert result.source_type == "api"

    def test_pattern_match_output_format_report(self):
        """Test pattern matching for report output format."""
        result = self.analyzer._pattern_match_fallback("리포트로 만들어주세요")
        assert result.output_format == "report"

        result = self.analyzer._pattern_match_fallback("보고서 형식으로")
        assert result.output_format == "report"

    def test_pattern_match_output_format_table(self):
        """Test pattern matching for table output format."""
        result = self.analyzer._pattern_match_fallback("표로 정리해주세요")
        assert result.output_format == "table"

        result = self.analyzer._pattern_match_fallback("테이블 형태로")
        assert result.output_format == "table"

    def test_pattern_match_output_format_chart(self):
        """Test pattern matching for chart output format."""
        result = self.analyzer._pattern_match_fallback("차트로 시각화해주세요")
        assert result.output_format == "chart"

        result = self.analyzer._pattern_match_fallback("그래프로 보여줘")
        assert result.output_format == "chart"

    def test_pattern_match_output_format_json(self):
        """Test pattern matching for JSON output format."""
        result = self.analyzer._pattern_match_fallback("JSON 형식으로 출력")
        assert result.output_format == "json"

    def test_pattern_match_complexity_simple(self):
        """Test complexity estimation for simple tasks."""
        result = self.analyzer._pattern_match_fallback("안녕하세요")
        assert result.estimated_complexity == "simple"

    def test_pattern_match_complexity_standard(self):
        """Test complexity estimation for standard tasks."""
        # >20 words
        result = self.analyzer._pattern_match_fallback(" ".join(["단어"] * 25))
        assert result.estimated_complexity == "standard"

        # data_collection task
        result = self.analyzer._pattern_match_fallback("데이터 수집")
        assert result.estimated_complexity == "standard"

        # report_generation task
        result = self.analyzer._pattern_match_fallback("리포트 작성")
        assert result.estimated_complexity == "standard"

    def test_pattern_match_complexity_complex(self):
        """Test complexity estimation for complex tasks."""
        # >50 words
        result = self.analyzer._pattern_match_fallback(" ".join(["단어"] * 55))
        assert result.estimated_complexity == "complex"

        # comparison task
        result = self.analyzer._pattern_match_fallback("제품 비교")
        assert result.estimated_complexity == "complex"

    def test_pattern_match_confidence_high(self):
        """Test confidence when task is recognized."""
        result = self.analyzer._pattern_match_fallback("감성 분석해주세요")
        assert result.confidence == 0.7

    def test_pattern_match_confidence_low(self):
        """Test confidence when task is not recognized."""
        result = self.analyzer._pattern_match_fallback("알 수 없는 요청")
        assert result.confidence == 0.3
        assert result.needs_clarification is True
        assert len(result.clarification_questions) > 0

    def test_pattern_match_combined_patterns(self):
        """Test pattern matching with combined patterns."""
        result = self.analyzer._pattern_match_fallback(
            "네이버 쇼핑 리뷰 감성 분석하고 리포트로 만들어주세요"
        )
        assert result.task == "sentiment_analysis"
        assert result.source_type == "web_reviews"
        assert "naver" in result.source_hints
        assert result.output_format == "report"

    async def test_analyze_with_needs_clarification(self):
        """Test analyze with result that needs clarification."""
        mock_response = LLMResponse(
            content=json.dumps(
                {
                    "task": "custom",
                    "needs_clarification": True,
                    "clarification_questions": ["어떤 데이터를 분석하고 싶으신가요?"],
                    "confidence": 0.3,
                }
            ),
            model="gpt-4o-mini",
            provider="openai",
            usage={"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
            cost_estimate=0.0001,
        )

        self.mock_router.generate = AsyncMock(return_value=mock_response)

        result = await self.analyzer.analyze("애매한 요청")

        assert result.needs_clarification is True
        assert len(result.clarification_questions) > 0
        assert result.confidence < 0.5
