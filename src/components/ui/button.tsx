import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
const variants = cva('inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 disabled:pointer-events-none disabled:opacity-50', {variants:{variant:{default:'bg-[#5c2483] text-white hover:bg-[#71369a]',ghost:'hover:bg-black/5',outline:'border border-black/10 bg-white hover:bg-slate-50'},size:{default:'h-10 px-4 rounded-xl',icon:'h-10 w-10 rounded-xl'}},defaultVariants:{variant:'default',size:'default'}});
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof variants> { asChild?: boolean }
export const Button = React.forwardRef<HTMLButtonElement,ButtonProps>(({className,variant,size,asChild=false,...props},ref)=>{ const Comp=asChild?Slot:'button';return <Comp ref={ref} className={twMerge(clsx(variants({variant,size}),className))} {...props}/>});
Button.displayName='Button';
