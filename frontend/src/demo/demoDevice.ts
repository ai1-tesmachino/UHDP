export interface DemoDevice {
    manufacturer: string;
    model: string;
    systemSerialNumber: string | null;
    processor: {
        manufacturer: string;
        model: string;
        physicalCores: number;
        logicalThreads: number;
        baseFrequencyGhz: number | null;
        maxFrequencyGhz: number | null;
    };
    keyboard: {
        layout: string;
        type: string;
    };
    touchpad: {
        present: boolean;
        type: string;
    };
    memory: {
        modules: Array<{
            slot: string;
            capacityGb: number;
            type: string;
            speedMts: number | null;
            serialNumber: string | null;
        }>;
    };
    storage: {
        drives: Array<{
            model: string;
            capacityGb: number;
            type: string;
            interface: string;
            serialNumber: string | null;
        }>;
    };
    graphicsAdapter: string;
    bios: {
        manufacturer: string;
        version: string;
        releaseDate: string | null;
        serialNumber: string | null;
    };
    display: {
        screenSizeInches: number | null;
        resolution: string | null;
        manufacturer: string | null;
        graphicsAdapter: string;
        touchscreenPresent: boolean;
    };
}

export const demoDevice: DemoDevice = {
    manufacturer: "Lenovo",
    model: "ThinkPad T480",
    systemSerialNumber: "PF123456",
    processor: {
        manufacturer: "Intel",
        model: "Core i5-8350U",
        physicalCores: 4,
        logicalThreads: 8,
        baseFrequencyGhz: 1.7,
        maxFrequencyGhz: 3.6,
    },
    keyboard: {
        layout: "US QWERTY",
        type: "Standard laptop keyboard",
    },
    touchpad: {
        present: true,
        type: "Integrated touchpad",
    },
    memory: {
        modules: [
            {
                slot: "Slot 1",
                capacityGb: 8,
                type: "DDR4",
                speedMts: 2400,
                serialNumber: "ABC123456",
            },
            {
                slot: "Slot 2",
                capacityGb: 8,
                type: "DDR4",
                speedMts: 2400,
                serialNumber: "DEF789012",
            },
        ],
    },
    storage: {
        drives: [
            {
                model: "Samsung PM981",
                capacityGb: 256,
                type: "NVMe SSD",
                interface: "PCIe",
                serialNumber: "S4XXXXXXXX",
            },
        ],
    },
    graphicsAdapter: "Intel UHD Graphics 620",
    bios: {
        manufacturer: "Lenovo",
        version: "N24ET",
        releaseDate: "2023-07-14",
        serialNumber: "PF123456",
    },
    display: {
        screenSizeInches: 14,
        resolution: "1920 × 1080",
        manufacturer: "BOE",
        graphicsAdapter: "Intel UHD Graphics 620",
        touchscreenPresent: false,
    },
};

export function getTotalInstalledRamGb(device: DemoDevice): number {
    return device.memory.modules.reduce((total, module) => total + module.capacityGb, 0);
}

export function getTotalInstalledStorageGb(device: DemoDevice): number {
    return device.storage.drives.reduce((total, drive) => total + drive.capacityGb, 0);
}
