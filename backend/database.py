from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(Base):
    __tablename__ = "jobs"

    _id = Column(String(36), primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False)
    totalRows = Column(Integer, default=0)
    processedRows = Column(Integer, default=0)
    successCount = Column(Integer, default=0)
    failedCount = Column(Integer, default=0)
    errors = relationship("JobError", back_populates="job", cascade="all, delete-orphan")
    createdAt = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completedAt = Column(DateTime(timezone=True), nullable=True)


class JobError(Base):
    __tablename__ = "job_errors"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    job_id = Column(String(36), ForeignKey("jobs._id"), nullable=False, index=True)
    error_message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    job = relationship("Job", back_populates="errors")


class Customer(Base):
    __tablename__ = "customers"

    _id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    phone = Column(String(50), nullable=True)
    company = Column(String(255), nullable=False)
    jobId = Column(String(36), ForeignKey("jobs._id"), nullable=False, index=True)
    createdAt = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
