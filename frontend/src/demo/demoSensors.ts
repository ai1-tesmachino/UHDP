export interface DemoSensor {
    id: string;
    name: string;
    unit: string;
    readings: number[] | null;
}

export const demoSensors: DemoSensor[] = [
    {
        id: "cpu-temperature",
        name: "CPU Temperature",
        unit: "°C",
        readings: [41, 42, 44, 43, 45, 46, 44, 45, 43, 44, 46, 45],
    },
    {
        id: "gpu-temperature",
        name: "GPU Temperature",
        unit: "°C",
        readings: [39, 40, 41, 42, 40, 41, 43, 42, 41, 40, 42, 42],
    },
    {
        id: "fan-speed",
        name: "Fan Speed",
        unit: "RPM",
        readings: [1900, 1950, 2050, 2100, 2000, 2150, 2200, 2100, 2050, 2150, 2100, 2100],
    },
    {
        id: "battery-temperature",
        name: "Battery Temperature",
        unit: "°C",
        readings: null,
    },
];
