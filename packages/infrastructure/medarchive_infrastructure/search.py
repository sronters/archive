from __future__ import annotations

from medarchive_application.search import PartnerSearchResult, ServiceSearchResult
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from medarchive_infrastructure.models import PartnerModel, ServiceModel


class SqlAlchemySearchRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def search_services(
        self,
        *,
        query: str | None,
        category: str | None,
        is_active: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[ServiceSearchResult, ...]:
        statement = select(ServiceModel).order_by(
            ServiceModel.official_name.asc(),
            ServiceModel.id.asc(),
        )
        if query is not None:
            pattern = f"%{query}%"
            statement = statement.where(
                or_(
                    ServiceModel.official_name.ilike(pattern),
                    ServiceModel.external_service_id.ilike(pattern),
                    ServiceModel.category.ilike(pattern),
                )
            )
        if category is not None:
            statement = statement.where(ServiceModel.category == category)
        if is_active is not None:
            statement = statement.where(ServiceModel.is_active.is_(is_active))
        with self._session_factory() as session:
            rows = session.execute(statement.limit(limit).offset(offset)).scalars().all()
            return tuple(
                ServiceSearchResult(
                    service_id=row.id,
                    external_service_id=row.external_service_id,
                    official_name=row.official_name,
                    category=row.category,
                    is_active=row.is_active,
                )
                for row in rows
            )

    def search_partners(
        self,
        *,
        query: str | None,
        city: str | None,
        is_active: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[PartnerSearchResult, ...]:
        statement = select(PartnerModel).order_by(PartnerModel.name.asc(), PartnerModel.id.asc())
        if query is not None:
            pattern = f"%{query}%"
            statement = statement.where(
                or_(
                    PartnerModel.name.ilike(pattern),
                    PartnerModel.external_partner_id.ilike(pattern),
                    PartnerModel.bin.ilike(pattern),
                )
            )
        if city is not None:
            statement = statement.where(PartnerModel.city == city)
        if is_active is not None:
            statement = statement.where(PartnerModel.is_active.is_(is_active))
        with self._session_factory() as session:
            rows = session.execute(statement.limit(limit).offset(offset)).scalars().all()
            return tuple(
                PartnerSearchResult(
                    partner_id=row.id,
                    external_partner_id=row.external_partner_id,
                    name=row.name,
                    bin=row.bin,
                    city=row.city,
                    is_active=row.is_active,
                )
                for row in rows
            )
