MANUAL_CHECKS = [
    {
        "id": "charger",
        "name": "Charger connection",
        "instructions": "Connect the charger and confirm the operating system reports that external power is connected.",
    },
    {
        "id": "charging_port",
        "name": "Charging port condition",
        "instructions": "Inspect the charging port for looseness, bent contacts, debris, heat damage, and an unstable connection. Do not force the adapter.",
    },
    {
        "id": "charging_indicator",
        "name": "Charging indicators",
        "instructions": "Connect the approved adapter and confirm the device or operating system shows the expected charging indicator.",
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
        "instructions": "Play the short test tone and confirm you can hear it clearly from the intended speakers.",
    },
    {
        "id": "webcam_image",
        "name": "Webcam image",
        "instructions": "Start the camera preview and confirm a clear live image appears. The image is not captured or saved.",
    },
    {
        "id": "face_recognition",
        "name": "Face-recognition workflow",
        "instructions": "If fitted and configured, use the operating-system sign-in workflow to verify camera-based face recognition. Do not capture or store biometric data in UHDP.",
    },
    {
        "id": "keyboard_input",
        "name": "Keyboard input",
        "instructions": "Type a short phrase in the masked test field and confirm letters, numbers, modifiers, and special keys register. Typed text is not retained.",
    },
    {
        "id": "keyboard_backlight",
        "name": "Keyboard backlight",
        "instructions": "Use the supported keyboard control to cycle the backlight and check that keys illuminate evenly.",
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
        "id": "touchpad_gestures",
        "name": "Touchpad buttons and gestures",
        "instructions": "Test left/right clicks, scrolling, and supported multi-finger gestures on the built-in touchpad.",
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
        "id": "display_brightness",
        "name": "Display brightness and uniformity",
        "instructions": "Cycle brightness from minimum to maximum and inspect the panel for uneven backlight, flicker, or artifacts.",
    },
    {
        "id": "microphone_input",
        "name": "Microphone input",
        "instructions": "Record a short phrase, play it back, and confirm your voice is clear. The recording stays in the browser and is discarded when you leave this step.",
    },
    {
        "id": "headset_jack",
        "name": "Headset and audio jack",
        "instructions": "Connect a known-good headset, confirm endpoint detection, and verify audio output from the headset.",
    },
    {
        "id": "usb_port",
        "name": "USB-A ports",
        "instructions": "Connect a known-good USB device to each fitted USB-A port and confirm the operating system detects it.",
    },
    {
        "id": "usb_c_port",
        "name": "USB-C / Thunderbolt ports",
        "instructions": "Test each fitted USB-C or Thunderbolt port with an approved known-good device and confirm connection and charging behavior as applicable.",
    },
    {
        "id": "hdmi_port",
        "name": "HDMI output",
        "instructions": "Connect a known-good display and cable to each fitted HDMI port and confirm a stable image.",
    },
    {
        "id": "displayport",
        "name": "DisplayPort output",
        "instructions": "Connect a known-good display and cable to each fitted DisplayPort output and confirm a stable image.",
    },
    {
        "id": "vga_port",
        "name": "VGA output",
        "instructions": "If fitted, connect a known-good display and cable to the VGA output and confirm a stable image.",
    },
    {
        "id": "card_reader",
        "name": "Memory card reader",
        "instructions": "Insert an approved known-good memory card and confirm detection. Do not format or alter the card.",
    },
    {
        "id": "fingerprint_reader",
        "name": "Fingerprint reader",
        "instructions": "If fitted and configured, use the operating-system enrollment or verification screen to confirm reader response. Do not save biometric data in UHDP.",
    },
    {
        "id": "ambient_light_sensor",
        "name": "Ambient light sensor",
        "instructions": "If fitted, vary the light near the sensor and confirm the operating system reports a corresponding sensor response.",
    },
    {
        "id": "proximity_sensor",
        "name": "Proximity sensor",
        "instructions": "If fitted, cover and uncover the sensor and confirm the expected operating-system or supported application response.",
    },
    {
        "id": "sleep_wake",
        "name": "Sleep, wake, and peripheral recovery",
        "instructions": "Put the device to sleep, wake it, and confirm display, network, audio, and attached test peripherals recover.",
    },
    {
        "id": "physical_inspection",
        "name": "Physical condition inspection",
        "instructions": "Inspect chassis, hinges, ports, corrosion, liquid damage, and battery swelling. Stop and escalate if a swollen battery or other safety hazard is observed.",
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
