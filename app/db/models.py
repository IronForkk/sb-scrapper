"""
SQLAlchemy ORM Modelleri
PostgreSQL tabloları için modeller
"""
from sqlalchemy import Column, BigInteger, String, Integer, Text, DateTime, Numeric, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class ApplicationLog(Base):
    """Application Logs Tablosu"""
    __tablename__ = "application_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now())
    level = Column(String(20), nullable=False)
    module = Column(String(255))
    function_name = Column(String(255))
    line_number = Column(Integer)
    message = Column(Text, nullable=False)
    extra_data = Column(Text)  # JSONB yerine Text (asyncpg için)
    created_at = Column(DateTime(timezone=True), default=func.now())

    __table_args__ = (
        CheckConstraint("level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')", name="check_app_log_level"),
    )


class RequestLog(Base):
    """Request Logs Tablosu"""
    __tablename__ = "request_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now())
    ip = Column(String(45), nullable=False)
    port = Column(Integer)
    method = Column(String(10), nullable=False)
    path = Column(Text, nullable=False)
    full_url = Column(Text)
    headers = Column(Text)  # JSONB yerine Text (asyncpg için)
    query_params = Column(Text)  # JSONB yerine Text (asyncpg için)
    user_agent = Column(Text)
    body = Column(Text)
    body_error = Column(Text)
    response_status_code = Column(Integer)
    response_time_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=func.now())

    __table_args__ = (
        CheckConstraint(
            "method IN ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS')",
            name="check_request_method"
        ),
    )


class DomainStats(Base):
    """Domain Stats Tablosu (Scraping istatistikleri için)"""
    __tablename__ = "domain_stats"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now())
    domain = Column(String(255), nullable=False)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    success_rate = Column(Numeric(5, 2))
    created_at = Column(DateTime(timezone=True), default=func.now())


class ErrorLog(Base):
    """Error Logs Tablosu (Ayrı tablo - hızlı sorgulama için)"""
    __tablename__ = "error_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now())
    level = Column(String(20), nullable=False)
    module = Column(String(255))
    function_name = Column(String(255))
    line_number = Column(Integer)
    message = Column(Text, nullable=False)
    stack_trace = Column(Text)
    url = Column(Text)
    domain = Column(String(255))
    extra_data = Column(Text)  # JSONB yerine Text (asyncpg için)
    created_at = Column(DateTime(timezone=True), default=func.now())

    __table_args__ = (
        CheckConstraint("level IN ('ERROR', 'CRITICAL')", name="check_error_log_level"),
    )
