import { PointerEvent, useEffect, useRef, useState } from "react";

interface Props {
    checkId: string;
    onEvidence: (evidence: string) => void;
}

export default function ManualHardwareTest({ checkId, onEvidence }: Props) {
    const [pointerEvents, setPointerEvents] = useState(0);
    const [lastPointerType, setLastPointerType] = useState("none");
    const [mediaError, setMediaError] = useState("");
    const [microphoneReady, setMicrophoneReady] = useState(false);
    const [recording, setRecording] = useState(false);
    const [recordingUrl, setRecordingUrl] = useState("");
    const videoRef = useRef<HTMLVideoElement>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const recorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const recordingUrlRef = useRef("");
    const recordingTimeoutRef = useRef<number | null>(null);
    const eventCountRef = useRef(0);
    const lastEvidenceAtRef = useRef(0);

    useEffect(() => {
        setMediaError("");
        setMicrophoneReady(false);
        setRecording(false);
        setRecordingUrl("");
        return () => {
            if (recordingTimeoutRef.current !== null) {
                window.clearTimeout(recordingTimeoutRef.current);
            }
            if (recorderRef.current?.state === "recording") {
                recorderRef.current.onstop = null;
                recorderRef.current.stop();
            }
            streamRef.current?.getTracks().forEach((track) => track.stop());
            streamRef.current = null;
            if (recordingUrlRef.current) {
                URL.revokeObjectURL(recordingUrlRef.current);
                recordingUrlRef.current = "";
            }
        };
    }, [checkId]);

    function pointerActivity(event: PointerEvent<HTMLDivElement>) {
        eventCountRef.current += 1;
        const count = eventCountRef.current;
        const now = event.timeStamp;
        if (now - lastEvidenceAtRef.current >= 150 || event.type === "pointerdown") {
            setPointerEvents(count);
            setLastPointerType(event.pointerType || "unknown");
            onEvidence(`${count} pointer events observed; last pointer type: ${event.pointerType || "unknown"}.`);
            lastEvidenceAtRef.current = now;
        }
    }

    function recordKey() {
        onEvidence("Keyboard activity detected. Key values and typed text were not retained.");
    }

    async function startCamera() {
        setMediaError("");
        if (!navigator.mediaDevices?.getUserMedia) {
            setMediaError("Camera capture is unsupported by this browser or page context.");
            return;
        }
        try {
            streamRef.current?.getTracks().forEach((track) => track.stop());
            const stream = await navigator.mediaDevices.getUserMedia({
                video: true,
                audio: false,
            });
            streamRef.current = stream;
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                await videoRef.current.play();
            }
            onEvidence("Live camera stream opened; no image was saved.");
        } catch (error) {
            const message = error instanceof Error ? error.message : "Camera permission was denied or no camera is available.";
            setMediaError(message);
        }
    }

    function stopCamera() {
        streamRef.current?.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        if (videoRef.current) {
            videoRef.current.srcObject = null;
        }
        onEvidence("Camera stream stopped; no image was saved.");
    }

    async function startMicrophoneRecording() {
        setMediaError("");
        if (!navigator.mediaDevices?.getUserMedia) {
            setMediaError("Microphone access is unsupported by this browser or page context.");
            return;
        }
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
            if (!window.MediaRecorder) {
                stream.getTracks().forEach((track) => track.stop());
                setMediaError("Audio recording is unsupported by this browser.");
                return;
            }
            const recorder = new MediaRecorder(stream);
            streamRef.current = stream;
            audioChunksRef.current = [];
            recorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };
            recorder.onstop = () => {
                if (recordingTimeoutRef.current !== null) {
                    window.clearTimeout(recordingTimeoutRef.current);
                    recordingTimeoutRef.current = null;
                }
                stream.getTracks().forEach((track) => track.stop());
                streamRef.current = null;
                setMicrophoneReady(true);
                setRecording(false);
                const recording = new Blob(audioChunksRef.current, {
                    type: recorder.mimeType || "audio/webm",
                });
                if (recording.size === 0) {
                    setMediaError("No audio was captured. Check the microphone and try again.");
                    return;
                }
                if (recordingUrlRef.current) {
                    URL.revokeObjectURL(recordingUrlRef.current);
                }
                recordingUrlRef.current = URL.createObjectURL(recording);
                setRecordingUrl(recordingUrlRef.current);
                onEvidence("Short microphone sample recorded locally for playback; it is not uploaded or saved to the inspection.");
            };
            recorder.onerror = () => {
                setMediaError("Microphone recording failed. Check the input device and try again.");
                stream.getTracks().forEach((track) => track.stop());
                streamRef.current = null;
                setRecording(false);
            };
            recorderRef.current = recorder;
            recorder.start();
            setMicrophoneReady(true);
            setRecording(true);
            if (recordingUrlRef.current) {
                URL.revokeObjectURL(recordingUrlRef.current);
                recordingUrlRef.current = "";
            }
            recordingTimeoutRef.current = window.setTimeout(() => {
                if (recorder.state === "recording") {
                    recorder.stop();
                }
            }, 5000);
            setRecordingUrl("");
            onEvidence("Recording microphone sample. Speak a short phrase, then stop to play it back.");
        } catch (error) {
            setMicrophoneReady(false);
            setMediaError(error instanceof Error ? error.message : "Microphone permission was denied or no input is available.");
        }
    }

    function stopMicrophoneRecording() {
        if (recordingTimeoutRef.current !== null) {
            window.clearTimeout(recordingTimeoutRef.current);
            recordingTimeoutRef.current = null;
        }
        if (recorderRef.current?.state === "recording") {
            recorderRef.current.stop();
        }
    }

    async function playTone() {
        const AudioContextConstructor = window.AudioContext;
        if (!AudioContextConstructor) {
            setMediaError("Web Audio is unsupported by this browser.");
            return;
        }
        try {
            const context = new AudioContextConstructor();
            if (context.state === "suspended") {
                await context.resume();
            }
            const oscillator = context.createOscillator();
            const gain = context.createGain();
            oscillator.frequency.value = 440;
            gain.gain.value = 0.12;
            oscillator.connect(gain);
            gain.connect(context.destination);
            oscillator.start();
            window.setTimeout(() => {
                oscillator.stop();
                void context.close();
            }, 700);
            onEvidence("Generated a short 440 Hz browser tone; no audio was recorded.");
        } catch (error) {
            setMediaError(error instanceof Error ? error.message : "Audio playback could not start.");
        }
    }

    if (["mouse", "touchpad", "touchscreen"].includes(checkId)) {
        return (
            <div
                className="interactive-input-pad"
                role="application"
                aria-label="Move or touch the pointer test area"
                onPointerMove={pointerActivity}
                onPointerDown={pointerActivity}
            >
                <strong>{checkId === "touchscreen" ? "Touch the target area" : "Move and click in the target area"}</strong>
                <span>Pointer events: {pointerEvents} · input type: {lastPointerType}</span>
                {checkId === "touchscreen" && (
                    <span>For a touchscreen check, use the physical touch surface and confirm the pointer type reports touch.</span>
                )}
            </div>
        );
    }

    if (checkId === "keyboard_input") {
        return (
            <label className="manual-keyboard-test">
                Type a short test phrase (the field masks text; only key activity is noted):
                <input
                    type="password"
                    autoComplete="off"
                    onKeyDown={recordKey}
                    onChange={recordKey}
                    onBlur={(event) => { event.currentTarget.value = ""; }}
                />
            </label>
        );
    }

    if (checkId === "webcam_image") {
        return (
            <div className="browser-media-test">
                <video ref={videoRef} muted playsInline aria-label="Live webcam preview" />
                <div className="action-row">
                    <button className="button button-secondary" type="button" onClick={() => void startCamera()}>
                        Start live preview
                    </button>
                    <button className="button button-quiet" type="button" onClick={stopCamera}>
                        Stop camera
                    </button>
                </div>
                <span>No frame is captured or stored.</span>
                {mediaError && <div className="error-box">{mediaError}</div>}
            </div>
        );
    }

    if (checkId === "speaker_output") {
        return (
            <div className="browser-media-test">
                <button className="button button-secondary" type="button" onClick={() => void playTone()}>
                    Play short test tone
                </button>
                <span>Confirm the tone is audible from the intended speakers. Microphone input is not accessed.</span>
                {mediaError && <div className="error-box">{mediaError}</div>}
            </div>
        );
    }

    if (checkId === "microphone_input") {
        return (
            <div className="browser-media-test">
                <div className="action-row">
                    {!recording ? (
                        <button className="button button-secondary" type="button" onClick={() => void startMicrophoneRecording()}>
                            Record a short sample
                        </button>
                    ) : (
                        <button className="button button-danger" type="button" onClick={stopMicrophoneRecording}>
                            Stop recording
                        </button>
                    )}
                </div>
                {recordingUrl && (
                    <div className="microphone-playback">
                        <strong>Listen to the recording, then choose whether it is clear.</strong>
                        <audio controls src={recordingUrl}>Audio playback is not supported by this browser.</audio>
                    </div>
                )}
                <span>
                    {recording
                        ? "Speak now. Recording stops automatically after 5 seconds and stays in this browser only."
                        : microphoneReady
                          ? "Recording ready for playback. Confirm your voice is clear and audible."
                          : "Record yourself saying a short phrase, stop, then play it back to check the microphone."}
                </span>
                {mediaError && <div className="error-box">{mediaError}</div>}
            </div>
        );
    }

    if (checkId === "display_pattern") {
        return <DisplayPatternTest onEvidence={onEvidence} />;
    }

    return <GuidedChecklist checkId={checkId} onEvidence={onEvidence} />;
}

const GUIDE_STEPS: Record<string, string[]> = {
    charger: ["Connect the approved charger", "Confirm the operating-system power state", "Confirm charging indicator behavior"],
    charging_port: ["Inspect port and contacts without inserting tools", "Check for looseness, debris, corrosion, or heat damage", "Stop and escalate if unsafe damage is present"],
    charging_indicator: ["Connect the approved adapter", "Check the device indicator", "Check the operating-system charging state"],
    ethernet: ["Connect a known-good cable", "Confirm link indication", "Confirm the network adapter reports a link"],
    wifi_connection: ["Connect to the approved test network", "Confirm the connection is active", "Do not enter or record a network password here"],
    bluetooth_connection: ["Enable Bluetooth", "Connect a known-good test device", "Confirm it remains connected"],
    keyboard_input: ["Test letter and number rows", "Test modifiers and function keys", "Check for stuck or repeated keys"],
    keyboard_backlight: ["Use the supported backlight control", "Cycle available brightness levels", "Check for dark or uneven key lighting"],
    mouse: ["Move across the target area", "Test primary and secondary clicks", "Confirm pointer movement is detected"],
    touchpad: ["Test pointer movement", "Test click response", "Check palm rejection if supported"],
    touchpad_gestures: ["Test left and right buttons", "Test scrolling", "Test supported multi-finger gestures"],
    touchscreen: ["Touch the center target", "Touch each edge and corner", "Test multitouch if supported"],
    display_pattern: ["Inspect black and white patterns", "Inspect red, green, and blue patterns", "Check for dead pixels, artifacts, and flicker"],
    display_brightness: ["Set minimum brightness", "Set maximum brightness", "Check uniformity and flicker"],
    headset_jack: ["Connect a known-good headset", "Confirm endpoint detection", "Confirm output from the headset"],
    usb_port: ["Test each fitted USB-A port", "Confirm known-good device detection", "Do not write to unknown storage devices"],
    usb_c_port: ["Test each fitted USB-C / Thunderbolt port", "Confirm known-good accessory detection", "Check charging/video only when the port supports it"],
    hdmi_port: ["Connect a known-good cable and display", "Confirm a stable image", "Repeat for each fitted port"],
    displayport: ["Connect a known-good cable and display", "Confirm a stable image", "Repeat for each fitted output"],
    vga_port: ["Confirm the port is fitted", "Connect an approved display and cable", "Confirm a stable image"],
    card_reader: ["Use an approved known-good card", "Confirm detection", "Do not format or change card contents"],
    fingerprint_reader: ["Confirm reader is fitted", "Open the operating-system authentication screen", "Confirm sensor response without saving biometric data in UHDP"],
    ambient_light_sensor: ["Confirm sensor is fitted", "Vary nearby light levels", "Confirm a corresponding system response if exposed"],
    proximity_sensor: ["Confirm sensor is fitted", "Cover and uncover the sensor", "Confirm expected system response if available"],
    sleep_wake: ["Put the device to sleep", "Wake the device", "Confirm display, network, audio, and peripherals recover"],
    physical_inspection: ["Inspect chassis and hinges", "Inspect ports for damage or corrosion", "Check for liquid damage or battery swelling; stop if a safety hazard is found"],
    usb_read_write: ["Use only an approved disposable test device", "Verify target identity before any write", "Do not test a drive containing valuable data"],
    memtest86_result: ["Run the separate boot-time test", "Record the externally reported result", "Do not treat the in-OS check as MemTest86+ evidence"],
    webcam_image: ["Start the live preview", "Confirm a live image is visible", "Stop the camera when finished"],
    face_recognition: ["Confirm supported camera and OS sign-in configuration", "Run the OS face-recognition workflow", "Do not capture or store biometric data in UHDP"],
    speaker_output: ["Play the short test tone", "Listen at the intended speaker", "Confirm the tone is clear and undistorted"],
};

function GuidedChecklist({ checkId, onEvidence }: Props) {
    const steps = GUIDE_STEPS[checkId] || [
        "Confirm whether this component or feature is fitted",
        "Perform the guided physical or operating-system check",
        "Record only the observed result and any relevant notes",
    ];
    const [stepIndex, setStepIndex] = useState(0);
    const [completedSteps, setCompletedSteps] = useState<string[]>([]);

    useEffect(() => {
        setStepIndex(0);
        setCompletedSteps([]);
        onEvidence("");
    }, [checkId]);

    function completeCurrentStep() {
        const completed = [...completedSteps, steps[stepIndex]];
        setCompletedSteps(completed);
        if (stepIndex + 1 === steps.length) {
            onEvidence(`Completed operator steps: ${completed.join("; ")}.`);
            return;
        }
        setStepIndex(stepIndex + 1);
    }

    return (
        <div className="manual-substep">
            <span className="eyebrow">INSTRUCTION {stepIndex + 1} OF {steps.length}</span>
            <strong>{steps[stepIndex]}</strong>
            <button className="button button-secondary" type="button" onClick={completeCurrentStep}>
                {stepIndex + 1 === steps.length ? "Finish instructions" : "Done, next instruction"}
            </button>
        </div>
    );
}

function DisplayPatternTest({ onEvidence }: { onEvidence: (evidence: string) => void }) {
    const [pattern, setPattern] = useState("black");
    const patterns = ["black", "white", "red", "green", "blue"];
    const colors: Record<string, string> = {
        black: "#000",
        white: "#fff",
        red: "#f00",
        green: "#0f0",
        blue: "#00f",
    };

    return (
        <div className="display-pattern-test">
            <div
                className="display-pattern-surface"
                style={{ backgroundColor: colors[pattern] }}
                aria-label={`${pattern} display test pattern`}
            />
            <div className="action-row">
                {patterns.map((name) => (
                    <button
                        className="button button-secondary"
                        type="button"
                        key={name}
                        onClick={() => {
                            setPattern(name);
                            onEvidence(`Display pattern viewed: ${name}.`);
                        }}
                    >
                        {name}
                    </button>
                ))}
            </div>
            <span>Inspect for dead pixels, uneven areas, flicker, and color artifacts.</span>
        </div>
    );
}
