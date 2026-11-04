import { Link } from "react-router-dom";

const FIELD_GROUPS = [
    {
        title: "Station setup",
        description: "Needed to identify the technician and workstation on each QC record.",
        fields: [
            { name: "Technician", required: true },
            { name: "Station ID", required: true },
        ],
    },
    {
        title: "Device intake",
        description: "Only the detected system device is required to begin an intake.",
        fields: [
            { name: "System device detected", required: true },
            { name: "Asset tag / serial / barcode", required: false },
            { name: "Technician", required: false },
            { name: "Customer / work-order reference", required: false },
            { name: "Technician workflow", required: false },
        ],
    },
    {
        title: "Cosmetic inspection",
        description: "Each item must be assessed and confirmed. Damage details are required only when condition is Damaged or Missing.",
        fields: [
            { name: "Condition", required: true },
            { name: "Damage severity", required: true },
            { name: "Damage description (Damaged / Missing)", required: true },
            { name: "Damage location (Damaged / Missing)", required: true },
            { name: "Technician confirmation", required: true },
            { name: "Notes", required: false },
            { name: "Photo evidence", required: false },
            { name: "Custom inspection item", required: false },
        ],
    },
    {
        title: "Final disposition",
        description: "Required before the session can be finalized.",
        fields: [
            { name: "Final disposition", required: true },
            { name: "QA approver", required: true },
            { name: "Approval confirmation", required: true },
            { name: "Reason for deviating from recommendation", required: true },
        ],
    },
];

export default function FieldRequirements() {
    return (
        <div className="page-flow field-requirements-page">
            <header className="page-header">
                <div>
                    <span className="eyebrow">SETTINGS · QC FORMS</span>
                    <h1 className="page-title">QC Field Requirements</h1>
                    <p className="page-description">
                        Review which information is required to complete a QC record and which can be skipped.
                    </p>
                </div>
                <Link className="button button-secondary" to="/setup">Station setup</Link>
            </header>

            <section className="field-requirements-legend" aria-label="Field requirement legend">
                <span><b className="required-field-mark" aria-hidden="true">*</b> Mandatory field</span>
                <span><b className="optional-field-mark">Optional</b> Can be left blank</span>
            </section>

            <div className="field-requirements-groups">
                {FIELD_GROUPS.map((group) => (
                    <section className="field-requirements-card" key={group.title}>
                        <div>
                            <h2>{group.title}</h2>
                            <p>{group.description}</p>
                        </div>
                        <ul>
                            {group.fields.map((field) => (
                                <li key={field.name}>
                                    <span>{field.name}</span>
                                    {field.required
                                        ? <b className="required-field-mark" aria-label="Mandatory">*</b>
                                        : <b className="optional-field-mark">Optional</b>}
                                </li>
                            ))}
                        </ul>
                    </section>
                ))}
            </div>
        </div>
    );
}
