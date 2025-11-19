/**
 * Constants synchronized with backend Pydantic models
 * Source: backend/src/database/models/user.py
 * 
 * IMPORTANT: Keep these in sync with backend enums!
 * Any changes to backend UserRole or GenderEnum should be reflected here.
 */

/**
 * User roles in the restaurant system
 * Backend source: backend/src/database/models/user.py:UserRole (StrEnum)
 */
export const USER_ROLES = {
    ADMIN: 'admin',
    KITCHEN: 'kitchen',
    CLIENT: 'client',
    WAITER: 'waiter',
};

/**
 * User gender options
 * Backend source: backend/src/database/models/user.py:GenderEnum (StrEnum)
 */
export const GENDER = {
    MALE: 'male',
    FEMALE: 'female',
    OTHER: 'other',
};

/**
 * Order status values
 * Backend source: backend/src/database/models/order.py:OrderStatus (StrEnum)
 * TODO: Verify these match the backend
 */
export const ORDER_STATUS = {
    PENDING: 'pending',
    PREPARING: 'preparing',
    READY: 'ready',
    DELIVERED: 'delivered',
    COMPLETED: 'completed',
    CANCELLED: 'cancelled',
};

/**
 * Helper functions for role checking
 */
export const isAdmin = (role) => role?.toLowerCase() === USER_ROLES.ADMIN;
export const isStaff = (role) => {
    const r = role?.toLowerCase();
    return r === USER_ROLES.ADMIN || r === USER_ROLES.WAITER || r === USER_ROLES.KITCHEN;
};
export const isClient = (role) => role?.toLowerCase() === USER_ROLES.CLIENT;

export default {
    USER_ROLES,
    GENDER,
    ORDER_STATUS,
    isAdmin,
    isStaff,
    isClient,
};
