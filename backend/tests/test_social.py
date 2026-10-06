from app.social.contracts import Capability, CampaignPlan, Platform
from app.social.providers.adapters import PROVIDERS
from app.social.store import classify_engagement

def test_all_declared_platforms_have_adapters():
    assert set(PROVIDERS) == set(Platform)

def test_engagement_classifier_prioritizes_commercial_intent():
    assert classify_engagement("How much does this cost?") == ("lead","neutral","high")

def test_engagement_classifier_escalates_complaints():
    assert classify_engagement("I was charged twice and need a refund") == ("complaint","negative","urgent")

def test_campaign_requires_valid_budget_and_name():
    plan=CampaignPlan(account_id="00000000-0000-0000-0000-000000000000",name="Launch",objective="traffic",daily_budget=10)
    assert plan.daily_budget==10

def test_platform_capabilities_are_explicit():
    assert Capability.PUBLISH in PROVIDERS[Platform.INSTAGRAM].capabilities
    assert Capability.ADS_WRITE in PROVIDERS[Platform.PINTEREST].capabilities
    assert Capability.ADS_WRITE not in PROVIDERS[Platform.TIKTOK].capabilities
