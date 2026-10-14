import { useEffect, useState } from "react";
import { getHealth } from "../api/health";
import { getStationProfile } from "../station";

export default function Navbar() {
    const [online, setOnline] = useState<boolean | null>(null);
    const station = getStationProfile();

    useEffect(() => {
        let mounted = true;

        getHealth()
            .then(() => {
                if (mounted) {
                    setOnline(true);
                }
            })
            .catch(() => {
                if (mounted) {
                    setOnline(false);
                }
            });

        return () => {
            mounted = false;
        };
    }, []);

    return (
        <header className="navbar">
            <div>
                <div className="navbar-title">
                    UHDP Diagnostics Platform
                </div>

                <div className="navbar-subtitle">
                    Universal Hardware Diagnostics Platform
                </div>
            </div>

            {online !== null && (
                <div
                    className={`health-indicator ${
                        online ? "online" : "offline"
                    }`}
                >
                    <span className="health-dot" />
                    {online ? "Backend Online" : "Backend Offline"}
                </div>
            )}
            {station && (
                <div className="navbar-station" aria-label="Current workstation">
                    <strong>{station.technician}</strong>
                    <span>Station {station.station_id}</span>
                </div>
            )}
        </header>
    );
}