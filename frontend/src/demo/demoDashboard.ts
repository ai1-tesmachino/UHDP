import { demoDevice } from "./demoDevice";
import { demoReports, type DemoReport } from "./demoReports";

export const demoDashboard = {
    device: demoDevice,
    reports: demoReports,
};

export function getDemoReportCount(reports: DemoReport[]): number {
    return reports.length;
}

export function getRecentDemoReports(reports: DemoReport[]): DemoReport[] {
    return [...reports]
        .sort((left, right) => right.inspectionDate.localeCompare(left.inspectionDate))
        .slice(0, 5);
}
