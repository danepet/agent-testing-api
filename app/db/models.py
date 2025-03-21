from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Job(Base):
    """Database model for batch execution jobs."""
    
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True)
    batch_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    total_tests = Column(Integer, default=0)
    completed_tests = Column(Integer, default=0)
    failed_tests = Column(Integer, default=0)
    current_test_id = Column(String, nullable=True)
    current_turn = Column(Integer, nullable=True)
    progress = Column(Float, default=0)
    error = Column(Text, nullable=True)
    
    test_results = relationship("TestResult", back_populates="job", cascade="all, delete-orphan")


class TestResult(Base):
    """Database model for test results."""
    
    __tablename__ = "test_results"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String, ForeignKey("jobs.id"))
    test_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    total_validations = Column(Integer, default=0)
    passed_validations = Column(Integer, default=0)
    failed_validations = Column(Integer, default=0)
    pass_rate = Column(Float, default=0)
    avg_response_time = Column(Float, default=0)
    
    job = relationship("Job", back_populates="test_results")
    turn_results = relationship("TurnResult", back_populates="test_result", cascade="all, delete-orphan")


class TurnResult(Base):
    """Database model for turn results."""
    
    __tablename__ = "turn_results"
    
    id = Column(Integer, primary_key=True)
    test_result_id = Column(Integer, ForeignKey("test_results.id"))
    turn_id = Column(String, nullable=False)
    order = Column(Integer, nullable=False)
    user_input = Column(Text, nullable=False)
    agent_response = Column(Text, nullable=False)
    scraped_content = Column(Text, nullable=True)
    response_time_ms = Column(Integer, default=0)
    validations_total = Column(Integer, default=0)
    validations_passed = Column(Integer, default=0)
    validations_failed = Column(Integer, default=0)
    
    test_result = relationship("TestResult", back_populates="turn_results")
    validation_results = relationship("ValidationResult", back_populates="turn_result", cascade="all, delete-orphan")


class ValidationResult(Base):
    """Database model for validation results."""
    
    __tablename__ = "validation_results"
    
    id = Column(Integer, primary_key=True)
    turn_result_id = Column(Integer, ForeignKey("turn_results.id"))
    validation_id = Column(String, nullable=False)
    validation_type = Column(String, nullable=False)
    is_passed = Column(Boolean, default=False)
    score = Column(Float, nullable=True)
    details = Column(JSON, nullable=True)
    
    turn_result = relationship("TurnResult", back_populates="validation_results")