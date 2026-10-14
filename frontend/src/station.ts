export interface StationProfile {
    technician: string;
    station_id: string;
}

const STORAGE_KEY = "uhdp.station-profile";

export function getStationProfile(): StationProfile | null {
    const value = localStorage.getItem(STORAGE_KEY);
    if (!value) {
        return null;
    }

    try {
        const profile: unknown = JSON.parse(value);
        if (
            typeof profile === "object" &&
            profile !== null &&
            "technician" in profile &&
            "station_id" in profile &&
            typeof profile.technician === "string" &&
            typeof profile.station_id === "string" &&
            profile.technician.trim() &&
            profile.station_id.trim()
        ) {
            return {
                technician: profile.technician,
                station_id: profile.station_id,
            };
        }
    } catch {
        return null;
    }

    return null;
}

export function saveStationProfile(profile: StationProfile): void {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
}
