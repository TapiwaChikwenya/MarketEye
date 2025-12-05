import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(value: number | string, currency: string = 'USD'): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;

  if (isNaN(num)) return '$0.00';

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}

export function formatPercent(value: number | string): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;

  if (isNaN(num)) return '0.00%';

  const sign = num >= 0 ? '+' : '';
  return `${sign}${num.toFixed(2)}%`;
}

export function formatNumber(value: number | string): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;

  if (isNaN(num)) return '0';

  if (num >= 1e9) {
    return `${(num / 1e9).toFixed(2)}B`;
  } else if (num >= 1e6) {
    return `${(num / 1e6).toFixed(2)}M`;
  } else if (num >= 1e3) {
    return `${(num / 1e3).toFixed(2)}K`;
  }

  return num.toFixed(2);
}
