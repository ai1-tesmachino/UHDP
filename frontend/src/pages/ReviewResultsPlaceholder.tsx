import { Link } from "react-router-dom";
import { ClipboardCheck } from "lucide-react";

export default function ReviewResultsPlaceholder() {
    return (
        <main className="hardware-diagnostics page-flow" aria-labelledby="review-results-placeholder-title">
            <header className="device-id-page-header">
                <div>
                    <span className="eyebrow">DEVICE INSPECTION</span>
                    <h1 className="page-title" id="review-results-placeholder-title">Review Results</h1>
                    <p className="page-description">Phase 5 placeholder. Review Results is not implemented in this phase.</p>
                </div>
                <span className="device-id-demo-label">DEMO DATA</span>
            </header>
            <section className="hardware-diagnostics-placeholder">
                <ClipboardCheck size={22} aria-hidden="true" />
                <p>Review Results will be available in a later phase.</p>
                <Link className="button button-secondary" to="/technician-checks">BACK TO TECHNICIAN CHECKS</Link>
            </section>
        </main>
    );
}
