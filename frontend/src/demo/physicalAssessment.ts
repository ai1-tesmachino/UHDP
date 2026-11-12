export type PhysicalCondition =
    | "Good"
    | "Minor scratches"
    | "Scratches"
    | "Scratched"
    | "Dent"
    | "Crack"
    | "Cracked"
    | "Broken"
    | "Missing"
    | "Damaged"
    | "Loose"
    | "Stiff"
    | "Worn keycaps"
    | "Missing keycaps"
    | "Physically damaged"
    | "Liquid damage visible"
    | "Surface scratches"
    | "Surface wear"
    | "Worn"
    | "Stuck"
    | "Pressure marks"
    | "Dirty"
    | "Bent connector"
    | "Broken housing"
    | "Corrosion visible"
    | "Obstructed"
    | "Not applicable"
    | "Peeling"
    | "Unable to verify";

export interface PhysicalInspectionArea {
    id: string;
    group: "External Body" | "Input Devices" | "Display & Camera" | "Other Components";
    title: string;
    guidance: string;
    options: readonly PhysicalCondition[];
}

export const physicalInspectionAreas = [
    {
        id: "top-cover",
        group: "External Body",
        title: "Top Cover",
        guidance: "Check the cover surface and edges for cosmetic or structural damage.",
        options: ["Good", "Minor scratches", "Scratches", "Dent", "Crack", "Broken", "Missing", "Damaged", "Unable to verify"],
    },
    {
        id: "bottom-cover",
        group: "External Body",
        title: "Bottom Cover",
        guidance: "Inspect for cracks, deformation, loose panels, and damage around screw points.",
        options: ["Good", "Minor scratches", "Scratches", "Dent", "Crack", "Broken", "Missing", "Damaged", "Unable to verify"],
    },
    {
        id: "front-bezel",
        group: "External Body",
        title: "Front Bezel",
        guidance: "Inspect the front edge and visible trim for cracks, chips, or missing sections.",
        options: ["Good", "Minor scratches", "Scratches", "Crack", "Broken", "Missing", "Damaged", "Unable to verify"],
    },
    {
        id: "palm-rest",
        group: "External Body",
        title: "Palm Rest",
        guidance: "Check the palm-rest surface and seams for wear, cracks, or separation.",
        options: ["Good", "Minor scratches", "Scratches", "Dent", "Crack", "Damaged", "Unable to verify"],
    },
    {
        id: "hinges",
        group: "External Body",
        title: "Hinges",
        guidance: "Check hinge covers, mounting points, and visible looseness without forcing the lid.",
        options: ["Good", "Loose", "Crack", "Broken", "Damaged", "Unable to verify"],
    },
    {
        id: "chassis-body",
        group: "External Body",
        title: "Chassis / Body Condition",
        guidance: "Inspect the overall chassis for deformation, separation, or structural damage.",
        options: ["Good", "Minor scratches", "Scratches", "Dent", "Crack", "Broken", "Damaged", "Unable to verify"],
    },
    {
        id: "screws-missing-parts",
        group: "External Body",
        title: "Screws and Missing Parts",
        guidance: "Check visible screw positions, covers, and other fitted external parts.",
        options: ["Good", "Missing", "Loose", "Broken", "Damaged", "Unable to verify"],
    },
    {
        id: "keyboard",
        group: "Input Devices",
        title: "Keyboard",
        guidance: "Check keycaps for wear, missing keys, liquid marks, and visible physical damage. Do not test key response here.",
        options: ["Good", "Worn keycaps", "Missing keycaps", "Physically damaged", "Liquid damage visible", "Unable to verify"],
    },
    {
        id: "touchpad",
        group: "Input Devices",
        title: "Touchpad",
        guidance: "Check the surface for scratches, wear, cracks, and physical damage. Functional testing is handled separately.",
        options: ["Good", "Surface scratches", "Surface wear", "Cracked", "Physically damaged", "Unable to verify"],
    },
    {
        id: "touchpad-buttons",
        group: "Input Devices",
        title: "Touchpad Buttons",
        guidance: "Check for worn, stuck, cracked, missing, or physically damaged buttons.",
        options: ["Good", "Worn", "Stuck", "Cracked", "Missing", "Physically damaged", "Unable to verify"],
    },
    {
        id: "display-panel",
        group: "Display & Camera",
        title: "Display Panel",
        guidance: "Check for cracks, scratches, pressure marks, and visible panel damage. Functional display checks are handled separately.",
        options: ["Good", "Scratched", "Pressure marks", "Cracked", "Physically damaged", "Unable to verify"],
    },
    {
        id: "display-bezel",
        group: "Display & Camera",
        title: "Display Bezel",
        guidance: "Check the bezel for cracks, loose edges, and missing trim; assess the panel separately.",
        options: ["Good", "Scratched", "Cracked", "Loose", "Broken", "Missing", "Unable to verify"],
    },
    {
        id: "camera-lens",
        group: "Display & Camera",
        title: "Camera Lens",
        guidance: "Inspect the lens for visible scratches, cracks, damage, or a missing lens cover.",
        options: ["Good", "Scratched", "Cracked", "Dirty", "Damaged", "Missing", "Unable to verify"],
    },
    {
        id: "sd-card-slot",
        group: "Other Components",
        title: "SD Card Slot / Cover",
        guidance: "Inspect the slot and cover where fitted. Use Not applicable only if this device has none.",
        options: ["Good", "Missing", "Broken", "Damaged", "Not applicable", "Unable to verify"],
    },
    {
        id: "speakers-grilles",
        group: "Other Components",
        title: "Speakers / Grilles",
        guidance: "Check grille condition and visible speaker-area damage; audio testing is separate.",
        options: ["Good", "Damaged", "Broken", "Obstructed", "Missing", "Not applicable", "Unable to verify"],
    },
    {
        id: "rubber-feet",
        group: "Other Components",
        title: "Rubber Feet",
        guidance: "Check that the feet are present, secure, and not excessively worn.",
        options: ["Good", "Worn", "Missing", "Damaged", "Unable to verify"],
    },
    {
        id: "labels-stickers",
        group: "Other Components",
        title: "Labels and Stickers",
        guidance: "Check asset, regulatory, and service labels for presence and legibility.",
        options: ["Good", "Peeling", "Damaged", "Missing", "Unable to verify"],
    },
    {
        id: "ports-connectors",
        group: "Other Components",
        title: "Ports and Connectors",
        guidance: "Check connector housings for bending, cracks, or visible corrosion. Do not infer functional status from presence.",
        options: ["Good", "Bent connector", "Broken housing", "Damaged", "Corrosion visible", "Unable to verify"],
    },
] as const satisfies readonly PhysicalInspectionArea[];

export type PhysicalInspectionAreaId = (typeof physicalInspectionAreas)[number]["id"];
export type PhysicalAssessmentStatus = "pending" | "assessed" | "skipped";

export interface PhysicalAreaAssessment {
    status: PhysicalAssessmentStatus;
    conditions: PhysicalCondition[];
    remarks: string;
    isSaved: boolean;
    ports: PhysicalPortAssessment[];
}

export interface PhysicalPortAssessment {
    id: string;
    type: string;
    conditions: PhysicalCondition[];
}

export type PhysicalAssessmentRecord = Record<PhysicalInspectionAreaId, PhysicalAreaAssessment>;

export function isPhysicalAssessmentComplete(assessments: PhysicalAssessmentRecord): boolean {
    return Object.entries(assessments).every(([areaId, assessment]) => {
        if (assessment.status === "skipped") return true;
        if (assessment.status !== "assessed") return false;
        if (areaId === "ports-connectors") {
            return assessment.ports.length > 0
                && assessment.ports.every((port) => port.conditions.length > 0);
        }
        return assessment.conditions.length > 0;
    });
}

export const physicalConditionNeedsRemarks = new Set<PhysicalCondition>([
    "Crack",
    "Cracked",
    "Broken",
    "Missing",
    "Damaged",
    "Physically damaged",
    "Liquid damage visible",
    "Stuck",
    "Stiff",
    "Loose",
    "Missing keycaps",
    "Pressure marks",
    "Bent connector",
    "Broken housing",
    "Corrosion visible",
    "Obstructed",
]);

export const physicalPortTypes = [
    "USB-A",
    "USB-C",
    "HDMI",
    "DisplayPort",
    "Ethernet (RJ-45)",
    "Audio jack",
    "Power connector",
    "VGA",
    "SD card slot",
    "Other",
] as const;

export const physicalPortConditionOptions: readonly PhysicalCondition[] = [
    "Good",
    "Bent connector",
    "Broken housing",
    "Damaged",
    "Corrosion visible",
    "Unable to verify",
];

export function createInitialPhysicalAssessments(): PhysicalAssessmentRecord {
    return physicalInspectionAreas.reduce((assessments, { id }) => {
        assessments[id] = { status: "pending", conditions: [], remarks: "", isSaved: false, ports: [] };
        return assessments;
    }, {} as PhysicalAssessmentRecord);
}
