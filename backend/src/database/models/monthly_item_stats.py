"""
MonthlyItemStats database model with i18n logging integration
Menu item performance analytics for data-driven menu optimization
"""
from sqlalchemy import Column, Integer, Float, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, validates
from datetime import date
from database.base import Base
from typing import List, Dict, Optional
from core.i18n_logger import get_i18n_logger
from config import LANG

logger = get_i18n_logger("monthly_item_stats_model")


class MonthlyItemStats(Base):
    """
    MonthlyItemStats tracks the performance of each menu item on a monthly basis.
    
    This is your menu item report card - it tells you which dishes are:
    - Selling well (high quantity_sold)
    - Making money (high revenue_generated)
    - Actually profitable (high avg_margin)
    - Underperforming (low sales, low profit)
    
    Why this matters:
    Menu engineering is crucial for restaurant success. You want to identify:
    - Stars: High popularity + high profit → Keep these!
    - Workhorses: High popularity + low profit → Raise prices or reduce cost
    - Puzzles: Low popularity + high profit → Market these better
    - Dogs: Low popularity + low profit → Remove from menu
    
    This data helps you make smart decisions about:
    - Which items to promote in marketing
    - Which items to remove to simplify the kitchen
    - Where to adjust prices
    - What ingredients to order more/less of
    
    Security Note:
    Contains profit margin data and detailed analytics - ADMIN access only.
    
    Design decisions:
    - One row per menu item per month (unique constraint)
    - Statistics are calculated and stored at end of month
    - Can be recalculated at any time if needed
    - All financial data comes from order_items table
    """
    __tablename__ = "monthly_item_stats"
    
    # === Core Identity ===
    id = Column(Integer, primary_key=True, index=True)
    
    # === Foreign Keys ===
    menu_item_id = Column(
        Integer, 
        ForeignKey("menu_items.id"),
        nullable=False,
        index=True
    )
    
    # === Time Period ===
    month_start = Column(
        Date,
        nullable=False,
        index=True
    )  # Always 1st of the month
    
    # === Performance Metrics ===
    quantity_sold = Column(
        Integer,
        nullable=False,
        default=0
    )  # How many times this item was ordered
    
    revenue_generated = Column(
        Float,
        nullable=False,
        default=0.0
    )  # Total money brought in by this item
    
    total_item_cost = Column(
        Float,
        nullable=False,
        default=0.0
    )  # Total cost to make all these items (COGS)
    
    avg_margin = Column(
        Float,
        nullable=False,
        default=0.0
    )  # Average profit margin (as decimal, 0.3 = 30%)
    
    # === Relationships ===
    menu_item = relationship("MenuItem", back_populates="monthly_stats")
    
    # === Constraints ===
    __table_args__ = (
        UniqueConstraint('menu_item_id', 'month_start', name='unique_item_month'),
    )
    
    # === Helper Methods ===
    
    def calculate_gross_profit(self) -> float:
        """
        Calculate total gross profit (revenue minus cost).
        
        Returns:
            Gross profit for this item for the month
        """
        return self.revenue_generated - self.total_item_cost
    
    def calculate_contribution_percentage(self, total_monthly_revenue: float) -> float:
        """
        Calculate what percentage of total revenue this item contributed.
        
        This shows which items are your revenue drivers.
        
        Args:
            total_monthly_revenue: Total restaurant revenue for this month
            
        Returns:
            Percentage of total revenue (0-100)
        """
        if total_monthly_revenue == 0:
            return 0.0
        
        return (self.revenue_generated / total_monthly_revenue) * 100
    
    def get_average_price(self) -> float:
        """
        Calculate average price per unit sold.
        
        Useful if prices changed during the month or if promotions were applied.
        
        Returns:
            Average selling price
        """
        if self.quantity_sold == 0:
            return 0.0
        
        return self.revenue_generated / self.quantity_sold
    
    def get_average_cost(self) -> float:
        """
        Calculate average cost per unit made.
        
        Returns:
            Average cost to produce one serving
        """
        if self.quantity_sold == 0:
            return 0.0
        
        return self.total_item_cost / self.quantity_sold
    
    def classify_item(self, avg_quantity: float, avg_margin: float) -> str:
        """
        Classify this item using menu engineering matrix.
        
        The four categories:
        - Star: Above average sales AND above average profit
        - Workhorse: Above average sales BUT below average profit
        - Puzzle: Below average sales BUT above average profit
        - Dog: Below average sales AND below average profit
        
        Args:
            avg_quantity: Average quantity sold for all items this month
            avg_margin: Average profit margin for all items this month
            
        Returns:
            Classification string: "star", "workhorse", "puzzle", or "dog"
        """
        high_quantity = self.quantity_sold >= avg_quantity
        high_margin = self.avg_margin >= avg_margin
        
        if high_quantity and high_margin:
            return "star"
        elif high_quantity and not high_margin:
            return "workhorse"
        elif not high_quantity and high_margin:
            return "puzzle"
        else:
            return "dog"
    
    @classmethod
    def generate_for_month(
        cls,
        db_session,
        year: int,
        month: int,
        menu_item_id: Optional[int] = None
    ):
        """
        Generate statistics for menu items for a specific month.
        
        This aggregates all order_items data for the month and creates/updates
        statistics entries. Run this at the end of each month, or on-demand to
        see current month progress.
        
        Args:
            db_session: Active database session
            year: Year
            month: Month number (1-12)
            menu_item_id: If specified, only generate for this item. 
                         If None, generate for all items.
        """
        from database.models.order_item import OrderItem
        from database.models.order import Order, OrderStatus
        from database.models.menu_item import MenuItem
        from datetime import datetime, timezone, timedelta
        
        month_start = date(year, month, 1)
        
        # Calculate date range for this month
        start_datetime = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            end_datetime = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end_datetime = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        
        logger.info(
            "monthly_item_stats.generating",
            language=LANG,
            month=f"{year}-{month:02d}",
            item_id=menu_item_id or "all"
        )
        
        # Determine which items to process
        if menu_item_id:
            items_to_process = [db_session.query(MenuItem).filter(
                MenuItem.id == menu_item_id
            ).first()]
        else:
            items_to_process = db_session.query(MenuItem).all()
        
        stats_created = 0
        stats_updated = 0
        
        for item in items_to_process:
            # Get all order_items for this menu item in this month
            # Only include completed orders
            order_items = db_session.query(OrderItem).join(Order).filter(
                OrderItem.item_id == item.id,
                Order.status == OrderStatus.COMPLETED,
                Order.finished_at >= start_datetime,
                Order.finished_at < end_datetime
            ).all()
            
            if not order_items:
                # No sales this month for this item
                continue
            
            # Calculate statistics
            quantity_sold = sum(oi.quantity for oi in order_items)
            revenue_generated = sum(oi.subtotal for oi in order_items)
            total_item_cost = sum(oi.total_cost for oi in order_items)
            
            # Calculate average margin
            if revenue_generated > 0:
                gross_profit = revenue_generated - total_item_cost
                avg_margin = gross_profit / revenue_generated
            else:
                avg_margin = 0.0
            
            # Check if stats already exist
            existing_stats = db_session.query(cls).filter(
                cls.menu_item_id == item.id,
                cls.month_start == month_start
            ).first()
            
            if existing_stats:
                # Update existing
                existing_stats.quantity_sold = quantity_sold
                existing_stats.revenue_generated = revenue_generated
                existing_stats.total_item_cost = total_item_cost
                existing_stats.avg_margin = avg_margin
                stats_updated += 1
            else:
                # Create new
                new_stats = cls(
                    menu_item_id=item.id,
                    month_start=month_start,
                    quantity_sold=quantity_sold,
                    revenue_generated=revenue_generated,
                    total_item_cost=total_item_cost,
                    avg_margin=avg_margin
                )
                db_session.add(new_stats)
                stats_created += 1
        
        db_session.commit()
        
        logger.info(
            "monthly_item_stats.generation_complete",
            language=LANG,
            month=f"{year}-{month:02d}",
            created=stats_created,
            updated=stats_updated
        )
    
    @classmethod
    def get_month_stats(cls, db_session, year: int, month: int) -> List['MonthlyItemStats']:
        """
        Get all item statistics for a specific month.
        
        Args:
            db_session: Active database session
            year: Year
            month: Month number
            
        Returns:
            List of stats for all items that had sales this month
        """
        month_start = date(year, month, 1)
        
        return db_session.query(cls).filter(
            cls.month_start == month_start
        ).all()
    
    @classmethod
    def get_top_sellers(cls, db_session, year: int, month: int, limit: int = 10) -> List[Dict]:
        """
        Get the best-selling items for a month.
        
        Args:
            db_session: Active database session
            year: Year
            month: Month number
            limit: How many top items to return
            
        Returns:
            List of top-selling items with their stats
        """
        stats = cls.get_month_stats(db_session, year, month)
        
        # Sort by quantity sold
        stats.sort(key=lambda x: x.quantity_sold, reverse=True)
        
        return [
            {
                'item_name': s.menu_item.name,
                'quantity_sold': s.quantity_sold,
                'revenue': s.revenue_generated,
                'profit': s.calculate_gross_profit(),
                'margin': s.avg_margin * 100  # As percentage
            }
            for s in stats[:limit]
        ]
    
    @classmethod
    def get_most_profitable(cls, db_session, year: int, month: int, limit: int = 10) -> List[Dict]:
        """
        Get the most profitable items for a month (by total gross profit).
        
        These aren't necessarily the best sellers, but they make you the most money.
        
        Args:
            db_session: Active database session
            year: Year
            month: Month number
            limit: How many top items to return
            
        Returns:
            List of most profitable items
        """
        stats = cls.get_month_stats(db_session, year, month)
        
        # Sort by gross profit
        stats.sort(key=lambda x: x.calculate_gross_profit(), reverse=True)
        
        return [
            {
                'item_name': s.menu_item.name,
                'gross_profit': s.calculate_gross_profit(),
                'quantity_sold': s.quantity_sold,
                'margin': s.avg_margin * 100
            }
            for s in stats[:limit]
        ]
    
    @classmethod
    def get_menu_engineering_analysis(cls, db_session, year: int, month: int) -> Dict:
        """
        Perform complete menu engineering analysis for the month.
        
        This classifies all items into the four quadrants and provides
        actionable recommendations.
        
        Args:
            db_session: Active database session
            year: Year
            month: Month number
            
        Returns:
            Dictionary with classified items and recommendations
        """
        stats = cls.get_month_stats(db_session, year, month)
        
        if not stats:
            return {
                'stars': [],
                'workhorses': [],
                'puzzles': [],
                'dogs': [],
                'recommendations': []
            }
        
        # Calculate averages
        avg_quantity = sum(s.quantity_sold for s in stats) / len(stats)
        avg_margin = sum(s.avg_margin for s in stats) / len(stats)
        
        # Classify all items
        stars = []
        workhorses = []
        puzzles = []
        dogs = []
        
        for s in stats:
            classification = s.classify_item(avg_quantity, avg_margin)
            item_data = {
                'name': s.menu_item.name,
                'quantity_sold': s.quantity_sold,
                'margin': s.avg_margin * 100,
                'profit': s.calculate_gross_profit()
            }
            
            if classification == "star":
                stars.append(item_data)
            elif classification == "workhorse":
                workhorses.append(item_data)
            elif classification == "puzzle":
                puzzles.append(item_data)
            else:
                dogs.append(item_data)
        
        # Generate recommendations
        recommendations = []
        
        if stars:
            recommendations.append(
                f"Promote your {len(stars)} star items in marketing - they're your best performers!"
            )
        
        if workhorses:
            recommendations.append(
                f"{len(workhorses)} workhorses are popular but not profitable - consider raising prices or reducing costs."
            )
        
        if puzzles:
            recommendations.append(
                f"{len(puzzles)} puzzles are profitable but not popular - improve visibility or marketing."
            )
        
        if dogs:
            recommendations.append(
                f"Consider removing {len(dogs)} underperforming items to simplify your menu."
            )
        
        return {
            'stars': stars,
            'workhorses': workhorses,
            'puzzles': puzzles,
            'dogs': dogs,
            'recommendations': recommendations,
            'avg_quantity': avg_quantity,
            'avg_margin': avg_margin * 100
        }
    
    @validates('quantity_sold')
    def validate_quantity(self, key, value):
        """Ensure quantity is non-negative"""
        if value < 0:
            logger.error(
                "error.validation",
                language=LANG,
                field="quantity_sold",
                message=f"Quantity cannot be negative, got {value}"
            )
            raise ValueError("Quantity sold cannot be negative")
        return value
    
    @validates('revenue_generated', 'total_item_cost')
    def validate_money(self, key, value):
        """Ensure financial values are non-negative"""
        if value < 0:
            logger.error(
                "error.validation",
                language=LANG,
                field=key,
                message=f"{key} cannot be negative, got {value}"
            )
            raise ValueError(f"{key} cannot be negative")
        return value
    
    @validates('avg_margin')
    def validate_margin(self, key, value):
        """Ensure margin is between -1 and 1"""
        if not -1 <= value <= 1:
            logger.warning(
                "monthly_item_stats.unusual_margin",
                language=LANG,
                margin=f"{value * 100:.1f}%"
            )
        return value
    
    def __repr__(self):
        return (
            f"<MonthlyItemStats {self.month_start.strftime('%Y-%m')} - "
            f"{self.menu_item.name if self.menu_item else 'Unknown'} - "
            f"{self.quantity_sold} sold - {self.avg_margin * 100:.1f}% margin>"
        )