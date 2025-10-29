from datetime import datetime
from database import db

class UserSession(db.Model):
    __tablename__ = "user_sessions"

    id = db.Column(db.Integer, primary_key=True)
    bucket_uuid = db.Column(db.String(64), index=True, nullable=False)
    ip_hash = db.Column(db.String(128), index=True, nullable=True)
    user_agent = db.Column(db.Text, nullable=True)

    first_seen = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    files_count = db.Column(db.Integer, default=0, nullable=False)
    total_pages = db.Column(db.Integer, default=0, nullable=False)
    total_bytes = db.Column(db.BigInteger, default=0, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)

    def touch(self):
        self.last_seen = datetime.utcnow()
