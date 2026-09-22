"""Share link database models and DAO."""

import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint

from dbgpt.storage.metadata import BaseDao, Model


class ShareLinkEntity(Model):
    """Share link entity — maps a random token to a conversation."""

    __tablename__ = "share_links"
    __table_args__ = (UniqueConstraint("token", name="uk_share_token"),)

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Primary key")
    token = Column(
        String(64),
        unique=False,  # enforced by UniqueConstraint above
        nullable=False,
        index=True,
        comment="Unique random share token",
    )
    conv_uid = Column(
        String(255),
        nullable=False,
        index=True,
        comment="The conversation uid being shared",
    )
    created_by = Column(
        String(255),
        nullable=True,
        comment="User who created the share link",
    )
    gmt_created = Column(
        DateTime,
        default=datetime.now,
        comment="Creation time",
    )


class ShareLinkDao(BaseDao):
    """DAO for share_links table."""

    def create_share(
        self, conv_uid: str, created_by: Optional[str] = None
    ) -> Optional[ShareLinkEntity]:
        """Create or return an existing share link for a conversation.

        If a share link already exists for this ``conv_uid``, it is returned
        as-is so that repeat clicks always yield the same URL.
        """
        # Check for an existing link first (read-only session)
        existing = self.get_by_conv_uid(conv_uid)
        if existing is not None:
            return existing

        token = secrets.token_urlsafe(32)
        entity = ShareLinkEntity(
            token=token,
            conv_uid=conv_uid,
            created_by=created_by,
            gmt_created=datetime.now(),
        )
        with self.session() as session:
            session.add(entity)
            session.flush()
            # Eagerly load all columns before the session closes
            session.refresh(entity)
            # Detach-safe: copy values into a plain object
            result = ShareLinkEntity(
                id=entity.id,
                token=entity.token,
                conv_uid=entity.conv_uid,
                created_by=entity.created_by,
                gmt_created=entity.gmt_created,
            )
        return result

    def get_by_token(self, token: str) -> Optional[ShareLinkEntity]:
        """Retrieve a share link by token."""
        with self.session(commit=False) as session:
            row = session.query(ShareLinkEntity).filter_by(token=token).first()
            if row is None:
                return None
            return ShareLinkEntity(
                id=row.id,
                token=row.token,
                conv_uid=row.conv_uid,
                created_by=row.created_by,
                gmt_created=row.gmt_created,
            )

    def get_by_conv_uid(self, conv_uid: str) -> Optional[ShareLinkEntity]:
        """Retrieve a share link by conversation uid."""
        with self.session(commit=False) as session:
            row = session.query(ShareLinkEntity).filter_by(conv_uid=conv_uid).first()
            if row is None:
                return None
            return ShareLinkEntity(
                id=row.id,
                token=row.token,
                conv_uid=row.conv_uid,
                created_by=row.created_by,
                gmt_created=row.gmt_created,
            )

    def delete_by_token(self, token: str) -> bool:
        """Delete a share link by token.  Returns True if a row was deleted."""
        with self.session() as session:
            rows = session.query(ShareLinkEntity).filter_by(token=token).delete()
            return rows > 0
