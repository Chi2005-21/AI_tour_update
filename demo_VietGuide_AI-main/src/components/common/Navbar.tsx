import { Link, useLocation } from 'react-router-dom';
import { MapPin, MessageCircle, Compass, Route, Settings, Sparkles } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';

const Navbar = () => {
  const { language, setLanguage, t } = useLanguage();
  const location = useLocation();

  const navItems = [
    { path: '/', label: t.nav.home, icon: MapPin },
    { path: '/chat', label: t.nav.chat, icon: MessageCircle },
    { path: '/explore', label: t.nav.explore, icon: Compass },
    { path: '/route-planner', label: t.nav.routePlanner, icon: Route },
    { path: '/admin', label: t.nav.admin, icon: Settings },
  ];

  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className="fixed top-0 left-0 right-0 z-50">
      {/* Glass background with subtle gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-surface/95 via-surface/90 to-surface/85 backdrop-blur-xl border-b border-border/50" />

      <div className="relative max-w-container mx-auto px-4 sm:px-6 lg:px-12">
        <div className="flex items-center justify-between h-18 lg:h-20">
          {/* Logo Section */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="relative">
              {/* Glow effect on hover */}
              <div className="absolute inset-0 bg-primary/20 rounded-2xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              <div className="relative w-11 h-11 rounded-2xl bg-gradient-to-br from-primary via-primary-dark to-primary-900 flex items-center justify-center shadow-premium group-hover:shadow-glow transition-all duration-300">
                <Sparkles className="w-5 h-5 text-white" />
                {/* Badge */}
                <div className="absolute -top-1 -right-1 w-4 h-4 bg-accent rounded-full flex items-center justify-center shadow-sm">
                  <span className="text-[8px] font-bold text-white">AI</span>
                </div>
              </div>
            </div>
            <div className="flex flex-col">
              <span className="text-xl font-bold text-text-main tracking-tight group-hover:text-primary transition-colors">
                VietGuide<span className="text-primary"> AI</span>
              </span>
              <span className="text-[10px] text-text-muted -mt-1 hidden sm:block">
                Hướng dẫn viên du lịch ảo
              </span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden lg:flex items-center gap-1">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`relative flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
                  isActive(item.path)
                    ? 'text-primary'
                    : 'text-text-muted hover:text-text-main'
                }`}
              >
                {/* Active indicator background */}
                {isActive(item.path) && (
                  <div className="absolute inset-0 bg-primary-light rounded-xl animate-fade-in" />
                )}
                <item.icon className={`w-4 h-4 relative z-10 ${isActive(item.path) ? 'text-primary' : ''}`} />
                <span className="relative z-10">{item.label}</span>
                {/* Active dot */}
                {isActive(item.path) && (
                  <div className="absolute bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 bg-primary rounded-full" />
                )}
              </Link>
            ))}
          </div>

          {/* Right Section */}
          <div className="flex items-center gap-3">
            {/* Language Toggle - Premium Design */}
            <div className="flex items-center bg-soft-surface rounded-2xl p-1 border border-border-light shadow-soft">
              <button
                onClick={() => setLanguage('vi')}
                className={`relative px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
                  language === 'vi'
                    ? 'text-white'
                    : 'text-text-muted hover:text-text-main'
                }`}
              >
                {language === 'vi' && (
                  <div className="absolute inset-0 bg-gradient-to-br from-primary to-primary-dark rounded-xl shadow-soft animate-fade-in" />
                )}
                <span className="relative z-10 font-semibold">VI</span>
              </button>
              <button
                onClick={() => setLanguage('en')}
                className={`relative px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
                  language === 'en'
                    ? 'text-white'
                    : 'text-text-muted hover:text-text-main'
                }`}
              >
                {language === 'en' && (
                  <div className="absolute inset-0 bg-gradient-to-br from-primary to-primary-dark rounded-xl shadow-soft animate-fade-in" />
                )}
                <span className="relative z-10 font-semibold">EN</span>
              </button>
            </div>

            {/* Premium CTA Button */}
            <Link
              to="/chat"
              className="hidden md:flex items-center gap-2.5 px-6 py-3 bg-gradient-to-r from-primary via-primary to-primary-dark hover:from-primary-dark hover:to-primary-900 text-white rounded-2xl font-semibold shadow-premium hover:shadow-glow transition-all duration-300 group"
            >
              <div className="relative">
                <MessageCircle className="w-5 h-5" />
                <div className="absolute inset-0 bg-white/20 rounded-full animate-pulse-soft" />
              </div>
              <span>{t.nav.askAI}</span>
              {/* Shine effect */}
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
            </Link>

            {/* Mobile menu button */}
            <button className="lg:hidden p-2 rounded-xl hover:bg-soft-surface transition-colors">
              <svg className="w-6 h-6 text-text-main" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        <div className="lg:hidden flex items-center gap-1 pb-3 overflow-x-auto scrollbar-hide -mx-4 px-4">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap transition-all ${
                isActive(item.path)
                  ? 'bg-primary-light text-primary'
                  : 'text-text-muted hover:text-text-main hover:bg-soft-surface'
              }`}
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
