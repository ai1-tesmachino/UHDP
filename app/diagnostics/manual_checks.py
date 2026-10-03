MANUAL_CHECKS = [
    {
        "id": "charger",
        "name": "Charger connection",
        "instructions": "Connect the charger and confirm the operating system reports that external power is connected.",
    },
    {
        "id": "ethernet",
        "name": "Ethernet connection",
        "instructions": "Connect an Ethernet cable and confirm the link indicator or operating-system network status shows a link.",
    },
    {
        "id": "wifi_connection",
        "name": "Wi-Fi connection",
        "instructions": "If Wi-Fi is available and expected, connect to the approved test network and confirm the connection. Do not record the network password.",
    },
    {
        "id": "bluetooth_connection",
        "name": "Bluetooth connection",
        "instructions": "If Bluetooth is available and expected, pair or connect a known test device and confirm it remains connected.",
    },
    {
        "id": "speaker_output",
        "name": "Speaker output",
        "instructions": "Play the test tone or sample and confirm audible output from the intended speaker.",
    },
    {
        "id": "webcam_image",
        "name": "Webcam image",
        "instructions": "Open the camera preview, confirm a live image is visible, and close the preview when finished.",
    },
    {
        "id": "keyboard_input",
        "name": "Keyboard input",
        "instructions": "Type a short phrase in the masked test field and confirm letters, numbers, modifiers, and special keys register. Typed text is not retained.",
    },
    {
        "id": "mouse",
        "name": "Mouse input",
        "instructions": "Move and click the mouse over the test target; confirm movement and clicks are detected.",
    },
    {
        "id": "touchpad",
        "name": "Touchpad input",
        "instructions": "Use the built-in touchpad over the test target; confirm pointer movement and clicks register.",
    },
    {
        "id": "touchscreen",
        "name": "Touchscreen input",
        "instructions": "Touch and move on the physical touchscreen; confirm touch pointer events register. A browser test does not calibrate the panel.",
    },
    {
        "id": "display_pattern",
        "name": "Display patterns",
        "instructions": "View black, white, red, green, and blue patterns; inspect for dead pixels, non-uniformity, or flicker.",
    },
    {
        "id": "usb_read_write",
        "name": "USB read/write",
        "instructions": "Select a known USB storage device and perform a disposable-file write/read/checksum/delete test using an approved test procedure. Never select a drive with valuable data.",
    },
    {
        "id": "memtest86_result",
        "name": "MemTest86+ boot test result",
        "instructions": "Run MemTest86+ separately from the operating system and record the pass/error result here. This is an external boot-time test, not the in-OS bounded RAM check.",
    },
]

MANUAL_CHECK_IDS = {check["id"] for check in MANUAL_CHECKS}
