import type { DisplayDiagnostic, DisplayTestOutcome } from "@/api/execution";

export interface DisplayTestDefinition {
    id: string;
    name: string;
    purpose: string;
    instructions: string;
    kind: "information" | "visual" | "assessment";
    patterns: string[];
}

export const DISPLAY_TEST_CATALOG: DisplayTestDefinition[] = [
    {
        id: "display_information",
        name: "Display Information",
        purpose: "Identify the active display mode and any available connection metadata.",
        instructions: "Review the collected information. Unavailable EDID or refresh data is not evidence of a defective panel.",
        kind: "information",
        patterns: ["Display metadata"],
    },
    {
        id: "dead_pixel",
        name: "Dead Pixel Test",
        purpose: "Inspect solid colours for dead pixels, stuck pixels, or isolated points.",
        instructions: "Look across the entire panel for pixels that stay dark or remain a different colour. The browser cannot detect or locate pixel defects automatically.",
        kind: "visual",
        patterns: ["Black", "White", "Red", "Green", "Blue"],
    },
    {
        id: "rgb_colour",
        name: "RGB Colour Test",
        purpose: "Inspect primary and secondary colour rendering.",
        instructions: "Check each full-screen colour for obvious colour shifts, missing channels, or abnormal rendering.",
        kind: "visual",
        patterns: ["Red", "Green", "Blue", "Cyan", "Magenta", "Yellow", "White", "Black"],
    },
    {
        id: "colour_uniformity",
        name: "Colour Uniformity",
        purpose: "Look for uneven brightness, colour patches, spots, or backlight bleed.",
        instructions: "Inspect the whole panel on each flat colour. This is a visual check, not a calibrated uniformity measurement.",
        kind: "visual",
        patterns: ["White", "Grey", "Black", "Red", "Green", "Blue"],
    },
    {
        id: "gradient",
        name: "Gradient Test",
        purpose: "Inspect smooth transitions for visible banding or missing tonal steps.",
        instructions: "Check horizontal and vertical transitions for abrupt bands or colour discontinuities.",
        kind: "visual",
        patterns: ["Black to white", "White to black", "Red gradient", "Green gradient", "Blue gradient", "Grayscale gradient"],
    },
    {
        id: "contrast",
        name: "Contrast Test",
        purpose: "Inspect shadow detail, highlight detail, and grayscale steps.",
        instructions: "Check that adjacent dark and light steps remain distinguishable. This is not a calibrated contrast-ratio measurement.",
        kind: "visual",
        patterns: ["Black-level steps", "Dark greys", "Light greys", "White-level steps"],
    },
    {
        id: "geometry",
        name: "Geometry Test",
        purpose: "Inspect line alignment, geometry, scaling, and missing display regions.",
        instructions: "Check the edges and center for straight lines, even spacing, complete borders, and image distortion.",
        kind: "visual",
        patterns: ["Line grid", "Checkerboard", "Concentric circles", "Crosshair", "Border alignment"],
    },
    {
        id: "visual_artifacts",
        name: "Visual Artefact Test",
        purpose: "Inspect moving patterns for visible flicker, tearing, or distortion.",
        instructions: "Watch the moving pattern. Browser animation does not measure panel response time or verify refresh-rate compliance.",
        kind: "visual",
        patterns: ["Moving square", "Moving horizontal line", "Moving vertical line", "Moving checkerboard", "Colour transitions"],
    },
    {
        id: "final_assessment",
        name: "Final Technician Assessment",
        purpose: "Review the recorded results before completing this display diagnostic.",
        instructions: "Confirm every required check has a result. Defects and inconclusive checks remain visible in the report.",
        kind: "assessment",
        patterns: [],
    },
];

export const REQUIRED_DISPLAY_TESTS = DISPLAY_TEST_CATALOG.filter(
    (test) => test.kind !== "assessment",
);

export const DEFECT_TYPES = [
    { value: "DEAD_PIXEL", label: "Dead pixel" },
    { value: "STUCK_PIXEL", label: "Stuck pixel" },
    { value: "COLOR_ABNORMALITY", label: "Colour abnormality" },
    { value: "UNEVEN_BRIGHTNESS", label: "Uneven brightness" },
    { value: "BACKLIGHT_BLEED", label: "Backlight bleed" },
    { value: "FLICKERING", label: "Flickering" },
    { value: "DISPLAY_LINES", label: "Display lines" },
    { value: "DISTORTION", label: "Distortion" },
    { value: "OTHER", label: "Other" },
] as const;

export function getTestOutcome(
    diagnostic: DisplayDiagnostic | null,
    testId: string,
): DisplayTestOutcome | "in_progress" | "not_started" {
    const test = diagnostic?.tests?.[testId];
    if (!test) return "not_started";
    if (test.status === "in_progress") return "in_progress";
    if (test.latest_result) return test.latest_result.status;
    return "not_started";
}
