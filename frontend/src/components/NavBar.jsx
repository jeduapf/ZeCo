import "../css/NavBar.css";
import React, { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function NavBar({ translations }) {
  const defaultTranslations = {
    about_title: 'Home',
    menu_title: 'Menu',
    checkout_title: 'Checkout'
  }
  translations = translations || defaultTranslations
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const currentTitle =
    location.pathname === "/"
      ? translations.about_title
      : location.pathname === "/menu"
        ? translations.menu_title
        : location.pathname === "/checkout"
          ? translations.checkout_title
          : location.pathname === "/login"
            ? translations.login_title
            : location.pathname === "/admin"
              ? translations.admin_title
              : location.pathname.replace("/", "");

  const handleLogout = () => {
    logout();
    navigate("/");
    setOpen(false);
  };

  return (
    <header className="navbar">
      {/* Hamburger ALWAYS visible */}
      <button className={`hamburger ${open ? "open" : ""}`} onClick={() => setOpen(!open)}>
        <span></span>
        <span></span>
        <span></span>
      </button>

      {/* Center Title */}
      <h1 className="navbar-title">{currentTitle}</h1>

      {/* Right side actions - both user and cart */}
      <div className="navbar-actions">
        {user && (
          <div className="user-info" onClick={handleLogout} title={`Logout ${user.username}`}>
            <span className="user-icon">👤</span>
            <span className="user-name">{user.username}</span>
          </div>
        )}
        <div className="cart-icon">
          <Link to="/checkout" title="Go to checkout">
            🛒
          </Link>
        </div>
      </div>

      {/* Slide-down Menu */}
      <nav className={`mobile-menu ${open ? "open" : ""}`}>
        <Link to="/" onClick={() => setOpen(false)}>
          {translations.about_title}
        </Link>
        <Link to="/menu" onClick={() => setOpen(false)}>
          {translations.menu_title}
        </Link>
        <Link to="/checkout" onClick={() => setOpen(false)}>
          {translations.checkout_title}
        </Link>
        <Link to="/login" onClick={() => setOpen(false)}>
          {translations.login_title}
        </Link>
        <Link to="/admin" onClick={() => setOpen(false)}>
          {translations.admin_title}
        </Link>
      </nav>
    </header>
  );
}


export default NavBar;