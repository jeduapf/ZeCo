"""
Staff Shift Service with integrated permission checking
This demonstrates how to use the ModelPermissions system in service methods
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from src.database.models.staff_shift import StaffShift, ShiftRole
from src.database.models.user import User
from src.core.permissions import require_admin, require_read, require_write
from datetime import datetime, timezone, date
from typing import List, Optional


class StaffShiftService:
    """
    Service layer for staff shift management.
    
    All methods here automatically check permissions using decorators.
    Only admins can access staff shift data due to its sensitive nature
    (work hours = salary information).
    """
    
    @staticmethod
    @require_admin  # Only admins can view shift data
    def get_all_shifts(db: Session, user: User) -> List[StaffShift]:
        """
        Get all staff shifts in the database.
        
        Security: Admin-only (enforced by decorator)
        
        Args:
            db: Database session
            user: The user making the request (for permission check)
            
        Returns:
            List of all shifts
        """
        return db.query(StaffShift).all()
    
    @staticmethod
    @require_admin
    def get_shift_by_id(db: Session, shift_id: int, user: User) -> StaffShift:
        """
        Get a specific shift by ID.
        
        Security: Admin-only
        
        Args:
            db: Database session
            shift_id: The shift's ID
            user: The user making the request
            
        Returns:
            StaffShift object
            
        Raises:
            HTTPException: If shift not found
        """
        shift = db.query(StaffShift).filter(StaffShift.id == shift_id).first()
        
        if not shift:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shift with ID {shift_id} not found"
            )
        
        return shift
    
    @staticmethod
    @require_admin
    def clock_in(
        db: Session, 
        staff_user_id: int, 
        role: ShiftRole, 
        admin_user: User
    ) -> StaffShift:
        """
        Clock in a staff member (start a new shift).
        
        Security: Admin-only (you don't want employees clocking themselves in)
        
        Args:
            db: Database session
            staff_user_id: ID of the employee clocking in
            role: Role they're working (waiter or kitchen)
            admin_user: The admin performing this action
            
        Returns:
            The newly created StaffShift
            
        Raises:
            HTTPException: If staff member already has an active shift
        """
        # Check if this user already has an active shift
        existing_active = db.query(StaffShift).filter(
            StaffShift.user_id == staff_user_id,
            StaffShift.shift_end == None  # Active shift has no end time
        ).first()
        
        if existing_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee is already clocked in (shift #{existing_active.id})"
            )
        
        # Create new shift
        new_shift = StaffShift(
            user_id=staff_user_id,
            shift_start=datetime.now(timezone.utc),
            role=role
        )
        
        db.add(new_shift)
        db.commit()
        db.refresh(new_shift)
        
        return new_shift
    
    @staticmethod
    @require_admin
    def clock_out(db: Session, shift_id: int, admin_user: User) -> StaffShift:
        """
        Clock out a staff member (end their shift).
        
        Security: Admin-only
        
        Args:
            db: Database session
            shift_id: ID of the shift to end
            admin_user: The admin performing this action
            
        Returns:
            The updated StaffShift with end time set
            
        Raises:
            HTTPException: If shift not found or already ended
        """
        shift = StaffShiftService.get_shift_by_id(db, shift_id, admin_user)
        
        if not shift.is_active():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Shift #{shift_id} has already ended"
            )
        
        shift.clock_out(db)
        
        return shift
    
    @staticmethod
    @require_admin
    def get_active_shifts(db: Session, user: User) -> List[StaffShift]:
        """
        Get all currently active shifts (employees currently working).
        
        Useful for:
        - Seeing who's at work right now
        - Real-time labor cost monitoring
        - Emergency contact lists
        
        Security: Admin-only
        
        Args:
            db: Database session
            user: Admin user making the request
            
        Returns:
            List of active shifts
        """
        return StaffShift.get_active_shifts(db)
    
    @staticmethod
    @require_admin
    def get_shifts_for_date(
        db: Session, 
        target_date: date, 
        user: User
    ) -> List[StaffShift]:
        """
        Get all shifts that occurred on a specific date.
        
        Perfect for:
        - Daily labor reports
        - Attendance tracking
        - Verifying schedules
        
        Security: Admin-only
        
        Args:
            db: Database session
            target_date: The date to query
            user: Admin user making the request
            
        Returns:
            List of shifts for that date
        """
        return StaffShift.get_shifts_for_date(db, target_date)
    
    @staticmethod
    @require_admin
    def get_user_monthly_hours(
        db: Session,
        staff_user_id: int,
        year: int,
        month: int,
        admin_user: User
    ) -> dict:
        """
        Calculate total hours worked by a specific employee in a month.
        
        This is essential for payroll processing.
        
        Security: Admin-only (sensitive payroll data)
        
        Args:
            db: Database session
            staff_user_id: ID of the employee
            year: Year
            month: Month number (1-12)
            admin_user: Admin making the request
            
        Returns:
            Dictionary with hours worked and shift details
        """
        staff_user = db.query(User).filter(User.id == staff_user_id).first()
        
        if not staff_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {staff_user_id} not found"
            )
        
        # Get all shifts for this user in this month
        month_start = date(year, month, 1)
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        
        shifts = db.query(StaffShift).filter(
            StaffShift.user_id == staff_user_id,
            StaffShift.shift_start >= datetime.combine(month_start, datetime.min.time()).replace(tzinfo=timezone.utc),
            StaffShift.shift_start < datetime.combine(next_month, datetime.min.time()).replace(tzinfo=timezone.utc)
        ).all()
        
        total_hours = StaffShift.calculate_total_hours(shifts)
        
        # Calculate regular vs overtime
        regular_hours = 0.0
        overtime_hours = 0.0
        
        for shift in shifts:
            shift_hours = shift.get_duration_hours()
            if shift_hours:
                if shift.is_overtime():
                    regular_hours += 8.0  # Assuming 8 hour standard
                    overtime_hours += shift.get_overtime_hours()
                else:
                    regular_hours += shift_hours
        
        return {
            'user_id': staff_user_id,
            'username': staff_user.username,
            'month': f"{year}-{month:02d}",
            'total_hours': total_hours,
            'regular_hours': regular_hours,
            'overtime_hours': overtime_hours,
            'shift_count': len(shifts),
            'shifts': [
                {
                    'id': shift.id,
                    'start': shift.shift_start.isoformat(),
                    'end': shift.shift_end.isoformat() if shift.shift_end else None,
                    'duration': shift.get_duration_formatted(),
                    'role': shift.role.value
                }
                for shift in shifts
            ]
        }
    
    @staticmethod
    @require_admin
    def calculate_labor_cost_for_month(
        db: Session,
        year: int,
        month: int,
        hourly_rates: dict,  # Format: {user_id: hourly_rate}
        admin_user: User
    ) -> dict:
        """
        Calculate total labor cost for all employees in a month.
        
        This is crucial for:
        - Budget management
        - Profit margin analysis
        - Cost optimization
        
        Security: Admin-only (highly sensitive financial data)
        
        Args:
            db: Database session
            year: Year
            month: Month number
            hourly_rates: Dictionary mapping user_id to their hourly pay rate
            admin_user: Admin making the request
            
        Returns:
            Dictionary with labor cost breakdown
        """
        # Get all shifts for this month
        month_start = date(year, month, 1)
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        
        all_shifts = db.query(StaffShift).filter(
            StaffShift.shift_start >= datetime.combine(month_start, datetime.min.time()).replace(tzinfo=timezone.utc),
            StaffShift.shift_start < datetime.combine(next_month, datetime.min.time()).replace(tzinfo=timezone.utc)
        ).all()
        
        # Calculate costs per employee
        costs_by_employee = {}
        total_cost = 0.0
        
        for shift in all_shifts:
            if shift.user_id not in costs_by_employee:
                costs_by_employee[shift.user_id] = {
                    'username': shift.user.username if shift.user else 'Unknown',
                    'hours': 0.0,
                    'cost': 0.0,
                    'shifts': 0
                }
            
            hours = shift.get_duration_hours()
            if hours:
                costs_by_employee[shift.user_id]['hours'] += hours
                costs_by_employee[shift.user_id]['shifts'] += 1
                
                # Calculate cost if we have the hourly rate
                if shift.user_id in hourly_rates:
                    cost = hours * hourly_rates[shift.user_id]
                    costs_by_employee[shift.user_id]['cost'] += cost
                    total_cost += cost
        
        return {
            'month': f"{year}-{month:02d}",
            'total_labor_cost': total_cost,
            'total_shifts': len(all_shifts),
            'employees': costs_by_employee,
            'average_cost_per_shift': total_cost / len(all_shifts) if all_shifts else 0.0
        }


# Example of how this would be used in an API endpoint:
"""
from fastapi import APIRouter, Depends
from core.dependencies import DbDependency, AdminUser
from services.staff_shift_service import StaffShiftService

router = APIRouter(prefix="/shifts", tags=["Staff Shifts"])

@router.get("/active")
async def get_active_shifts(
    db: DbDependency,
    admin: AdminUser  # This ensures only admins can access
):
    # The service method has its own @require_admin decorator as a second layer
    return StaffShiftService.get_active_shifts(db, admin)

@router.post("/clock-in")
async def clock_in_employee(
    staff_user_id: int,
    role: ShiftRole,
    db: DbDependency,
    admin: AdminUser
):
    return StaffShiftService.clock_in(db, staff_user_id, role, admin)
"""