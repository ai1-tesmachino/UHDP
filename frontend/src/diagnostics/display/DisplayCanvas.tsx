import { useEffect, useRef, type KeyboardEvent } from "react";
import { drawDisplayPattern } from "./displayTestRenderer";

interface DisplayCanvasProps {
    testId: string;
    patternIndex: number;
    patternCount: number;
    metadata: Record<string, unknown>;
    patternActive: boolean;
    onPatternChange: (index: number) => void;
}

export default function DisplayCanvas({
    testId,
    patternIndex,
    patternCount,
    metadata,
    patternActive,
    onPatternChange,
}: DisplayCanvasProps) {
    const stageRef = useRef<HTMLDivElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const stage = stageRef.current;
        const canvas = canvasRef.current;
        const context = canvas?.getContext("2d", { alpha: false });
        if (!stage || !canvas || !context) return;

        let disposed = false;
        let animationFrame = 0;
        const animated = testId === "visual_artifacts" && patternActive;

        const render = (timestamp: number) => {
            if (disposed) return;
            const bounds = stage.getBoundingClientRect();
            const width = Math.max(1, Math.floor(bounds.width));
            const height = Math.max(1, Math.floor(bounds.height));
            const pixelRatio = Math.max(1, window.devicePixelRatio || 1);
            const bitmapWidth = Math.round(width * pixelRatio);
            const bitmapHeight = Math.round(height * pixelRatio);
            if (canvas.width !== bitmapWidth || canvas.height !== bitmapHeight) {
                canvas.width = bitmapWidth;
                canvas.height = bitmapHeight;
            }
            context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
            drawDisplayPattern(
                context,
                width,
                height,
                testId,
                patternIndex,
                timestamp,
                metadata,
                patternActive,
            );
            if (animated) animationFrame = window.requestAnimationFrame(render);
        };

        const observer = new ResizeObserver(() => render(performance.now()));
        observer.observe(stage);
        const handleResize = () => render(performance.now());
        window.addEventListener("resize", handleResize);
        render(performance.now());

        return () => {
            disposed = true;
            observer.disconnect();
            window.removeEventListener("resize", handleResize);
            if (animationFrame) window.cancelAnimationFrame(animationFrame);
        };
    }, [metadata, patternActive, patternIndex, testId]);

    function handleKeyDown(event: KeyboardEvent<HTMLCanvasElement>) {
        if (patternCount <= 1) return;
        if (event.key === "ArrowRight") {
            event.preventDefault();
            onPatternChange((patternIndex + 1) % patternCount);
        } else if (event.key === "ArrowLeft") {
            event.preventDefault();
            onPatternChange((patternIndex - 1 + patternCount) % patternCount);
        }
    }

    return (
        <div className="display-canvas-stage" ref={stageRef}>
            <canvas
                ref={canvasRef}
                className="display-test-canvas"
                aria-label="Technician-visible display test pattern. The pattern does not automatically detect panel defects."
                tabIndex={0}
                onKeyDown={handleKeyDown}
            />
        </div>
    );
}
