import { FormEvent, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { getStationProfile, saveStationProfile } from "../station";
import FieldLabel from "../components/FieldLabel";

export default function StationSetup() {
    const navigate = useNavigate();
    const location = useLocation();
    const [technician, setTechnician] = useState(() => getStationProfile()?.technician || "");
    const [stationId, setStationId] = useState(() => getStationProfile()?.station_id || "");

    function save(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        const profile = {
            technician: technician.trim(),
            station_id: stationId.trim(),
        };
        if (!profile.technician || !profile.station_id) {
            return;
        }
        saveStationProfile(profile);
        const returnPath = (location.state as { from?: string } | null)?.from;
        navigate(returnPath && returnPath !== "/setup" ? returnPath : "/", { replace: true });
    }

    return (
        <div className="setup-page">
            <section className="setup-card">
                <span className="eyebrow">STATION SETUP</span>
                <h1>Set up this inspection station</h1>
                <p>
                    Enter the technician and station identifiers that should appear with
                    new QC sessions. This identifies the workstation; it is not
                    an authenticated sign-in.
                </p>
                <form onSubmit={save}>
                    <FieldLabel required>
                        Technician
                        <input
                            autoComplete="name"
                            maxLength={150}
                            required
                            value={technician}
                            onChange={(event) => setTechnician(event.target.value)}
                        />
                    </FieldLabel>
                    <FieldLabel required>
                        Station ID
                        <input
                            autoComplete="off"
                            maxLength={100}
                            required
                            value={stationId}
                            onChange={(event) => setStationId(event.target.value)}
                        />
                    </FieldLabel>
                    <button className="button button-primary" type="submit">
                        Save station and continue
                    </button>
                </form>
            </section>
        </div>
    );
}
