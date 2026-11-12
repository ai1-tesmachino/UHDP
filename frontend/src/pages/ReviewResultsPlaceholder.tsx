import { Link } from "react-router-dom";
import { ClipboardCheck } from "lucide-react";
import { PageHeader } from "../components/shared/PageHeader";

export default function ReviewResultsPlaceholder() {
    return (
        <main className="hardware-diagnostics page-flow" aria-labelledby="review-results-placeholder-title">
            <PageHeader
                title="Review Results"
                titleId="review-results-placeholder-title"
                description="Phase 5 placeholder. Review Results is not implemented in this phase."
                eyebrow="DEVICE INSPECTION"
                actions={<span className="device-id-demo-label">DEMO DATA</span>}
            />
            <section className="hardware-diagnostics-placeholder">
                <ClipboardCheck size={22} aria-hidden="true" />
                <p>Review Results will be available in a later phase.</p>
                <Link className="button button-secondary" to="/technician-checks">BACK TO TECHNICIAN CHECKS</Link>
            </section>
        </main>
    );
}
