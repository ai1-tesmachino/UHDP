import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

interface PageContainerProps extends HTMLAttributes<HTMLElement> {
    children: ReactNode;
}

export function PageContainer({ children, className, ...props }: PageContainerProps) {
    return <main className={cn("page-container", className)} {...props}>{children}</main>;
}
