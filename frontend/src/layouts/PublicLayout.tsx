import { useState } from "react";
import { ArrowRight, Menu, X } from "lucide-react";
import { Link, NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

const links = [
    { label: "Platform", to: "/features" },
    { label: "How it works", to: "/how-it-works" },
    { label: "About", to: "/about" },
    { label: "Contact", to: "/contact" },
];

export function PublicLayout() {
    const [menuOpen, setMenuOpen] = useState(false);
    const { isAuthenticated } = useAuth();

    return (
        <div className="public-shell">
            <header className="site-header">
                <div className="container nav-container">
                    <Link to="/" className="brand-link" aria-label="RollNexa home" onClick={() => setMenuOpen(false)}>
                        <img src="/static/images/rollnexa-logo.svg" alt="RollNexa" />
                    </Link>
                    <button
                        className="mobile-menu-button"
                        type="button"
                        aria-label={menuOpen ? "Close navigation" : "Open navigation"}
                        aria-expanded={menuOpen}
                        onClick={() => setMenuOpen((open) => !open)}
                    >
                        {menuOpen ? <X size={22} /> : <Menu size={22} />}
                    </button>
                    <nav className={`public-nav ${menuOpen ? "is-open" : ""}`} aria-label="Main navigation">
                        {links.map((link) => (
                            <NavLink key={link.to} to={link.to} onClick={() => setMenuOpen(false)}>
                                {link.label}
                            </NavLink>
                        ))}
                        <Link
                            className="button button-primary nav-cta"
                            to={isAuthenticated ? "/app" : "/login"}
                            onClick={() => setMenuOpen(false)}
                        >
                            {isAuthenticated ? "Open dashboard" : "Sign in"}
                            <ArrowRight size={16} />
                        </Link>
                    </nav>
                </div>
            </header>
            <main>
                <Outlet />
            </main>
            <footer className="site-footer">
                <div className="container footer-grid">
                    <div className="footer-brand-block">
                        <Link to="/" className="footer-brand">
                            <img src="/static/images/rollnexa-mark.svg" alt="" />
                            <span>RollNexa</span>
                        </Link>
                        <p>Academic management and attendance, connected in one platform.</p>
                    </div>
                    <div className="footer-links">
                        <span className="footer-heading">Explore</span>
                        <Link to="/features">Platform</Link>
                        <Link to="/how-it-works">How it works</Link>
                        <Link to="/about">About RollNexa</Link>
                    </div>
                    <div className="footer-links">
                        <span className="footer-heading">Information</span>
                        <Link to="/contact">Contact</Link>
                        <Link to="/privacy">Privacy notice</Link>
                        <Link to="/terms">Terms of use</Link>
                    </div>
                    <div className="footer-note-block">
                        <span className="footer-heading">RollNexa</span>
                        <p>Your institution provides your account. Contact them if you need access.</p>
                        <span className="footer-tagline">Attendance, connected.</span>
                    </div>
                </div>
                <div className="container footer-bottom">
                    <span>© {new Date().getFullYear()} RollNexa</span>
                    <span>Academic management · Attendance</span>
                </div>
            </footer>
        </div>
    );
}
