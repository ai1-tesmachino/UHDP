import { ReactNode } from "react";
import Navbar from "./Navbar";
import Sidebar from "./Sidebar";
import WorkflowSteps from "./WorkflowSteps";

interface Props {
    children: ReactNode;
}

export default function Layout({ children }: Props) {
    return (
        <div className="app-shell">
            <Sidebar />

            <div className="main-shell">
                <Navbar />

                <WorkflowSteps />

                <main className="content">
                    {children}
                </main>
            </div>
        </div>
    );
}