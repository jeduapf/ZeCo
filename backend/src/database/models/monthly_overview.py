"""
MonthlyOverview database model with i18n logging integration
Monthly financial tracking for P&L statements and budget management
"""
from sqlalchemy import Column, Integer, Float, Date, String, Text, UniqueConstraint
from sqlalchemy.orm import validates
from datetime import date, timedelta
from src.database.base import Base
from enum import StrEnum
from typing import List, Dict, Optional
from src.core.i18n_logger import get_i18n_logger
from config import LANG

logger = get_i18n_logger("monthly_overview_model")


class FinancialCategory(StrEnum):
    """
    Categories for financial tracking in a restaurant.
    
    This enum defines all the different types of income and expenses you might
    track. Having standardized categories makes it easy to generate consistent
    reports and compare month-to-month.
    """
    # === Revenue Categories ===
    REVENUE = "revenue"  # Total sales from customers
    
    # === Cost of Goods Sold (COGS) ===
    FOOD_COST = "food_cost"  # Money spent on ingredients
    BEVERAGE_COST = "beverage_cost"  # Money spent on drinks
    
    # === Labor Costs ===
    STAFF_WAGES = "staff_wages"  # Employee salaries/hourly pay
    PAYROLL_TAX = "payroll_tax"  # Employer taxes on wages
    
    # === Operating Expenses ===
    RENT = "rent"  # Monthly rent payment
    UTILITIES = "utilities"  # Electricity, water, gas, internet
    INSURANCE = "insurance"  # Business insurance premiums
    EQUIPMENT = "equipment"  # Kitchen equipment, furniture purchases
    MAINTENANCE = "maintenance"  # Repairs and upkeep
    MARKETING = "marketing"  # Advertising, promotions
    SUPPLIES = "supplies"  # Non-food items (napkins, cleaning supplies, etc.)
    LICENSES = "licenses"  # Business licenses, health permits
    
    # === Taxes ===
    SALES_TAX = "sales_tax"  # Tax collected from customers (usually a wash)
    INCOME_TAX = "income_tax"  # Business income tax
    PROPERTY_TAX = "property_tax"  # Tax on property/building
    
    # === Other ===
    MISCELLANEOUS = "miscellaneous"  # Uncategorized expenses
    LOAN_PAYMENT = "loan_payment"  # Debt service


class MonthlyOverview(Base):
    """
    MonthlyOverview tracks all income and expenses for each month.
    
    Unlike DailyLog which is auto-generated, this table is more manual/flexible.
    It's designed to work like a traditional accounting ledger where you record
    different types of expenses throughout the month.
    
    Think of it as your monthly budget spreadsheet turned into database rows.
    Each row represents one financial entry for the month:
    - "November 2024: Rent = -€2,500"
    - "November 2024: Revenue = +€45,000"
    - "November 2024: Food Cost = -€12,000"
    
    Why this structure?
    - Flexible: Easy to add new expense categories without schema changes
    - Detailed: Can have multiple entries per category (e.g., multiple equipment purchases)
    - Traceable: Each entry can have notes explaining what it was for
    - Queryable: Easy to generate reports like "show all expenses for Q4"
    
    Security Note:
    This is highly sensitive financial data - ADMIN access only.
    
    Design decisions:
    - month_start is always the 1st of the month (2024-11-01, 2024-12-01, etc.)
    - amount is positive for income, negative for expenses
    - category uses enum to ensure consistency in reports
    - Multiple entries per category/month allowed (for detailed tracking)
    """
    __tablename__ = "monthly_overview"
    
    # === Core Identity ===
    id = Column(Integer, primary_key=True, index=True)
    
    # === Time Period ===
    month_start = Column(
        Date,
        nullable=False,
        index=True  # Heavily queried for month-based reports
    )  # Always set to 1st of month (e.g., 2024-11-01)
    
    # === Financial Details ===
    category = Column(
        String(50),  # Using String instead of Enum for flexibility
        nullable=False,
        index=True  # For category-based queries
    )
    
    amount = Column(
        Float,
        nullable=False
    )  # Positive for income/revenue, negative for expenses
    
    # === Optional Context ===
    notes = Column(
        Text,
        nullable=True
    )  # Detailed description of this entry
    
    # === Constraints ===
    # Note: We DON'T make month_start + category unique because you might have
    # multiple expense entries in the same category (e.g., two equipment purchases)
    
    # === Helper Methods ===
    
    def is_income(self) -> bool:
        """Check if this entry represents income"""
        return self.amount > 0
    
    def is_expense(self) -> bool:
        """Check if this entry represents an expense"""
        return self.amount < 0
    
    def get_absolute_amount(self) -> float:
        """Get the amount as a positive number (for display purposes)"""
        return abs(self.amount)
    
    @classmethod
    def get_month_entries(cls, db_session, year: int, month: int) -> List['MonthlyOverview']:
        """
        Get all financial entries for a specific month.
        
        Args:
            db_session: Active database session
            year: Year (e.g., 2024)
            month: Month number (1-12)
            
        Returns:
            List of all entries for that month
        """
        month_start = date(year, month, 1)
        
        return db_session.query(cls).filter(
            cls.month_start == month_start
        ).all()
    
    @classmethod
    def calculate_monthly_totals(cls, db_session, year: int, month: int) -> Dict:
        """
        Calculate key financial metrics for a month.
        
        This generates a mini profit & loss statement:
        - Total revenue
        - Total expenses
        - Net profit
        - Profit margin
        - Breakdown by category
        
        Args:
            db_session: Active database session
            year: Year
            month: Month number
            
        Returns:
            Dictionary with financial summary
        """
        entries = cls.get_month_entries(db_session, year, month)
        
        if not entries:
            return {
                'total_revenue': 0.0,
                'total_expenses': 0.0,
                'net_profit': 0.0,
                'profit_margin': 0.0,
                'by_category': {}
            }
        
        # Separate income and expenses
        revenue_entries = [e for e in entries if e.is_income()]
        expense_entries = [e for e in entries if e.is_expense()]
        
        total_revenue = sum(e.amount for e in revenue_entries)
        total_expenses = abs(sum(e.amount for e in expense_entries))
        net_profit = total_revenue - total_expenses
        profit_margin = (net_profit / total_revenue) if total_revenue > 0 else 0.0
        
        # Break down by category
        by_category = {}
        for entry in entries:
            if entry.category not in by_category:
                by_category[entry.category] = 0.0
            by_category[entry.category] += entry.amount
        
        return {
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
            'profit_margin': profit_margin * 100,  # As percentage
            'by_category': by_category,
            'entries_count': len(entries)
        }
    
    @classmethod
    def compare_months(cls, db_session, year1: int, month1: int, year2: int, month2: int) -> Dict:
        """
        Compare financial performance between two months.
        
        Useful for:
        - Month-over-month growth analysis
        - Year-over-year comparisons (Nov 2024 vs Nov 2023)
        - Identifying trends and anomalies
        
        Args:
            db_session: Active database session
            year1, month1: First month to compare
            year2, month2: Second month to compare
            
        Returns:
            Dictionary with comparison metrics
        """
        summary1 = cls.calculate_monthly_totals(db_session, year1, month1)
        summary2 = cls.calculate_monthly_totals(db_session, year2, month2)
        
        def calc_change(val1, val2):
            if val2 == 0:
                return 0.0
            return ((val1 - val2) / val2) * 100
        
        return {
            'month1': f"{year1}-{month1:02d}",
            'month2': f"{year2}-{month2:02d}",
            'revenue_change_pct': calc_change(summary1['total_revenue'], summary2['total_revenue']),
            'expense_change_pct': calc_change(summary1['total_expenses'], summary2['total_expenses']),
            'profit_change_pct': calc_change(summary1['net_profit'], summary2['net_profit']),
            'month1_summary': summary1,
            'month2_summary': summary2
        }
    
    @classmethod
    def get_yearly_summary(cls, db_session, year: int) -> Dict:
        """
        Calculate financial metrics for an entire year.
        
        This is your annual P&L statement, perfect for:
        - Tax preparation
        - Annual reports
        - Investment pitches
        - Performance reviews
        
        Args:
            db_session: Active database session
            year: The year to analyze
            
        Returns:
            Dictionary with yearly totals and monthly breakdown
        """
        monthly_summaries = []
        
        for month in range(1, 13):
            summary = cls.calculate_monthly_totals(db_session, year, month)
            summary['month'] = f"{year}-{month:02d}"
            monthly_summaries.append(summary)
        
        total_revenue = sum(m['total_revenue'] for m in monthly_summaries)
        total_expenses = sum(m['total_expenses'] for m in monthly_summaries)
        net_profit = total_revenue - total_expenses
        
        return {
            'year': year,
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
            'profit_margin': (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0,
            'monthly_breakdown': monthly_summaries,
            'avg_monthly_revenue': total_revenue / 12,
            'avg_monthly_profit': net_profit / 12
        }
    
    @classmethod
    def get_top_expenses(cls, db_session, year: int, month: int, limit: int = 5) -> List[Dict]:
        """
        Get the largest expense entries for a month.
        
        Helps identify where money is going and what to optimize.
        
        Args:
            db_session: Active database session
            year: Year
            month: Month number
            limit: How many top expenses to return
            
        Returns:
            List of expense entries sorted by amount (highest first)
        """
        entries = cls.get_month_entries(db_session, year, month)
        expense_entries = [e for e in entries if e.is_expense()]
        
        # Sort by absolute amount (largest expenses first)
        expense_entries.sort(key=lambda x: abs(x.amount), reverse=True)
        
        return [
            {
                'category': e.category,
                'amount': abs(e.amount),
                'notes': e.notes
            }
            for e in expense_entries[:limit]
        ]
    
    @classmethod
    def add_entry(
        cls,
        db_session,
        year: int,
        month: int,
        category: str,
        amount: float,
        notes: Optional[str] = None
    ) -> 'MonthlyOverview':
        """
        Add a new financial entry for a month.
        
        This is the main method admins use to record income and expenses.
        
        Args:
            db_session: Active database session
            year: Year
            month: Month number
            category: Financial category (use FinancialCategory enum values)
            amount: Amount (positive for income, negative for expense)
            notes: Optional description
            
        Returns:
            The created entry
        """
        month_start = date(year, month, 1)
        
        entry = cls(
            month_start=month_start,
            category=category,
            amount=amount,
            notes=notes
        )
        
        db_session.add(entry)
        db_session.commit()
        
        entry_type = "income" if amount > 0 else "expense"
        
        logger.info(
            "monthly_overview.entry_added",
            language=LANG,
            month=f"{year}-{month:02d}",
            category=category,
            amount=f"€{abs(amount):.2f}",
            type=entry_type
        )
        
        return entry
    
    @validates('month_start')
    def validate_month_start(self, key, value):
        """Ensure month_start is always the 1st of a month"""
        if value.day != 1:
            corrected = value.replace(day=1)
            logger.warning(
                "monthly_overview.date_corrected",
                language=LANG,
                provided=value.isoformat(),
                corrected=corrected.isoformat()
            )
            return corrected
        return value
    
    def __repr__(self):
        sign = "+" if self.amount >= 0 else "-"
        return (
            f"<MonthlyOverview {self.month_start.strftime('%Y-%m')} - "
            f"{self.category} - {sign}€{abs(self.amount):.2f}>"
        )