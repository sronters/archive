from __future__ import annotations

from uuid import uuid4

import pytest
from medarchive_application.partner_profiles import PartnerProfileDraft, PartnerProfileService

from tests.fakes import FakePartnerProfileRepository


def test_partner_profile_is_saved_only_as_confirmed_profile_and_versioned() -> None:
    repository = FakePartnerProfileRepository()
    service = PartnerProfileService(repository=repository)
    partner_id = uuid4()
    operator_id = uuid4()
    draft = PartnerProfileDraft(
        partner_id=partner_id,
        layout_signature="sheet:price/header:8/service:D/resident:H",
        sheet_name="Price",
        header_row_index=8,
        service_column="D",
        service_code_column="B",
        resident_price_column="H",
        nonresident_price_column="I",
        normalization_rules={"MRI": "МРТ"},
        learned_from_document_id=uuid4(),
        approved_by=operator_id,
    )

    first = service.save_confirmed_profile(draft)
    second = service.save_confirmed_profile(draft)

    assert first.profile_version == 1
    assert second.profile_version == 2
    assert service.get_partner_profile(partner_id) == second


def test_partner_profile_requires_layout_signature() -> None:
    service = PartnerProfileService(repository=FakePartnerProfileRepository())
    draft = PartnerProfileDraft(
        partner_id=uuid4(),
        layout_signature=" ",
        sheet_name=None,
        header_row_index=None,
        service_column=None,
        service_code_column=None,
        resident_price_column=None,
        nonresident_price_column=None,
        normalization_rules={},
        learned_from_document_id=None,
        approved_by=uuid4(),
    )

    with pytest.raises(ValueError, match="layout_signature"):
        service.save_confirmed_profile(draft)
