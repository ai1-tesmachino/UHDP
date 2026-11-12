export interface DemoReport {
    reportId: string;
    manufacturer: string;
    model: string;
    serialNumber: string;
    inspectionDate: string;
    result: "passed" | "issues_found";
    disposition:
        | "Ready for resale"
        | "Resale with disclosed issues"
        | "Repair required"
        | "Reject / parts only"
        | "Inspection incomplete / retest required";
}

const historicalDevices = [
    { manufacturer: "Lenovo", model: "ThinkPad T480" },
    { manufacturer: "Dell", model: "Latitude 5420" },
    { manufacturer: "HP", model: "ProBook 440 G8" },
    { manufacturer: "Dell", model: "OptiPlex 7090" },
    { manufacturer: "HP", model: "EliteBook 840 G7" },
];

const earlierReports: DemoReport[] = Array.from({ length: 18 }, (_, index) => {
    const reportNumber = index + 1;
    const device = historicalDevices[index % historicalDevices.length];

    return {
        reportId: `UHDP-R${String(reportNumber).padStart(3, "0")}`,
        ...device,
        serialNumber: `DEMO-SN-${String(reportNumber).padStart(4, "0")}`,
        inspectionDate: `2026-10-${String(reportNumber).padStart(2, "0")}`,
        result: "passed",
        disposition: "Ready for resale",
    };
});

export const demoReports: DemoReport[] = [
    ...earlierReports,
    {
        reportId: "UHDP-R019",
        manufacturer: "Lenovo",
        model: "ThinkPad L14",
        serialNumber: "DEMO-SN-0019",
        inspectionDate: "2026-10-19",
        result: "issues_found",
        disposition: "Repair required",
    },
    {
        reportId: "UHDP-R020",
        manufacturer: "Dell",
        model: "Latitude 5420",
        serialNumber: "DEMO-SN-0020",
        inspectionDate: "2026-11-03",
        result: "passed",
        disposition: "Ready for resale",
    },
    {
        reportId: "UHDP-R021",
        manufacturer: "HP",
        model: "ProBook 440 G8",
        serialNumber: "DEMO-SN-0021",
        inspectionDate: "2026-11-04",
        result: "issues_found",
        disposition: "Resale with disclosed issues",
    },
    {
        reportId: "UHDP-R022",
        manufacturer: "Lenovo",
        model: "ThinkPad T480",
        serialNumber: "DEMO-SN-0022",
        inspectionDate: "2026-11-05",
        result: "passed",
        disposition: "Ready for resale",
    },
    {
        reportId: "UHDP-R023",
        manufacturer: "Dell",
        model: "Latitude 5420",
        serialNumber: "DEMO-SN-0023",
        inspectionDate: "2026-11-06",
        result: "issues_found",
        disposition: "Repair required",
    },
    {
        reportId: "UHDP-R024",
        manufacturer: "Lenovo",
        model: "ThinkPad T480",
        serialNumber: "DEMO-SN-0024",
        inspectionDate: "2026-11-07",
        result: "passed",
        disposition: "Ready for resale",
    },
];
