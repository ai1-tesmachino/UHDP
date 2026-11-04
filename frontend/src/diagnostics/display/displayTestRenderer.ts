const SOLID_COLOURS: Record<string, string> = {
    Black: "#000000",
    White: "#ffffff",
    Red: "#ff0000",
    Green: "#00ff00",
    Blue: "#0000ff",
    Cyan: "#00ffff",
    Magenta: "#ff00ff",
    Yellow: "#ffff00",
    Grey: "#808080",
};

function centeredText(
    context: CanvasRenderingContext2D,
    text: string,
    x: number,
    y: number,
    color: string,
    size: number,
) {
    context.fillStyle = color;
    context.font = `${size}px system-ui, sans-serif`;
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillText(text, x, y);
}

function drawInformation(
    context: CanvasRenderingContext2D,
    width: number,
    height: number,
    metadata: Record<string, unknown>,
) {
    context.fillStyle = "#101923";
    context.fillRect(0, 0, width, height);
    const lines = [
        ["Resolution", metadata.resolution],
        ["Refresh rate", metadata.refresh_rate_hz ? `${metadata.refresh_rate_hz} Hz` : null],
        ["Display", metadata.display_name],
        ["Manufacturer", metadata.manufacturer],
        ["Model", metadata.model],
        ["Connection", Array.isArray(metadata.connectors)
            ? metadata.connectors
                .filter((connector) =>
                    typeof connector === "object" &&
                    connector !== null &&
                    (connector as Record<string, unknown>).status === "connected",
                )
                .map((connector) => (connector as Record<string, unknown>).name)
                .join(", ") || null
            : null],
    ];
    const lineHeight = Math.min(42, height / (lines.length + 2));
    const top = height / 2 - lineHeight * (lines.length - 1) / 2;
    centeredText(context, "Display information · visual health is technician assessed", width / 2, top - lineHeight * 1.4, "#e5edf5", Math.max(16, lineHeight * 0.6));
    lines.forEach(([label, value], index) => {
        const content = value === null || value === undefined || value === ""
            ? "Not available"
            : String(value);
        centeredText(
            context,
            `${label}: ${content}`,
            width / 2,
            top + index * lineHeight,
            value === null || value === undefined || value === "" ? "#91a0b0" : "#f8fafc",
            Math.max(15, lineHeight * 0.48),
        );
    });
}

function drawGradient(
    context: CanvasRenderingContext2D,
    width: number,
    height: number,
    patternIndex: number,
) {
    const gradients = [
        ["#000000", "#ffffff"],
        ["#ffffff", "#000000"],
        ["#000000", "#ff0000"],
        ["#000000", "#00ff00"],
        ["#000000", "#0000ff"],
        ["#000000", "#ffffff"],
    ];
    const colors = gradients[patternIndex % gradients.length];
    const horizontal = patternIndex % 2 === 0;
    const gradient = horizontal
        ? context.createLinearGradient(0, 0, width, 0)
        : context.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, colors[0]);
    gradient.addColorStop(1, colors[1]);
    context.fillStyle = gradient;
    context.fillRect(0, 0, width, height);
}

function drawContrast(
    context: CanvasRenderingContext2D,
    width: number,
    height: number,
    patternIndex: number,
) {
    context.fillStyle = patternIndex === 3 ? "#ffffff" : "#000000";
    context.fillRect(0, 0, width, height);
    const count = 17;
    const barWidth = width / count;
    const barHeight = Math.min(height * 0.34, 220);
    const top = (height - barHeight) / 2;
    for (let index = 0; index < count; index += 1) {
        const level = Math.round(index / (count - 1) * 255);
        const value = patternIndex === 0
            ? Math.round(index / (count - 1) * 32)
            : patternIndex === 1
              ? Math.round(16 + index / (count - 1) * 64)
              : patternIndex === 2
                ? Math.round(160 + index / (count - 1) * 80)
                : 255 - level;
        context.fillStyle = `rgb(${value} ${value} ${value})`;
        context.fillRect(index * barWidth, top, Math.ceil(barWidth), barHeight);
    }
}

function drawGeometry(
    context: CanvasRenderingContext2D,
    width: number,
    height: number,
    patternIndex: number,
) {
    context.fillStyle = "#111111";
    context.fillRect(0, 0, width, height);
    context.strokeStyle = "#f4f4f4";
    context.lineWidth = 1;
    context.imageSmoothingEnabled = false;

    if (patternIndex === 0) {
        const step = Math.max(18, Math.min(width, height) / 28);
        context.beginPath();
        for (let x = step; x < width; x += step) {
            context.moveTo(x, 0);
            context.lineTo(x, height);
        }
        for (let y = step; y < height; y += step) {
            context.moveTo(0, y);
            context.lineTo(width, y);
        }
        context.stroke();
    } else if (patternIndex === 1) {
        const step = Math.max(12, Math.min(width, height) / 32);
        for (let y = 0; y < height; y += step) {
            for (let x = 0; x < width; x += step) {
                if ((Math.floor(x / step) + Math.floor(y / step)) % 2 === 0) {
                    context.fillStyle = "#f4f4f4";
                    context.fillRect(x, y, step, step);
                }
            }
        }
    } else if (patternIndex === 2) {
        const maxRadius = Math.min(width, height) * 0.46;
        context.beginPath();
        for (let radius = 12; radius <= maxRadius; radius += Math.max(12, maxRadius / 16)) {
            context.moveTo(width / 2 + radius, height / 2);
            context.arc(width / 2, height / 2, radius, 0, Math.PI * 2);
        }
        context.stroke();
    } else if (patternIndex === 3) {
        context.beginPath();
        context.moveTo(width / 2, 0);
        context.lineTo(width / 2, height);
        context.moveTo(0, height / 2);
        context.lineTo(width, height / 2);
        for (let offset = 20; offset < Math.min(width, height) / 2; offset += 20) {
            context.moveTo(width / 2 + offset, height / 2 - 7);
            context.lineTo(width / 2 + offset, height / 2 + 7);
            context.moveTo(width / 2 - offset, height / 2 - 7);
            context.lineTo(width / 2 - offset, height / 2 + 7);
            context.moveTo(width / 2 - 7, height / 2 + offset);
            context.lineTo(width / 2 + 7, height / 2 + offset);
            context.moveTo(width / 2 - 7, height / 2 - offset);
            context.lineTo(width / 2 + 7, height / 2 - offset);
        }
        context.stroke();
    } else {
        const inset = Math.min(width, height) * 0.04;
        context.strokeRect(inset, inset, width - inset * 2, height - inset * 2);
        context.beginPath();
        for (const fraction of [0.25, 0.5, 0.75]) {
            context.moveTo(width * fraction, 0);
            context.lineTo(width * fraction, height);
            context.moveTo(0, height * fraction);
            context.lineTo(width, height * fraction);
        }
        context.stroke();
    }
}

function drawArtifacts(
    context: CanvasRenderingContext2D,
    width: number,
    height: number,
    patternIndex: number,
    timestamp: number,
) {
    context.fillStyle = "#080808";
    context.fillRect(0, 0, width, height);
    const phase = (timestamp % 3200) / 3200;
    if (patternIndex === 0) {
        const size = Math.max(24, Math.min(width, height) * 0.12);
        context.fillStyle = "#ffffff";
        context.fillRect(phase * (width + size) - size, height / 2 - size / 2, size, size);
    } else if (patternIndex === 1 || patternIndex === 2) {
        context.fillStyle = "#ffffff";
        if (patternIndex === 1) {
            const y = phase * height;
            context.fillRect(0, y, width, 3);
        } else {
            const x = phase * width;
            context.fillRect(x, 0, 3, height);
        }
    } else if (patternIndex === 3) {
        const cell = Math.max(16, Math.min(width, height) / 24);
        const offset = (phase * cell * 8) % (cell * 2);
        for (let y = -cell; y < height + cell; y += cell) {
            for (let x = -cell; x < width + cell; x += cell) {
                const odd = (Math.floor((x + offset) / cell) + Math.floor(y / cell)) % 2 !== 0;
                context.fillStyle = odd ? "#ffffff" : "#000000";
                context.fillRect(x + offset, y, cell, cell);
            }
        }
    } else {
        const colours = ["#ff0000", "#00ff00", "#0000ff", "#ffffff", "#000000"];
        context.fillStyle = colours[Math.floor(timestamp / 650) % colours.length];
        context.fillRect(0, 0, width, height);
    }
}

export function drawDisplayPattern(
    context: CanvasRenderingContext2D,
    width: number,
    height: number,
    testId: string,
    patternIndex: number,
    timestamp: number,
    metadata: Record<string, unknown>,
    patternActive: boolean,
) {
    if (width <= 0 || height <= 0) return;
    if (!patternActive) {
        context.fillStyle = "#17202a";
        context.fillRect(0, 0, width, height);
        centeredText(context, "Pattern paused", width / 2, height / 2, "#f5f7fa", Math.max(18, Math.min(width, height) * 0.035));
        return;
    }

    if (testId === "display_information") {
        drawInformation(context, width, height, metadata);
        return;
    }
    if (testId === "dead_pixel" || testId === "rgb_colour" || testId === "colour_uniformity") {
        const colours = testId === "dead_pixel"
            ? ["Black", "White", "Red", "Green", "Blue"]
            : testId === "rgb_colour"
              ? ["Red", "Green", "Blue", "Cyan", "Magenta", "Yellow", "White", "Black"]
              : ["White", "Grey", "Black", "Red", "Green", "Blue"];
        context.fillStyle = SOLID_COLOURS[colours[patternIndex % colours.length]];
        context.fillRect(0, 0, width, height);
        return;
    }
    if (testId === "gradient") {
        drawGradient(context, width, height, patternIndex);
        return;
    }
    if (testId === "contrast") {
        drawContrast(context, width, height, patternIndex);
        return;
    }
    if (testId === "geometry") {
        drawGeometry(context, width, height, patternIndex);
        return;
    }
    if (testId === "visual_artifacts") {
        drawArtifacts(context, width, height, patternIndex, timestamp);
        return;
    }
    context.fillStyle = "#111111";
    context.fillRect(0, 0, width, height);
}
