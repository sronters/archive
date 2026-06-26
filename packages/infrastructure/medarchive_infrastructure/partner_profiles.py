from __future__ import annotations

from uuid import UUID, uuid4

from medarchive_application.partner_profiles import PartnerProfile, PartnerProfileDraft
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from medarchive_infrastructure.models import PartnerProfileModel


class SqlAlchemyPartnerProfileRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save_confirmed_profile(self, draft: PartnerProfileDraft) -> PartnerProfile:
        with self._session_factory() as session:
            row = session.execute(
                select(PartnerProfileModel).where(
                    PartnerProfileModel.partner_id == draft.partner_id,
                )
            ).scalar_one_or_none()
            if row is None:
                row = PartnerProfileModel(
                    id=uuid4(),
                    partner_id=draft.partner_id,
                    profile_version=1,
                )
                session.add(row)
            else:
                row.profile_version += 1
            row.layout_signature = draft.layout_signature
            row.sheet_name = draft.sheet_name
            row.header_row_index = draft.header_row_index
            row.service_column = draft.service_column
            row.service_code_column = draft.service_code_column
            row.resident_price_column = draft.resident_price_column
            row.nonresident_price_column = draft.nonresident_price_column
            row.normalization_rules = draft.normalization_rules
            row.learned_from_document_id = draft.learned_from_document_id
            row.approved_by = draft.approved_by
            session.commit()
            return _profile(row)

    def get_partner_profile(self, partner_id: UUID) -> PartnerProfile | None:
        with self._session_factory() as session:
            row = session.execute(
                select(PartnerProfileModel).where(PartnerProfileModel.partner_id == partner_id)
            ).scalar_one_or_none()
            return _profile(row) if row is not None else None


def _profile(row: PartnerProfileModel) -> PartnerProfile:
    return PartnerProfile(
        partner_id=row.partner_id,
        profile_version=row.profile_version,
        layout_signature=row.layout_signature,
        sheet_name=row.sheet_name,
        header_row_index=row.header_row_index,
        service_column=row.service_column,
        service_code_column=row.service_code_column,
        resident_price_column=row.resident_price_column,
        nonresident_price_column=row.nonresident_price_column,
        normalization_rules=row.normalization_rules,
        learned_from_document_id=row.learned_from_document_id,
        approved_by=row.approved_by,
    )
