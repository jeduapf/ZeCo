"""
StaffShift database model with i18n logging integration
Admin-only access for shift management and payroll calculations
"""
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship, validates
from datetime import datetime, timezone, timedelta
from database.base import Base
from enum import StrEnum
from typing import Optional
from core.i18n_logger import get_i18n_logger
from config import LANG

logger = get_i18n_logger("staff_shift_model")


class ShiftRole(StrEnum):
    """Role the staff member performed during this shift"""
    WAITER = "waiter"
    KITCHEN = "kitchen"


class StaffShift(Base):
    """
    StaffShift tracks when employees clock in and out for their shifts.
    
    This is crucial for:
    - Payroll calculation (how many hours each employee worked)
    - Labor cost analysis (what percentage of revenue goes to staff?)
    - Compliance with labor laws (overtime tracking, break requirements)
    - Performance analysis (who works which shifts, productivity patterns)
    
    Security Note:
    This table contains sensitive employee data (work hours = salary data).
    Access is restricted to ADMIN role only via ModelPermissions.
    
    Design decisions:
    - We store the role performed during THIS shift, not the user's permanent role
      (someone might be cross-trained and work kitchen one day, waiter the next)
    - shift_end can be null (employee hasn't clocked out yet)
    - All times are UTC with timezone awareness for consistency
    """
    __tablename__ = "staff_shifts"
    
    # === Core Identity ===
    id = Column(Integer, primary_key=True, index=True)
    
    # === Foreign Keys ===
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # === Shift Timing ===
    shift_start = Column(
        DateTime(timezone=True), 
        nullable=False,
        index=True  # Indexed for queries like "all shifts in date range"
    )
    shift_end = Column(
        DateTime(timezone=True), 
        nullable=True  # Null means shift is still ongoing
    )
    
    # === Role During This Shift ===
    role = Column(
        SQLAlchemyEnum(ShiftRole),
        nullable=False,
        index=True  # Indexed for role-based analytics
    )
    
    # === Relationships ===
    user = relationship("User", back_populates="staff_shifts")
    
    # === Helper Methods ===
    
    def is_active(self) -> bool:
        """Check if this shift is currently ongoing (employee hasn't clocked out)"""
        return self.shift_end is None
    
    def get_duration_hours(self) -> Optional[float]:
        """
        Calculate how long this shift lasted in hours.
        
        Returns:
            Hours worked, or None if shift is still active
        """
        if self.shift_end is None:
            # Shift ongoing - calculate from start to now
            duration = datetime.now(timezone.utc) - self.shift_start
        else:
            duration = self.shift_end - self.shift_start
        
        return duration.total_seconds() / 3600  # Convert seconds to hours
    
    def get_duration_formatted(self) -> str:
        """
        Get a human-readable duration string.
        
        Returns:
            String like "8 hours 30 minutes" or "Ongoing (5 hours so far)"
        """
        hours = self.get_duration_hours()
        if hours is None:
            return "Not ended"
        
        full_hours = int(hours)
        minutes = int((hours - full_hours) * 60)
        
        if self.is_active():
            return f"Ongoing ({full_hours}h {minutes}m so far)"
        else:
            return f"{full_hours}h {minutes}m"
    
    def clock_out(self, db_session):
        """
        End this shift by setting the end time to now.
        
        This should be called when an employee clocks out at the end of their shift.
        """
        if not self.is_active():
            logger.warning(
                "staff_shift.already_ended",
                language=LANG,
                shift_id=self.id,
                username=self.user.username if self.user else "unknown"
            )
            return
        
        self.shift_end = datetime.now(timezone.utc)
        duration = self.get_duration_hours()
        
        logger.info(
            "staff_shift.clocked_out",
            language=LANG,
            username=self.user.username if self.user else "unknown",
            duration=f"{duration:.2f} hours",
            role=self.role.value
        )
        
        db_session.commit()
    
    def calculate_labor_cost(self, hourly_rate: float) -> float:
        """
        Calculate the labor cost for this shift.
        
        Args:
            hourly_rate: The employee's pay rate per hour
            
        Returns:
            Total cost for this shift (hours × rate)
        """
        hours = self.get_duration_hours()
        if hours is None:
            return 0.0
        
        return hours * hourly_rate
    
    def is_overtime(self, regular_hours: float = 8.0) -> bool:
        """
        Check if this shift qualifies as overtime.
        
        Args:
            regular_hours: Number of hours before overtime kicks in (default 8)
            
        Returns:
            True if shift exceeds regular hours
        """
        hours = self.get_duration_hours()
        if hours is None:
            return False
        
        return hours > regular_hours
    
    def get_overtime_hours(self, regular_hours: float = 8.0) -> float:
        """
        Calculate how many overtime hours were worked.
        
        Args:
            regular_hours: Number of hours before overtime (default 8)
            
        Returns:
            Number of overtime hours, or 0 if no overtime
        """
        hours = self.get_duration_hours()
        if hours is None or hours <= regular_hours:
            return 0.0
        
        return hours - regular_hours
    
    @classmethod
    def get_active_shifts(cls, db_session):
        """
        Get all currently active shifts (employees currently working).
        
        This is useful for:
        - Real-time staff tracking (who's working right now?)
        - Emergency contact lists
        - Labor cost monitoring in real-time
        
        Args:
            db_session: Active database session
            
        Returns:
            List of StaffShift objects that are ongoing
        """
        return db_session.query(cls).filter(cls.shift_end == None).all()
    
    @classmethod
    def get_shifts_for_date(cls, db_session, target_date: datetime.date):
        """
        Get all shifts that occurred on a specific date.
        
        Useful for:
        - Daily labor cost reports
        - Attendance tracking
        - Shift schedule verification
        
        Args:
            db_session: Active database session
            target_date: The date to query
            
        Returns:
            List of shifts that started on the given date
        """
        start_of_day = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_of_day = start_of_day + timedelta(days=1)
        
        return db_session.query(cls).filter(
            cls.shift_start >= start_of_day,
            cls.shift_start < end_of_day
        ).all()
    
    @classmethod
    def get_user_shifts_in_range(
        cls, 
        db_session, 
        user_id: int, 
        start_date: datetime, 
        end_date: datetime
    ):
        """
        Get all shifts for a specific user within a date range.
        
        Perfect for:
        - Generating individual payroll reports
        - Calculating monthly hours worked
        - Verifying submitted timesheets
        
        Args:
            db_session: Active database session
            user_id: The employee's user ID
            start_date: Beginning of date range
            end_date: End of date range
            
        Returns:
            List of shifts for this user in the date range
        """
        return db_session.query(cls).filter(
            cls.user_id == user_id,
            cls.shift_start >= start_date,
            cls.shift_start <= end_date
        ).order_by(cls.shift_start).all()
    
    @classmethod
    def calculate_total_hours(cls, shifts: list) -> float:
        """
        Calculate total hours worked across multiple shifts.
        
        Args:
            shifts: List of StaffShift objects
            
        Returns:
            Total hours worked across all shifts
        """
        total = 0.0
        for shift in shifts:
            hours = shift.get_duration_hours()
            if hours:
                total += hours
        
        return total
    
    @validates('shift_start')
    def validate_shift_start(self, key, value):
        """Ensure shift start time is not in the future"""
        if value > datetime.now(timezone.utc):
            logger.error(
                "error.validation",
                language=LANG,
                field="shift_start",
                message=f"Shift start time cannot be in the future: {value}"
            )
            raise ValueError("Shift start time cannot be in the future")
        return value
    
    @validates('shift_end')
    def validate_shift_end(self, key, value):
        """Ensure shift end time is after start time"""
        if value and hasattr(self, 'shift_start') and value < self.shift_start:
            logger.error(
                "error.validation",
                language=LANG,
                field="shift_end",
                message=f"Shift end ({value}) cannot be before start ({self.shift_start})"
            )
            raise ValueError("Shift end time must be after start time")
        return value
    
    def __repr__(self):
        status = "ACTIVE" if self.is_active() else f"ENDED ({self.get_duration_formatted()})"
        return (
            f"<StaffShift #{self.id} - "
            f"{self.user.username if self.user else 'Unknown'} - "
            f"{self.role.value} - {status}>"
        )