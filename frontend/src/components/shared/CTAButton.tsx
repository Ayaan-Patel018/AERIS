import React from 'react';
import { useNavigate } from 'react-router-dom';

interface CTAButtonProps {
  onClick?: () => void;
  to?: string;
  variant?: 'primary' | 'ghost';
  children: React.ReactNode;
  className?: string;
}

export const CTAButton: React.FC<CTAButtonProps> = ({ 
  onClick, 
  to, 
  variant = 'primary', 
  children, 
  className = '' 
}) => {
  const navigate = useNavigate();

  const handleClick = (e: React.MouseEvent) => {
    if (to) {
      e.preventDefault();
      // Handle the page transition overlay manually if needed, or just navigate
      const pt = document.getElementById('pageTransition');
      if (pt) pt.classList.add('active');
      setTimeout(() => {
        navigate(to);
      }, 320);
    }
    if (onClick) onClick();
  };

  const baseClass = 'btn';
  const variantClass = variant === 'primary' ? 'btn-pri' : 'btn-ghost';

  return (
    <button onClick={handleClick} className={`${baseClass} ${variantClass} ${className}`}>
      {children}
    </button>
  );
};
