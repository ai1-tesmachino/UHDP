import { PointerEvent, useEffect, useRef, useState } from "react";

interface Props {
    checkId: string;
    onEvidence: (evidence: string) => void;
}

export default function ManualHardwareTest({ checkId, onEvidence }: Props) {
    const [pointerEvents, setPointerEvents] = useState(0);
    const [lastPointerType, setLastPointerType] = useState("none");
    const [mediaError, setMediaError] = useState("");
    const videoRef = useRef<HTMLVideoElement>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const eventCountRef = useRef(0);
    const lastEvidenceAtRef = useRef(0);

    useEffect(() => {
        setMediaError("");
        return () => {
            streamRef.current?.getTracks().forEach((track) => track.stop());
            streamRef.current = null;
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

    if (checkId === "display_pattern") {
        return <DisplayPatternTest onEvidence={onEvidence} />;
    }

    return null;
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
