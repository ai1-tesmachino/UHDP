export const physicalInspectionAreas = [
    {
        id: "top-cover",
        title: "Top Cover",
        bodyIdentifier: "Body A",
        imageLabel: "Top cover",
        guidance: null,
        inspectionPoints: [
            "Scratches, dents or cracks.",
            "Paint or coating damage.",
            "Missing or damaged parts.",
            "Other visible defects.",
        ],
    },
    {
        id: "display-bezel",
        title: "Display Bezel",
        bodyIdentifier: "Body B",
        imageLabel: "Display bezel",
        guidance: "Inspect physical condition only; do not test pixels or screen functionality here.",
        inspectionPoints: [
            "Cracks or scratches.",
            "Missing bezel parts.",
            "Loose or damaged edges.",
            "Other visible physical damage.",
        ],
    },
    {
        id: "touchpad-area",
        title: "Touchpad Area",
        bodyIdentifier: "Body C",
        imageLabel: "Touchpad area",
        guidance: "Inspect physical condition only; pointer, click and gesture checks belong to a later stage.",
        inspectionPoints: [
            "Scratches or surface wear.",
            "Cracks.",
            "Missing or damaged parts.",
            "Other visible physical damage.",
        ],
    },
    {
        id: "bottom-cover",
        title: "Bottom Cover",
        bodyIdentifier: "Body D",
        imageLabel: "Bottom cover",
        guidance: null,
        inspectionPoints: [
            "Scratches, dents or cracks.",
            "Missing screws or covers.",
            "Damaged rubber feet.",
            "Loose panels, deformation or other visible defects.",
        ],
    },
    {
        id: "keyboard-area",
        title: "Keyboard Area",
        bodyIdentifier: null,
        imageLabel: "Keyboard area",
        guidance: "Inspect physical condition only; do not perform key-response testing here.",
        inspectionPoints: [
            "Missing keys or broken keycaps.",
            "Damaged keyboard surface.",
            "Visible liquid or corrosion marks.",
            "Other physical damage.",
        ],
    },
    {
        id: "ports-connectors",
        title: "Ports and Connectors",
        bodyIdentifier: null,
        imageLabel: "Ports and connectors",
        guidance: "Record physical condition only; do not perform connectivity testing here.",
        inspectionPoints: [
            "VGA, HDMI or DisplayPort connectors.",
            "USB and USB Type-C ports.",
            "Audio jack and other visible connectors.",
            "Bent connectors, broken housings or missing covers.",
        ],
    },
    {
        id: "sd-card-slot",
        title: "SD Card Slot / Cover",
        bodyIdentifier: null,
        imageLabel: "SD card slot",
        guidance: "Inspect where fitted. Select Not applicable if the device has no SD card slot or cover.",
        inspectionPoints: [
            "Missing or broken cover.",
            "Physical damage.",
            "Visible obstruction.",
        ],
    },
    {
        id: "hinges-external-body",
        title: "Hinges and External Body",
        bodyIdentifier: null,
        imageLabel: "Hinges and external body",
        guidance: "Record each defect in its most relevant inspection area to avoid duplicate entries.",
        inspectionPoints: [
            "Hinge damage or looseness.",
            "Cracks around hinge mounts.",
            "Chassis separation or body deformation.",
            "Other visible structural damage.",
        ],
    },
] as const;

export type PhysicalInspectionAreaId = (typeof physicalInspectionAreas)[number]["id"];
export type PhysicalCondition =
    | "Good"
    | "Minor scratches / wear"
    | "Damaged"
    | "Broken"
    | "Missing parts"
    | "Not applicable";
export type PhysicalAssessmentStatus = "not_assessed" | "assessed";

export interface PhysicalAreaAssessment {
    status: PhysicalAssessmentStatus;
    condition: PhysicalCondition | null;
    defects: string[];
    remarks: string;
    photoRefs: string[];
    isDemoSample: boolean;
}

export type PhysicalAssessmentRecord = Record<PhysicalInspectionAreaId, PhysicalAreaAssessment>;

export function isPhysicalAssessmentComplete(assessments: PhysicalAssessmentRecord): boolean {
    return Object.values(assessments).every(
        (assessment) => assessment.status === "assessed" && assessment.condition !== null,
    );
}

export const physicalConditionOptions: PhysicalCondition[] = [
    "Good",
    "Minor scratches / wear",
    "Damaged",
    "Broken",
    "Missing parts",
    "Not applicable",
];

function createAssessment(
    overrides: Partial<PhysicalAreaAssessment> = {},
): PhysicalAreaAssessment {
    return {
        status: "not_assessed",
        condition: null,
        defects: [],
        remarks: "",
        photoRefs: [],
        isDemoSample: false,
        ...overrides,
    };
}

export function createInitialPhysicalAssessments(): PhysicalAssessmentRecord {
    return {
        "top-cover": createAssessment({
            status: "assessed",
            condition: "Minor scratches / wear",
            defects: ["Light scratches on the top cover"],
            remarks: "Light surface wear is visible in this demo sample.",
            photoRefs: ["Top cover · demo photo placeholder"],
            isDemoSample: true,
        }),
        "display-bezel": createAssessment({
            status: "assessed",
            condition: "Good",
            remarks: "No visible cracks or loose edges in this demo sample.",
            isDemoSample: true,
        }),
        "touchpad-area": createAssessment(),
        "bottom-cover": createAssessment(),
        "keyboard-area": createAssessment(),
        "ports-connectors": createAssessment(),
        "sd-card-slot": createAssessment(),
        "hinges-external-body": createAssessment(),
    };
}
