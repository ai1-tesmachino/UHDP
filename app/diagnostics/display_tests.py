DISPLAY_TESTS = (
    {
        "id": "display_information",
        "name": "Display information",
        "purpose": "Identify available display mode and connection metadata.",
        "kind": "information",
    },
    {
        "id": "dead_pixel",
        "name": "Dead pixel test",
        "purpose": "Inspect solid colour patterns for dead or stuck pixels.",
        "kind": "visual",
    },
    {
        "id": "rgb_colour",
        "name": "RGB colour test",
        "purpose": "Inspect primary and secondary colour rendering.",
        "kind": "visual",
    },
    {
        "id": "colour_uniformity",
        "name": "Colour uniformity",
        "purpose": "Inspect full-screen colours for unevenness, spots, or bleed.",
        "kind": "visual",
    },
    {
        "id": "gradient",
        "name": "Gradient test",
        "purpose": "Inspect colour and grayscale transitions for visible banding.",
        "kind": "visual",
    },
    {
        "id": "contrast",
        "name": "Contrast test",
        "purpose": "Inspect black-level, shadow, highlight, and grayscale steps.",
        "kind": "visual",
    },
    {
        "id": "geometry",
        "name": "Geometry test",
        "purpose": "Inspect alignment, lines, grids, and scaling.",
        "kind": "visual",
    },
    {
        "id": "visual_artifacts",
        "name": "Visual artefact test",
        "purpose": "Inspect moving patterns for visible flicker, tearing, or distortion.",
        "kind": "visual",
    },
)

DISPLAY_TEST_IDS = frozenset(test["id"] for test in DISPLAY_TESTS)
DISPLAY_ASSESSMENT_ID = "final_assessment"
DISPLAY_NAVIGATION_IDS = DISPLAY_TEST_IDS | {DISPLAY_ASSESSMENT_ID}

DISPLAY_DEFECT_TYPES = frozenset(
    {
        "DEAD_PIXEL",
        "STUCK_PIXEL",
        "COLOR_ABNORMALITY",
        "UNEVEN_BRIGHTNESS",
        "BACKLIGHT_BLEED",
        "FLICKERING",
        "DISPLAY_LINES",
        "DISTORTION",
        "OTHER",
    }
)
