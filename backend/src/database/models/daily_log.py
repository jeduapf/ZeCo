"""
DailyLog database model with i18n logging integration
Daily business summary for high-level operational insights
"""
from sqlalchemy import Column, Integer, Float, Date, Text
from sqlalchemy.orm import validates
from datetime import date, datetime, timezone, timedelta
from src.database.base import Base
from typing import List, Dict, Optional
from src.core.i18n_logger import get_i18n_logger
from config import LANG

logger = get_i18n_logger("daily_log_model")


class DailyLog(Base):
    """
    DailyLog captures a snapshot of the restaurant's performance for each day.
    
    Think of this as your daily report card - at the end of each day, the system
    automatically calculates and stores key metrics that tell you how the business
    performed. This makes it incredibly fast to pull up historical data without
    having to re-aggregate thousands of orders every time.
    
    Why we need this:
    - Performance tracking: See at a glance how busy each day was
    - Trend analysis: Compare today to last week, last month, last year
    - Quick reporting: Generate weekly/monthly reports by summing daily logs
    - Anomaly detection: Spot unusual days (surprisingly low revenue, etc.)
    
    What gets tracked:
    - total_customers: How many people ate here today
    - total_revenue: All money brought in from orders
    - total_expenses: Rough daily operating costs (can be detailed elsewhere)
    - worked_time: Total staff hours for labor cost calculation
    
    Security Note:
    This contains sensitive financial data - ADMIN access only.
    
    Design philosophy:
    These logs are created automatically at end-of-day (or start of next day).
    They can be manually corrected by admins if mistakes are found.
    They should NEVER be deleted - if wrong, create a correcting entry.
    """
    __tablename__ = "daily_logs"
    
    # === Core Identity ===
    id = Column(Integer, primary_key=True, index=True)
    
    # === Date Tracking ===
    log_date = Column(
        Date, 
        unique=True,  # Only one log per date
        nullable=False,
        index=True  # Heavily queried for date ranges
    )
    
    # === Customer Metrics ===
    total_customers = Column(
        Integer, 
        nullable=False, 
        default=0
    )  # Sum of all num_customers from orders
    
    # === Financial Metrics ===
    total_revenue = Column(
        Float, 
        nullable=False, 
        default=0.0
    )  # Sum of all completed order totals
    
    total_expenses = Column(
        Float, 
        nullable=False, 
        default=0.0
    )  # Daily costs (food, supplies, utilities, etc.)
    
    # === Labor Metrics ===
    worked_time = Column(
        Float, 
        nullable=False, 
        default=0.0
    )  # Total staff hours worked this day
    
    # === Optional Notes ===
    notes = Column(
        Text, 
        nullable=True
    )  # For recording special events ("Valentine's Day rush", "Power outage 2-4pm")
    
    # === Helper Methods ===
    
    def calculate_net_profit(self) -> float:
        """
        Calculate the day's profit (revenue minus expenses).
        
        Returns:
            Net profit for the day (can be negative on bad days)
        """
        return self.total_revenue - self.total_expenses
    
    def calculate_profit_margin(self) -> float:
        """
        Calculate profit margin as a percentage.
        
        Returns:
            Profit margin (0.0 to 1.0, where 0.3 = 30% margin)
        """
        if self.total_revenue == 0:
            return 0.0
        
        return self.calculate_net_profit() / self.total_revenue
    
    def calculate_revenue_per_customer(self) -> float:
        """
        Calculate average spend per customer.
        
        This is a key metric: are customers spending more or less over time?
        
        Returns:
            Average revenue per customer
        """
        if self.total_customers == 0:
            return 0.0
        
        return self.total_revenue / self.total_customers
    
    def calculate_labor_cost_percentage(self) -> float:
        """
        Calculate what percentage of revenue went to labor costs.
        
        Industry standard: good restaurants aim for 25-35% labor cost.
        Too high = overstaffed or underpaying.
        Too low = understaffed or overworking employees.
        
        Note: This requires knowing hourly wage rates, which aren't stored here.
        For now, this just returns the ratio of hours to revenue.
        
        Returns:
            Ratio of worked hours to revenue (you'll need wages to calculate actual cost %)
        """
        if self.total_revenue == 0:
            return 0.0
        
        return self.worked_time / self.total_revenue
    
    def is_weekend(self) -> bool:
        """
        Check if this day was a weekend (Saturday or Sunday).
        
        Useful for separating weekend vs weekday analytics.
        
        Returns:
            True if Saturday or Sunday
        """
        return self.log_date.weekday() >= 5  # 5=Saturday, 6=Sunday
    
    def get_day_of_week(self) -> str:
        """
        Get the human-readable day name.
        
        Returns:
            Day name like "Monday", "Tuesday", etc.
        """
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return days[self.log_date.weekday()]
    
    @classmethod
    def generate_for_date(cls, db_session, target_date: date, notes: Optional[str] = None):
        """
        Generate a DailyLog by aggregating all data for a specific date.
        
        This is typically called automatically at end-of-day, but can also be
        run manually by an admin to backfill historical data.
        
        Process:
        1. Get all completed orders for this date
        2. Sum up revenue and customer counts
        3. Get all shifts for this date
        4. Sum up worked hours
        5. Create or update the DailyLog entry
        
        Args:
            db_session: Active database session
            target_date: The date to generate the log for
            notes: Optional notes about this day
            
        Returns:
            The created or updated DailyLog
        """
        from src.database.models.order import Order, OrderStatus
        from src.database.models.staff_shift import StaffShift
        
        logger.info(
            "daily_log.generating",
            language=LANG,
            date=target_date.isoformat()
        )
        
        # Check if log already exists
        existing_log = db_session.query(cls).filter(cls.log_date == target_date).first()
        
        # Define the time window for this date
        start_of_day = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_of_day = start_of_day + timedelta(days=1)
        
        # Aggregate order data
        completed_orders = db_session.query(Order).filter(
            Order.status == OrderStatus.COMPLETED,
            Order.finished_at >= start_of_day,
            Order.finished_at < end_of_day
        ).all()
        
        total_revenue = sum(order.total_amount for order in completed_orders)
        total_customers = sum(order.num_customers for order in completed_orders if order.num_customers)
        
        # Aggregate shift data
        shifts = StaffShift.get_shifts_for_date(db_session, target_date)
        worked_time = StaffShift.calculate_total_hours(shifts)
        
        # Create or update log
        if existing_log:
            existing_log.total_customers = total_customers
            existing_log.total_revenue = total_revenue
            existing_log.worked_time = worked_time
            if notes:
                existing_log.notes = notes
            
            logger.info(
                "daily_log.updated",
                language=LANG,
                date=target_date.isoformat(),
                revenue=f"€{total_revenue:.2f}",
                customers=total_customers
            )
            
            daily_log = existing_log
        else:
            daily_log = cls(
                log_date=target_date,
                total_customers=total_customers,
                total_revenue=total_revenue,
                total_expenses=0.0,  # To be set manually or from expense tracking
                worked_time=worked_time,
                notes=notes
            )
            db_session.add(daily_log)
            
            logger.info(
                "daily_log.created",
                language=LANG,
                date=target_date.isoformat(),
                revenue=f"€{total_revenue:.2f}",
                customers=total_customers
            )
        
        db_session.commit()
        return daily_log
    
    @classmethod
    def get_date_range(cls, db_session, start_date: date, end_date: date) -> List['DailyLog']:
        """
        Get all daily logs within a date range.
        
        Perfect for:
        - Weekly reports (last 7 days)
        - Monthly reports (this month)
        - Comparative analysis (this month vs last month)
        
        Args:
            db_session: Active database session
            start_date: Beginning of range
            end_date: End of range (inclusive)
            
        Returns:
            List of DailyLog entries, ordered by date
        """
        return db_session.query(cls).filter(
            cls.log_date >= start_date,
            cls.log_date <= end_date
        ).order_by(cls.log_date).all()
    
    @classmethod
    def get_weekly_summary(cls, db_session, week_start: date) -> Dict:
        """
        Get aggregated metrics for a week.
        
        Args:
            db_session: Active database session
            week_start: Monday of the week to analyze
            
        Returns:
            Dictionary with weekly totals and averages
        """
        week_end = week_start + timedelta(days=6)
        logs = cls.get_date_range(db_session, week_start, week_end)
        
        if not logs:
            return {
                'total_revenue': 0.0,
                'total_customers': 0,
                'total_worked_hours': 0.0,
                'avg_daily_revenue': 0.0,
                'avg_customers_per_day': 0.0,
                'days_with_data': 0
            }
        
        return {
            'total_revenue': sum(log.total_revenue for log in logs),
            'total_customers': sum(log.total_customers for log in logs),
            'total_worked_hours': sum(log.worked_time for log in logs),
            'avg_daily_revenue': sum(log.total_revenue for log in logs) / len(logs),
            'avg_customers_per_day': sum(log.total_customers for log in logs) / len(logs),
            'days_with_data': len(logs),
            'best_day': max(logs, key=lambda x: x.total_revenue).log_date,
            'worst_day': min(logs, key=lambda x: x.total_revenue).log_date
        }
    
    @classmethod
    def compare_to_previous_week(cls, db_session, current_week_start: date) -> Dict:
        """
        Compare current week's performance to previous week.
        
        Returns percentage changes in key metrics.
        
        Args:
            db_session: Active database session
            current_week_start: Monday of current week
            
        Returns:
            Dictionary with comparison metrics
        """
        current = cls.get_weekly_summary(db_session, current_week_start)
        previous_start = current_week_start - timedelta(days=7)
        previous = cls.get_weekly_summary(db_session, previous_start)
        
        def calc_change(current_val, previous_val):
            if previous_val == 0:
                return 0.0
            return ((current_val - previous_val) / previous_val) * 100
        
        return {
            'revenue_change_pct': calc_change(current['total_revenue'], previous['total_revenue']),
            'customer_change_pct': calc_change(current['total_customers'], previous['total_customers']),
            'current_week': current,
            'previous_week': previous
        }
    
    @validates('total_customers')
    def validate_customers(self, key, value):
        """Ensure customer count is non-negative"""
        if value < 0:
            logger.error(
                "error.validation",
                language=LANG,
                field="total_customers",
                message=f"Customer count cannot be negative, got {value}"
            )
            raise ValueError("Customer count cannot be negative")
        return value
    
    @validates('total_revenue', 'total_expenses', 'worked_time')
    def validate_positive_numbers(self, key, value):
        """Ensure financial metrics are non-negative"""
        if value < 0:
            logger.error(
                "error.validation",
                language=LANG,
                field=key,
                message=f"{key} cannot be negative, got {value}"
            )
            raise ValueError(f"{key} cannot be negative")
        return value
    
    def __repr__(self):
        profit = self.calculate_net_profit()
        profit_str = f"+€{profit:.2f}" if profit >= 0 else f"-€{abs(profit):.2f}"
        return (
            f"<DailyLog {self.log_date} - "
            f"{self.total_customers} customers - "
            f"€{self.total_revenue:.2f} revenue - "
            f"{profit_str} profit>"
        )