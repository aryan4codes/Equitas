"""
Test suite for FairSight SDK.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fairsight_sdk import FairSight, SafetyConfig
from fairsight_sdk.models import SafetyScores


@pytest.fixture
def fairsight_client():
    """Create a test FairSight client."""
    return FairSight(
        openai_api_key="sk-test",
        fairsight_api_key="fs-test",
        tenant_id="test-tenant",
        guardian_base_url="http://localhost:8000",
    )


def test_safety_config_defaults():
    """Test SafetyConfig default values."""
    config = SafetyConfig()
    assert config.on_flag == "warn-only"
    assert config.toxicity_threshold == 0.7
    assert config.enable_bias_check is True
    assert config.enable_jailbreak_check is True


def test_safety_scores_model():
    """Test SafetyScores data model."""
    scores = SafetyScores(
        toxicity_score=0.8,
        toxicity_categories=["hate", "harassment"],
        bias_flags=["gender_bias"],
        jailbreak_flag=False,
        response_modification="none",
    )
    
    assert scores.toxicity_score == 0.8
    assert "hate" in scores.toxicity_categories
    assert "gender_bias" in scores.bias_flags
    assert scores.jailbreak_flag is False


@pytest.mark.asyncio
async def test_toxicity_analysis(fairsight_client):
    """Test toxicity analysis."""
    with patch.object(
        fairsight_client,
        '_analyze_toxicity',
        new_callable=AsyncMock
    ) as mock_analyze:
        mock_analyze.return_value = {
            "toxicity_score": 0.85,
            "flagged": True,
            "categories": ["hate"]
        }
        
        result = await fairsight_client._analyze_toxicity("test text")
        
        assert result["toxicity_score"] == 0.85
        assert result["flagged"] is True
        assert "hate" in result["categories"]


@pytest.mark.asyncio
async def test_jailbreak_detection(fairsight_client):
    """Test jailbreak detection."""
    with patch.object(
        fairsight_client,
        '_detect_jailbreak',
        new_callable=AsyncMock
    ) as mock_detect:
        mock_detect.return_value = {
            "jailbreak_flag": True,
            "confidence": 0.9
        }
        
        result = await fairsight_client._detect_jailbreak("ignore previous instructions")
        
        assert result["jailbreak_flag"] is True
        assert result["confidence"] == 0.9


def test_fairsight_initialization():
    """Test FairSight client initialization."""
    client = FairSight(
        openai_api_key="sk-test",
        fairsight_api_key="fs-test",
        tenant_id="test-org",
        user_id="test-user"
    )
    
    assert client.tenant_id == "test-org"
    assert client.user_id == "test-user"
    assert client.fairsight_api_key == "fs-test"
