/**
 * Cart Context
 * 
 * Manages shopping cart state with authentication integration.
 * 
 * Key features:
 * - Persists cart to localStorage
 * - Syncs cart with user authentication state
 * - Clears cart on logout
 * - Associates cart with table ID for guests
 * - Validates items against menu availability
 * 
 * Design decisions:
 * - Cart is stored in localStorage for persistence across page reloads
 * - When user logs in, we merge guest cart with user's saved cart
 * - When user logs out, we clear the cart for security
 * - For guests, cart is tied to their current session
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { useTranslation } from 'react-i18next';
import { STORAGE_KEYS } from '../utils/constants';
import menuService from '../services/menuService';

const CartContext = createContext();

/**
 * Cart item structure:
 * {
 *   id: number,           // Menu item ID
 *   name: string,         // Item name
 *   price: number,        // Price per unit
 *   quantity: number,     // How many
 *   category: string,     // Category
 *   specifications: string // Special requests (optional)
 * }
 */

export const CartProvider = ({ children }) => {
  const { user, isAuthenticated } = useAuth();
  const { t } = useTranslation();
  const [cart, setCart] = useState([]);
  const [tableId, setTableId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  /**
   * Initialize cart from localStorage on mount
   * 
   * Why we need this:
   * - Preserves cart across page refreshes
   * - Allows guests to add items before logging in
   */
  useEffect(() => {
    const loadCart = () => {
      try {
        const savedCart = localStorage.getItem(STORAGE_KEYS.CART);
        const savedTableId = localStorage.getItem(STORAGE_KEYS.TABLE_ID);
        
        if (savedCart) {
          setCart(JSON.parse(savedCart));
        }
        
        if (savedTableId) {
          setTableId(JSON.parse(savedTableId));
        }
        
        console.log('[Cart] Cart loaded from localStorage');
      } catch (error) {
        console.error('[Cart] Error loading cart:', error);
        // If localStorage is corrupted, start fresh
        localStorage.removeItem(STORAGE_KEYS.CART);
        setCart([]);
      }
    };

    loadCart();
  }, []);

  /**
   * Save cart to localStorage whenever it changes
   * 
   * Why we need this:
   * - Automatic persistence without manual save calls
   * - Cart survives page refreshes
   */
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEYS.CART, JSON.stringify(cart));
      console.log('[Cart] Cart saved to localStorage');
    } catch (error) {
      console.error('[Cart] Error saving cart:', error);
    }
  }, [cart]);

  /**
   * Save table ID to localStorage
   */
  useEffect(() => {
    if (tableId) {
      localStorage.setItem(STORAGE_KEYS.TABLE_ID, JSON.stringify(tableId));
    }
  }, [tableId]);

  /**
   * Clear cart when user logs out
   * 
   * Security measure: Don't let next user see previous user's cart
   */
  useEffect(() => {
    if (!isAuthenticated) {
      // User logged out, clear cart for security
      clearCart();
    }
  }, [isAuthenticated]);

  /**
   * Add item to cart
   * 
   * @param {Object} item - Menu item to add
   * @param {number} quantity - How many to add (default 1)
   * @param {string} specifications - Special instructions (optional)
   * 
   * Example:
   * addItem(pizzaItem, 2, "No onions, extra cheese");
   */
  const addItem = useCallback(async (item, quantity = 1, specifications = '') => {
    setIsLoading(true);
    
    try {
      // Validate item availability with backend
      const availability = await menuService.checkAvailability(item.id, quantity);
      
      if (!availability.available) {
        throw new Error(availability.message || t('menu:item.unavailable'));
      }

      setCart(prevCart => {
        // Check if item already exists in cart
        const existingItemIndex = prevCart.findIndex(
          cartItem => cartItem.id === item.id && cartItem.specifications === specifications
        );

        if (existingItemIndex > -1) {
          // Item exists, increase quantity
          const newCart = [...prevCart];
          newCart[existingItemIndex].quantity += quantity;
          
          console.log(`[Cart] Increased quantity of ${item.name} to ${newCart[existingItemIndex].quantity}`);
          return newCart;
        } else {
          // Item doesn't exist, add new entry
          const newItem = {
            id: item.id,
            name: item.name,
            price: item.price,
            quantity: quantity,
            category: item.category,
            specifications: specifications
          };
          
          console.log(`[Cart] Added new item: ${item.name} x${quantity}`);
          return [...prevCart, newItem];
        }
      });

      return { success: true };
    } catch (error) {
      console.error('[Cart] Error adding item:', error);
      return { success: false, error: error.message };
    } finally {
      setIsLoading(false);
    }
  }, [t]);

  /**
   * Remove item from cart
   * 
   * @param {number} itemId - Item ID to remove
   * @param {string} specifications - Specifications to match (for items with special requests)
   */
  const removeItem = useCallback((itemId, specifications = '') => {
    setCart(prevCart => {
      const newCart = prevCart.filter(
        item => !(item.id === itemId && item.specifications === specifications)
      );
      
      console.log(`[Cart] Removed item with ID ${itemId}`);
      return newCart;
    });
  }, []);

  /**
   * Update item quantity
   * 
   * @param {number} itemId - Item ID
   * @param {number} newQuantity - New quantity (if 0, removes item)
   * @param {string} specifications - Specifications to match
   */
  const updateQuantity = useCallback((itemId, newQuantity, specifications = '') => {
    if (newQuantity <= 0) {
      removeItem(itemId, specifications);
      return;
    }

    setCart(prevCart => {
      return prevCart.map(item => {
        if (item.id === itemId && item.specifications === specifications) {
          console.log(`[Cart] Updated ${item.name} quantity to ${newQuantity}`);
          return { ...item, quantity: newQuantity };
        }
        return item;
      });
    });
  }, [removeItem]);

  /**
   * Clear entire cart
   */
  const clearCart = useCallback(() => {
    setCart([]);
    setTableId(null);
    localStorage.removeItem(STORAGE_KEYS.CART);
    localStorage.removeItem(STORAGE_KEYS.TABLE_ID);
    console.log('[Cart] Cart cleared');
  }, []);

  /**
   * Calculate cart totals
   * 
   * @returns {Object} Cart totals and item count
   */
  const getCartTotals = useCallback(() => {
    const subtotal = cart.reduce((total, item) => {
      return total + (item.price * item.quantity);
    }, 0);

    const itemCount = cart.reduce((total, item) => {
      return total + item.quantity;
    }, 0);

    // You can add tax, discounts, etc. here
    const tax = subtotal * 0.1; // 10% tax example
    const total = subtotal + tax;

    return {
      subtotal: subtotal.toFixed(2),
      tax: tax.toFixed(2),
      total: total.toFixed(2),
      itemCount
    };
  }, [cart]);

  /**
   * Check if an item is in cart
   * 
   * @param {number} itemId - Item ID to check
   * @returns {boolean}
   */
  const isInCart = useCallback((itemId) => {
    return cart.some(item => item.id === itemId);
  }, [cart]);

  /**
   * Get quantity of specific item in cart
   * 
   * @param {number} itemId - Item ID
   * @param {string} specifications - Specifications to match
   * @returns {number} Quantity in cart (0 if not found)
   */
  const getItemQuantity = useCallback((itemId, specifications = '') => {
    const item = cart.find(
      item => item.id === itemId && item.specifications === specifications
    );
    return item ? item.quantity : 0;
  }, [cart]);

  /**
   * Set table ID for the order
   * 
   * This is crucial for QR code scanning:
   * When guest scans QR, we extract table ID and store it
   * 
   * @param {number} id - Table ID
   */
  const setOrderTable = useCallback((id) => {
    setTableId(id);
    console.log(`[Cart] Table set to: ${id}`);
  }, []);

  /**
   * Validate cart before checkout
   * 
   * Checks:
   * - Cart is not empty
   * - All items are still available
   * - Quantities are valid
   * 
   * @returns {Promise<Object>} Validation result
   */
  const validateCart = useCallback(async () => {
    if (cart.length === 0) {
      return {
        valid: false,
        errors: [t('menu:cart.empty')]
      };
    }

    const errors = [];
    setIsLoading(true);

    try {
      // Check each item's availability
      for (const item of cart) {
        const availability = await menuService.checkAvailability(item.id, item.quantity);
        
        if (!availability.available) {
          errors.push(`${item.name}: ${availability.message}`);
        }
      }

      return {
        valid: errors.length === 0,
        errors
      };
    } catch (error) {
      console.error('[Cart] Error validating cart:', error);
      return {
        valid: false,
        errors: [t('common:error')]
      };
    } finally {
      setIsLoading(false);
    }
  }, [cart, t]);

  const value = {
    // State
    cart,
    tableId,
    isLoading,
    
    // Actions
    addItem,
    removeItem,
    updateQuantity,
    clearCart,
    setOrderTable,
    
    // Queries
    getCartTotals,
    isInCart,
    getItemQuantity,
    validateCart,
    
    // Computed
    isEmpty: cart.length === 0
  };

  return (
    <CartContext.Provider value={value}>
      {children}
    </CartContext.Provider>
  );
};

/**
 * Custom hook to use cart context
 */
export const useCart = () => {
  const context = useContext(CartContext);
  
  if (!context) {
    throw new Error('useCart must be used within CartProvider');
  }
  
  return context;
};